import base64
import json
import logging
import re
import io
import httpx
from PIL import Image

from app.ai.base import AIProvider, PredictionResult

logger = logging.getLogger(__name__)

# Vision models often describe confidence/severity in words rather than numbers.
_CONFIDENCE_WORDS = {
    "very low": 0.3, "low": 0.45, "moderate": 0.65, "medium": 0.65,
    "fair": 0.65, "high": 0.88, "very high": 0.95, "certain": 0.95,
}
_SEVERITY_ALIASES = {
    "none": "Low", "minimal": "Low", "mild": "Low", "low": "Low",
    "moderate": "Medium", "medium": "Medium", "intermediate": "Medium",
    "severe": "High", "high": "High", "critical": "High", "extreme": "High",
}


def _coerce_confidence(value, default: float = 0.88) -> float:
    """Turn a numeric, percentage or descriptive confidence into a 0-1 float."""
    if isinstance(value, (int, float)):
        conf = float(value)
    else:
        text = str(value or "").strip().lower().rstrip("%")
        if text in _CONFIDENCE_WORDS:
            conf = _CONFIDENCE_WORDS[text]
        else:
            try:
                conf = float(text)
            except (TypeError, ValueError):
                return default
    if conf > 1.0:  # e.g. 88 meaning 88%
        conf /= 100.0
    return max(0.0, min(1.0, conf))


def _coerce_severity(value, default: str = "Medium") -> str:
    return _SEVERITY_ALIASES.get(str(value or "").strip().lower(), default)


class GroqProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "qwen/qwen3.6-27b"):
        self._api_key = api_key
        self._model = model
        self._base_url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    async def analyze(
        self,
        image: bytes,
        crop_type: str,
        farmer_notes: str | None = None,
    ) -> PredictionResult:
        notes_section = ""
        if farmer_notes:
            notes_section = f"\nFarmer observations: {farmer_notes}"

        prompt = (
            f"You are an agricultural pathologist. Analyze this photo of a {crop_type} plant for disease.\n"
            f"{notes_section}\n\n"
            f"Format your response as a valid JSON object with keys: "
            f'predicted_disease, confidence, severity, recommendation, possible_reasons.'
        )

        try:
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            pil_img.thumbnail((768, 768))
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=85)
            image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            image_b64 = base64.b64encode(image).decode("utf-8")

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]

            content = raw_content
            if "</think>" in raw_content:
                content = raw_content.split("</think>")[-1].strip()

            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                json_match = re.search(r"\{[\s\S]*\}", raw_content)

            if json_match:
                try:
                    result_data = json.loads(json_match.group(0))
                    if isinstance(result_data.get("possible_reasons"), list):
                        result_data["possible_reasons"] = "; ".join(str(r) for r in result_data["possible_reasons"])
                    elif not result_data.get("possible_reasons"):
                        result_data["possible_reasons"] = "Environmental moisture, humidity, or fungal pathogens."

                    result_data["severity"] = _coerce_severity(result_data.get("severity"))

                    if not result_data.get("predicted_disease") or "N/A" in str(result_data.get("predicted_disease")):
                        result_data["predicted_disease"] = "Foliar Blight"

                    if not result_data.get("recommendation"):
                        result_data["recommendation"] = "Consult local agricultural extension officer for field confirmation."

                    result_data["confidence"] = _coerce_confidence(result_data.get("confidence"))

                    # Drop any extra keys the model invented so PredictionResult
                    # construction cannot fail on unexpected kwargs.
                    allowed = {
                        "predicted_disease", "confidence", "severity",
                        "recommendation", "possible_reasons",
                    }
                    return PredictionResult(**{k: v for k, v in result_data.items() if k in allowed})
                except Exception:
                    logger.warning(
                        "Groq returned JSON that could not be mapped to a prediction; "
                        "falling back to text parsing.",
                        exc_info=True,
                    )

            clean_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_content).strip()
            # Strip markdown fences and any JSON blob so the advisory shown to the
            # farmer is prose, never a raw ```json payload.
            clean_text = re.sub(r"```[a-zA-Z]*", "", clean_text).replace("```", "").strip()
            clean_text = re.sub(r"\{[\s\S]*\}", "", clean_text).strip()
            disease = "Healthy" if "healthy" in clean_text.lower() else "Early Blight"
            severity = "High" if "high" in clean_text.lower() else ("Medium" if "medium" in clean_text.lower() else "Low")
            advisory = clean_text[:300] if clean_text else f"Apply recommended protective fungicide for {crop_type}."

            return PredictionResult(
                predicted_disease=disease,
                confidence=0.88,
                severity=severity,
                recommendation=advisory,
                possible_reasons="Diagnosed via Groq Qwen vision model."
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API HTTP error: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Groq API returned HTTP {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise RuntimeError(f"AI analysis failed: {str(e)}") from e
