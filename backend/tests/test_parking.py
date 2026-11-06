"""Automated tests (pytest + FastAPI TestClient).

Every test uses a fresh in-memory SQLite database and a temporary folder for
processed images, so tests never touch your real ``parking.db``.
The test images are synthetic drawings created by ``scripts/generate_samples.py``.
"""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers tables)
from app.config import settings
from app.database import Base, get_db
from app.detector import EdgeDensityDetector, SpaceRegion
from app.main import app
from app.services import StatusDebouncer, calculate_summary
from app.detector import DetectionResult
from scripts.generate_samples import SAMPLE_SPACES, render_lot

PARTIAL_OCCUPIED = [0, 2, 3, 6, 8]  # 0-based indexes of cars in the partial lot


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #
@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "processed_images_dir", tmp_path / "processed")
    yield TestClient(app)  # no "with": skips start-up so the real DB is untouched
    app.dependency_overrides.clear()
    engine.dispose()


def add_sample_spaces(client, count=10):
    ids = []
    for space in SAMPLE_SPACES[:count]:
        response = client.post("/api/parking/spaces", json=space)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


def png_bytes(image):
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def post_image(client, image, **kwargs):
    return client.post(
        "/api/parking/detect/image",
        files={"file": ("lot.png", png_bytes(image), "image/png")},
        **kwargs,
    )


def statuses(client):
    return {s["id"]: s["status"] for s in client.get("/api/parking/spaces").json()}


# --------------------------------------------------------------------------- #
# General endpoints
# --------------------------------------------------------------------------- #
def test_root_and_health(client):
    root = client.get("/")
    assert root.status_code == 200
    assert "Welcome" in root.json()["message"]
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


# --------------------------------------------------------------------------- #
# Creating and retrieving parking spaces
# --------------------------------------------------------------------------- #
def test_create_parking_space(client):
    payload = {"name": "Space A", "x": 10, "y": 20, "width": 100, "height": 150}
    response = client.post("/api/parking/spaces", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["status"] == "vacant"
    assert body["last_updated"]
    assert {k: body[k] for k in payload} == payload


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "A", "x": -1, "y": 0, "width": 10, "height": 10},  # negative x
        {"name": "A", "x": 0, "y": -5, "width": 10, "height": 10},  # negative y
        {"name": "A", "x": 0, "y": 0, "width": 0, "height": 10},  # zero width
        {"name": "A", "x": 0, "y": 0, "width": 10, "height": -3},  # negative height
        {"name": "   ", "x": 0, "y": 0, "width": 10, "height": 10},  # blank name
        {"name": "A", "x": 0, "y": 0, "width": 10},  # missing height
    ],
)
def test_create_rejects_invalid_values(client, bad):
    assert client.post("/api/parking/spaces", json=bad).status_code == 422
    assert client.get("/api/parking/spaces").json() == []


def test_get_all_and_single_space(client):
    assert client.get("/api/parking/spaces").json() == []
    ids = add_sample_spaces(client, 3)
    all_spaces = client.get("/api/parking/spaces").json()
    assert [s["id"] for s in all_spaces] == ids
    assert all(s["status"] == "vacant" for s in all_spaces)
    single = client.get(f"/api/parking/spaces/{ids[1]}")
    assert single.status_code == 200
    assert single.json()["name"] == "Parking Space 2"


# --------------------------------------------------------------------------- #
# Invalid ids
# --------------------------------------------------------------------------- #
def test_missing_space_returns_404(client):
    assert client.get("/api/parking/spaces/999").status_code == 404
    assert client.put("/api/parking/spaces/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/parking/spaces/999").status_code == 404


@pytest.mark.parametrize("bad_id", ["abc", "0", "-4", "1.5"])
def test_invalid_id_format_returns_422(client, bad_id):
    assert client.get(f"/api/parking/spaces/{bad_id}").status_code == 422


# --------------------------------------------------------------------------- #
# Updating and deleting
# --------------------------------------------------------------------------- #
def test_update_space_details_and_status(client):
    space_id = add_sample_spaces(client, 1)[0]
    before = client.get(f"/api/parking/spaces/{space_id}").json()

    response = client.put(
        f"/api/parking/spaces/{space_id}",
        json={"name": "VIP", "x": 5, "status": "occupied"},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["x"], body["status"]) == ("VIP", 5, "occupied")
    assert body["y"] == before["y"]  # untouched fields stay the same
    assert body["last_updated"] >= before["last_updated"]
    assert client.get("/api/parking/summary").json()["occupied_spaces"] == 1

    # and back to vacant
    client.put(f"/api/parking/spaces/{space_id}", json={"status": "vacant"})
    assert client.get("/api/parking/summary").json()["occupied_spaces"] == 0


@pytest.mark.parametrize(
    "bad",
    [{}, {"status": "broken"}, {"x": -1}, {"width": 0}, {"height": -2}],
)
def test_update_rejects_invalid_body(client, bad):
    space_id = add_sample_spaces(client, 1)[0]
    assert client.put(f"/api/parking/spaces/{space_id}", json=bad).status_code == 422


def test_delete_space(client):
    ids = add_sample_spaces(client, 2)
    assert client.delete(f"/api/parking/spaces/{ids[0]}").status_code == 204
    assert client.get(f"/api/parking/spaces/{ids[0]}").status_code == 404
    assert len(client.get("/api/parking/spaces").json()) == 1
    assert client.get("/api/parking/summary").json()["total_spaces"] == 1


# --------------------------------------------------------------------------- #
# Summary calculation
# --------------------------------------------------------------------------- #
def test_summary_for_empty_configuration(client):
    response = client.get("/api/parking/summary")
    assert response.status_code == 200
    assert response.json() == {
        "total_spaces": 0,
        "occupied_spaces": 0,
        "available_spaces": 0,
        "occupancy_percentage": 0.0,
        "availability_percentage": 0.0,
    }


def test_summary_counts_and_percentages(client):
    ids = add_sample_spaces(client, 4)
    client.put(f"/api/parking/spaces/{ids[0]}", json={"status": "occupied"})
    summary = client.get("/api/parking/summary").json()
    assert summary == {
        "total_spaces": 4,
        "occupied_spaces": 1,
        "available_spaces": 3,
        "occupancy_percentage": 25.0,
        "availability_percentage": 75.0,
    }


def test_calculate_summary_formulas():
    assert calculate_summary(50, 30).model_dump() == {
        "total_spaces": 50,
        "occupied_spaces": 30,
        "available_spaces": 20,
        "occupancy_percentage": 60.0,
        "availability_percentage": 40.0,
    }
    zero = calculate_summary(0, 0)
    assert zero.occupancy_percentage == 0.0 and zero.availability_percentage == 0.0
    third = calculate_summary(3, 1)
    assert third.occupancy_percentage + third.availability_percentage == pytest.approx(100)


# --------------------------------------------------------------------------- #
# Image detection
# --------------------------------------------------------------------------- #
def test_detect_image_marks_occupied_and_vacant(client):
    ids = add_sample_spaces(client)
    response = post_image(client, render_lot(PARTIAL_OCCUPIED))
    assert response.status_code == 200
    body = response.json()

    expected = {ids[i]: ("occupied" if i in PARTIAL_OCCUPIED else "vacant") for i in range(10)}
    assert statuses(client) == expected
    assert {r["space_id"]: r["status"] for r in body["results"]} == expected
    assert body["status_changes"] == len(PARTIAL_OCCUPIED)
    assert body["summary"] == {
        "total_spaces": 10,
        "occupied_spaces": 5,
        "available_spaces": 5,
        "occupancy_percentage": 50.0,
        "availability_percentage": 50.0,
    }
    # the summary endpoint agrees with what the detection response said
    assert client.get("/api/parking/summary").json() == body["summary"]


def test_detect_image_empty_and_full_lots(client):
    add_sample_spaces(client)
    full = post_image(client, render_lot(range(10))).json()
    assert full["summary"]["occupied_spaces"] == 10
    assert full["summary"]["availability_percentage"] == 0.0
    empty = post_image(client, render_lot([])).json()
    assert empty["summary"]["occupied_spaces"] == 0
    assert empty["summary"]["availability_percentage"] == 100.0
    assert empty["status_changes"] == 10  # every car left


def test_same_image_twice_causes_no_database_changes(client):
    add_sample_spaces(client)
    image = render_lot(PARTIAL_OCCUPIED)
    post_image(client, image)
    before = client.get("/api/parking/spaces").json()
    second = post_image(client, image).json()
    after = client.get("/api/parking/spaces").json()
    assert second["status_changes"] == 0
    assert all(not r["changed"] for r in second["results"])
    assert before == after  # statuses AND last_updated timestamps untouched


def test_detect_image_status_change_updates_timestamp(client):
    ids = add_sample_spaces(client)
    post_image(client, render_lot([]))
    old = client.get(f"/api/parking/spaces/{ids[0]}").json()["last_updated"]
    post_image(client, render_lot([0]))  # car arrives in space 1
    new = client.get(f"/api/parking/spaces/{ids[0]}").json()
    assert new["status"] == "occupied"
    assert new["last_updated"] > old


def test_processed_image_is_red_and_green(client):
    add_sample_spaces(client)
    response = post_image(client, render_lot(PARTIAL_OCCUPIED))
    url = response.json()["processed_image_url"]
    image_response = client.get(url)
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    image = cv2.imdecode(np.frombuffer(image_response.content, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == (500, 800, 3)
    # Pixels on the left edge of space 1 (occupied) are red, of space 2 (vacant) green.
    s1, s2 = SAMPLE_SPACES[0], SAMPLE_SPACES[1]
    assert tuple(image[s1["y"] + 80, s1["x"]]) == (0, 0, 255)
    assert tuple(image[s2["y"] + 80, s2["x"]]) == (0, 255, 0)


def test_detect_image_can_return_png_directly(client):
    add_sample_spaces(client)
    response = post_image(client, render_lot(PARTIAL_OCCUPIED), params={"return_image": "true"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-occupied-spaces"] == "5"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_processed_image_endpoint_rejects_bad_names(client):
    assert client.get("/api/parking/processed/missing.png").status_code == 404
    assert client.get("/api/parking/processed/..%2Fsecret.png").status_code == 404


def test_space_outside_image_is_skipped_with_warning(client):
    ids = add_sample_spaces(client, 2)
    far = client.post(
        "/api/parking/spaces",
        json={"name": "Off-screen", "x": 5000, "y": 5000, "width": 100, "height": 100},
    ).json()
    body = post_image(client, render_lot([0])).json()
    assert body["spaces_processed"] == 2
    assert any("Off-screen" in w for w in body["warnings"])
    assert client.get(f"/api/parking/spaces/{far['id']}").json()["status"] == "vacant"
    assert statuses(client)[ids[0]] == "occupied"


# --------------------------------------------------------------------------- #
# Invalid uploads and empty configuration
# --------------------------------------------------------------------------- #
def test_detect_image_rejects_wrong_file_type(client):
    add_sample_spaces(client)
    response = client.post(
        "/api/parking/detect/image",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_detect_image_rejects_corrupt_image(client):
    add_sample_spaces(client)
    response = client.post(
        "/api/parking/detect/image",
        files={"file": ("broken.png", b"this is not a picture", "image/png")},
    )
    assert response.status_code == 400
    empty = client.post(
        "/api/parking/detect/image", files={"file": ("empty.png", b"", "image/png")}
    )
    assert empty.status_code == 400


def test_detect_image_requires_a_file(client):
    assert client.post("/api/parking/detect/image").status_code == 422


def test_detect_with_no_spaces_configured(client):
    response = post_image(client, render_lot([0]))
    assert response.status_code == 400
    assert "No parking spaces" in response.json()["detail"]
    assert client.get("/api/parking/summary").json()["total_spaces"] == 0
    assert client.post("/api/parking/detect/simulate", json={}).status_code == 400


def test_upload_size_limit(client, monkeypatch):
    add_sample_spaces(client)
    monkeypatch.setattr(settings, "max_image_size_mb", 1)
    big = b"\x00" * (1024 * 1024 + 10)
    response = client.post(
        "/api/parking/detect/image", files={"file": ("big.png", big, "image/png")}
    )
    assert response.status_code == 413


# --------------------------------------------------------------------------- #
# Video detection
# --------------------------------------------------------------------------- #
def make_video(path, frames_spec, fps=10):
    """``frames_spec`` is a list of occupied-index lists, one per video frame."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (800, 500))
    if not writer.isOpened():
        pytest.skip("This OpenCV build cannot write test videos.")
    for i, occupied in enumerate(frames_spec):
        writer.write(render_lot(occupied, noise_seed=i))
    writer.release()
    return path


def post_video(client, path, **params):
    return client.post(
        "/api/parking/detect/video",
        files={"file": (path.name, path.read_bytes(), "video/x-msvideo")},
        params=params,
    )


def test_detect_video_updates_to_latest_state(client, tmp_path):
    add_sample_spaces(client)
    video = make_video(tmp_path / "lot.avi", [[0, 2]] * 5 + [[0, 2, 5]] * 5)
    response = post_video(client, video, frame_interval=2)
    assert response.status_code == 200
    body = response.json()
    assert body["frames_read"] == 10
    assert body["frames_processed"] == 5  # frames 0, 2, 4, 6, 8
    assert body["frame_interval"] == 2
    assert body["summary"]["occupied_spaces"] == 3
    occupied = {r["space_id"] for r in body["results"] if r["status"] == "occupied"}
    assert occupied == {1, 3, 6}
    assert body["status_changes"] == 3
    assert client.get(body["processed_image_url"]).status_code == 200


def test_video_interval_skips_frames_and_confirm_frames_debounces(client, tmp_path):
    add_sample_spaces(client)
    # Space 6 is occupied in only ONE frame (frame 3), a flicker.
    spec = [[0]] * 3 + [[0, 5]] + [[0]] * 4
    video = make_video(tmp_path / "flicker.avi", spec)

    immediate = post_video(client, video, frame_interval=1, confirm_frames=1).json()
    assert immediate["summary"]["occupied_spaces"] == 1  # flicker came and went
    # It was written twice (vacant->occupied->vacant), but the final state is right.

    # Interval 10 analyses only frame 0.
    client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0})
    sparse = post_video(client, video, frame_interval=10).json()
    assert sparse["frames_processed"] == 1

    # With confirm_frames=2 the one-frame flicker is never saved.
    client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0})
    debounced = post_video(client, video, frame_interval=1, confirm_frames=2).json()
    assert debounced["status_changes"] == 1  # only space 1, space 6 never confirmed
    assert statuses(client)[6] == "vacant"


def test_video_rejects_bad_files(client, tmp_path):
    add_sample_spaces(client)
    wrong_type = client.post(
        "/api/parking/detect/video",
        files={"file": ("clip.txt", b"abc", "text/plain")},
    )
    assert wrong_type.status_code == 415
    corrupt = client.post(
        "/api/parking/detect/video",
        files={"file": ("clip.mp4", b"not really a video" * 50, "video/mp4")},
    )
    assert corrupt.status_code == 400
    bad_interval = client.post(
        "/api/parking/detect/video",
        params={"frame_interval": 0},
        files={"file": ("clip.mp4", b"x", "video/mp4")},
    )
    assert bad_interval.status_code == 422


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def test_simulation_changes_occupancy(client):
    add_sample_spaces(client)
    half = client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0.5, "seed": 1})
    assert half.status_code == 200
    body = half.json()
    assert body["detector"] == "simulation"
    assert body["summary"]["occupied_spaces"] == 5
    assert body["summary"]["available_spaces"] == 5
    assert client.get("/api/parking/summary").json() == body["summary"]

    assert client.post("/api/parking/detect/simulate", json={"occupancy_rate": 1}).json()[
        "summary"
    ]["occupied_spaces"] == 10
    assert client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0}).json()[
        "summary"
    ]["occupied_spaces"] == 0


def test_simulation_is_repeatable_with_a_seed(client):
    add_sample_spaces(client)
    client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0.4, "seed": 42})
    first = statuses(client)
    client.post("/api/parking/detect/simulate", json={"occupancy_rate": 0.4, "seed": 42})
    assert statuses(client) == first
    assert list(first.values()).count("occupied") == 4


def test_simulation_defaults_and_validation(client):
    add_sample_spaces(client)
    assert client.post("/api/parking/detect/simulate").status_code == 200  # no body
    assert client.post("/api/parking/detect/simulate", json={"occupancy_rate": 1.5}).status_code == 422
    assert client.post("/api/parking/detect/simulate", json={"occupancy_rate": -0.1}).status_code == 422


# --------------------------------------------------------------------------- #
# Detector and helper unit tests
# --------------------------------------------------------------------------- #
def test_detector_scores_cars_higher_than_empty_ground():
    regions = [
        SpaceRegion(i + 1, s["name"], s["x"], s["y"], s["width"], s["height"])
        for i, s in enumerate(SAMPLE_SPACES)
    ]
    results = EdgeDensityDetector().detect(render_lot(PARTIAL_OCCUPIED), regions)
    for i, result in enumerate(results):
        assert result.status == ("occupied" if i in PARTIAL_OCCUPIED else "vacant")
    occupied_scores = [results[i].score for i in PARTIAL_OCCUPIED]
    vacant_scores = [r.score for i, r in enumerate(results) if i not in PARTIAL_OCCUPIED]
    assert min(occupied_scores) > max(vacant_scores)


def test_detector_handles_grayscale_and_out_of_bounds():
    gray = cv2.cvtColor(render_lot([0]), cv2.COLOR_BGR2GRAY)
    regions = [
        SpaceRegion(1, "in", **{k: SAMPLE_SPACES[0][k] for k in ("x", "y", "width", "height")}),
        SpaceRegion(2, "out", 9000, 9000, 50, 50),
    ]
    results = EdgeDensityDetector().detect(gray, regions)
    assert results[0].status == "occupied"
    assert results[1].status is None and results[1].note


def test_status_debouncer_requires_consecutive_confirmations():
    debouncer = StatusDebouncer({1: "vacant"}, confirm_frames=3)
    occ = [DetectionResult(1, "occupied", 0.1)]
    vac = [DetectionResult(1, "vacant", 0.0)]
    assert debouncer.update(occ) == {}
    assert debouncer.update(occ) == {}
    assert debouncer.update(vac) == {}  # flicker resets the count
    assert debouncer.update(occ) == {}
    assert debouncer.update(occ) == {}
    assert debouncer.update(occ) == {1: "occupied"}
    assert debouncer.update(occ) == {}  # already saved, nothing new
