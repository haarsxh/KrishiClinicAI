import io
import pytest

@pytest.mark.asyncio
async def test_create_prediction_success(client, sample_image):
    response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test_crop.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Yellow spots on leaves"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["crop_type"] == "Wheat"
    assert data["farmer_notes"] == "Yellow spots on leaves"
    assert data["predicted_disease"] == "Pending Review"
    assert data["confidence"] == 0.0
    assert data["ai_provider"] == "Hidden"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_prediction_missing_image(client):
    response = await client.post(
        "/api/v1/predictions",
        data={"crop_type": "Wheat"},
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_prediction_invalid_file_type(client):
    response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
        data={"crop_type": "Wheat"},
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_prediction_empty_crop_type(client, sample_image):
    response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "   "},
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_list_predictions(client, sample_image):
    await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Rice"},
    )

    response = await client.get("/api/v1/predictions")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert len(data["items"]) > 0

@pytest.mark.asyncio
async def test_list_predictions_with_filter(client):
    response = await client.get("/api/v1/predictions?crop_type=Wheat")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_prediction_detail(client, sample_image):
    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Tomato"},
    )
    prediction_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/predictions/{prediction_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == prediction_id
    assert data["crop_type"] == "Tomato"

@pytest.mark.asyncio
async def test_get_prediction_not_found(client):
    response = await client.get(
        "/api/v1/predictions/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_agronomist_review_flow(client, sample_image, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "AUTO_APPROVE_CONFIDENCE_THRESHOLD", 0.99)

    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )
    assert create_response.status_code == 201
    pred_id = create_response.json()["id"]

    detail_response = await client.get(f"/api/v1/predictions/{pred_id}")
    assert detail_response.json()["status"] == "PENDING_REVIEW"
    assert detail_response.json()["predicted_disease"] == "Pending Review"

    review_response = await client.post(
        f"/api/v1/predictions/{pred_id}/review",
        json={
            "predicted_disease": "Yellow Rust",
            "severity": "Medium",
            "review": "Fungicide recommended immediately."
        }
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "REVIEWED"

    detail_response_after = await client.get(f"/api/v1/predictions/{pred_id}")
    assert detail_response_after.json()["status"] == "REVIEWED"
    assert detail_response_after.json()["predicted_disease"] == "Yellow Rust"
    assert detail_response_after.json()["recommendation"] == "Fungicide recommended immediately."

@pytest.mark.asyncio
async def test_auto_release_high_confidence(client, sample_image, monkeypatch):
    """Opt-in legacy behaviour: with mandatory review disabled, confident
    predictions are released to the farmer without an agronomist."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "REQUIRE_AGRONOMIST_APPROVAL", False)
    monkeypatch.setattr(get_settings(), "AUTO_APPROVE_CONFIDENCE_THRESHOLD", 0.70)

    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )
    assert create_response.status_code == 201
    pred_id = create_response.json()["id"]

    detail_response = await client.get(f"/api/v1/predictions/{pred_id}")
    assert detail_response.status_code == 200
    data = detail_response.json()
    assert data["status"] == "REVIEWED"
    assert data["predicted_disease"] != "Pending Review"
    assert data["confidence"] >= 0.70
    assert data["reviewed_at"] is not None

@pytest.mark.asyncio
async def test_high_confidence_still_needs_agronomist_by_default(client, sample_image):
    """Default behaviour: even a highly confident diagnosis is withheld from the
    farmer until an agronomist approves it."""
    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )
    assert create_response.status_code == 201
    pred_id = create_response.json()["id"]

    # The farmer must not see the diagnosis yet.
    data = (await client.get(f"/api/v1/predictions/{pred_id}")).json()
    assert data["status"] == "PENDING_REVIEW"
    assert data["predicted_disease"] == "Pending Review"
    assert data["confidence"] == 0.0
    assert data["reviewed_at"] is None

    # It must be sitting in the agronomist's queue.
    queue = (await client.get("/api/v1/predictions?status=PENDING_REVIEW")).json()
    assert pred_id in [item["id"] for item in queue["items"]]


@pytest.mark.asyncio
async def test_farmer_sees_diagnosis_only_after_agronomist_approves(client, sample_image):
    """End-to-end gate: upload -> queued -> agronomist opinion -> released."""
    pred_id = (await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )).json()["id"]

    assert (await client.get(f"/api/v1/predictions/{pred_id}")).json()["status"] == "PENDING_REVIEW"

    review = await client.post(
        f"/api/v1/predictions/{pred_id}/review",
        json={
            "predicted_disease": "Yellow Rust",
            "severity": "High",
            "review": "Confirmed. Apply propiconazole at 0.1%.",
        },
    )
    assert review.status_code == 200

    released = (await client.get(f"/api/v1/predictions/{pred_id}")).json()
    assert released["status"] == "REVIEWED"
    assert released["agronomist_id"] is not None
    assert released["reviewed_at"] is not None
    # The farmer now sees the agronomist's verified opinion.
    assert released["agronomist_predicted_disease"] == "Yellow Rust"
    assert released["agronomist_review"] == "Confirmed. Apply propiconazole at 0.1%."
    assert released["predicted_disease"] != "Pending Review"


@pytest.mark.asyncio
async def test_low_confidence_remains_gated(client, sample_image, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "REQUIRE_AGRONOMIST_APPROVAL", False)
    monkeypatch.setattr(get_settings(), "AUTO_APPROVE_CONFIDENCE_THRESHOLD", 0.99)

    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )
    assert create_response.status_code == 201
    pred_id = create_response.json()["id"]

    detail_response = await client.get(f"/api/v1/predictions/{pred_id}")
    assert detail_response.status_code == 200
    data = detail_response.json()
    assert data["status"] == "PENDING_REVIEW"
    assert data["predicted_disease"] == "Pending Review"
    assert data["confidence"] == 0.0

@pytest.mark.asyncio
async def test_admin_can_review_prediction(client, sample_image, monkeypatch):
    import uuid
    from app.main import app
    from app.core.dependencies import get_current_agronomist
    from app.models.user import User

    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "AUTO_APPROVE_CONFIDENCE_THRESHOLD", 0.99)

    create_response = await client.post(
        "/api/v1/predictions",
        files={"image": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")},
        data={"crop_type": "Wheat", "farmer_notes": "Rust spots"},
    )
    pred_id = create_response.json()["id"]

    admin_user = User(
        id=uuid.uuid4(),
        username="test_admin",
        password_hash="mock_hash",
        role="ADMIN"
    )
    app.dependency_overrides[get_current_agronomist] = lambda: admin_user

    try:
        review_response = await client.post(
            f"/api/v1/predictions/{pred_id}/review",
            json={
                "predicted_disease": "Yellow Rust",
                "severity": "High",
                "review": "Admin verified advisory."
            }
        )
        assert review_response.status_code == 200
        assert review_response.json()["status"] == "REVIEWED"
        assert review_response.json()["agronomist_review"] == "Admin verified advisory."
    finally:
        from tests.conftest import override_get_current_agronomist
        app.dependency_overrides[get_current_agronomist] = override_get_current_agronomist

