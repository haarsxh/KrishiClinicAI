"""Prefetch the local EfficientNetV2-S weights into app/ai/weights at build time.

The local PyTorch provider (AI_PROVIDER=local) needs model.pt and metadata.json
bundled in the image so inference works with zero network access. Every other
provider (mock, gemini, groq, openai) never touches these files, so a failed
download must not break the image build for those users.

Exit codes:
    0 - weights are present, or they are optional and could not be fetched
    1 - weights are required (REQUIRE_WEIGHTS=true) but could not be fetched
"""

import os
import sys
from pathlib import Path

REPO_ID = os.environ.get(
    "MODEL_REPO_ID",
    "the-harsh-vardhan/krishiclinic-crop-disease-v0-1-baseline-bmd",
)
MODEL_FILENAME = "model.pt"
METADATA_FILENAME = "metadata.json"

WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ai" / "weights"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    required = _truthy(os.environ.get("REQUIRE_WEIGHTS"))
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = WEIGHTS_DIR / MODEL_FILENAME
    metadata_path = WEIGHTS_DIR / METADATA_FILENAME

    if model_path.exists() and metadata_path.exists():
        print(f"==> Model weights already bundled in {WEIGHTS_DIR}. Skipping download.")
        return 0

    print(f"==> Fetching model weights from Hugging Face repo '{REPO_ID}'...")

    try:
        from huggingface_hub import hf_hub_download

        for filename in (MODEL_FILENAME, METADATA_FILENAME):
            if (WEIGHTS_DIR / filename).exists():
                continue
            hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                local_dir=str(WEIGHTS_DIR),
                token=token,
            )
        print(f"==> Model weights bundled successfully in {WEIGHTS_DIR}.")
        return 0

    except Exception as exc:  # noqa: BLE001 - any failure is handled identically
        message = (
            f"Could not download model weights from '{REPO_ID}': {exc}\n"
            "    This repo is private/gated. To use AI_PROVIDER=local, either:\n"
            "      * pass a Hugging Face token with access:\n"
            "          docker build --build-arg HF_TOKEN=hf_xxx --build-arg REQUIRE_WEIGHTS=true ./backend\n"
            "      * point MODEL_REPO_ID at a repo you can read, or\n"
            "      * place model.pt and metadata.json directly in backend/app/ai/weights/."
        )

        if required:
            print(f"ERROR: {message}", file=sys.stderr)
            return 1

        print(f"WARNING: {message}")
        print(
            "==> Continuing build without local weights. All other AI providers "
            "(mock, gemini, groq, openai) work normally; AI_PROVIDER=local will not."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
