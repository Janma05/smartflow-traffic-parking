"""Generate SYNTHETIC sample data for testing (no real camera needed).

Creates in ``parking_images/``:
  * empty_lot.png, partial_lot.png, full_lot.png  - a drawn parking lot
  * sample_parking_video.mp4                       - cars arrive and leave
  * sample_spaces.json                             - the 10 space rectangles

These are drawings, not photos. They prove the pipeline works; they say
nothing about accuracy on real parking-lot footage.

Run from the project root:   python -m scripts.generate_samples
"""

import json
from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np

IMAGE_WIDTH, IMAGE_HEIGHT = 800, 500
COLUMNS = 5
SPACE_W, SPACE_H = 130, 170
X0, X_PITCH = 40, 148
ROW_Y = (30, 300)

# 10 spaces: 2 rows x 5 columns. Same format the POST /spaces endpoint accepts.
SAMPLE_SPACES = [
    {
        "name": f"Parking Space {i + 1}",
        "x": X0 + (i % COLUMNS) * X_PITCH,
        "y": ROW_Y[i // COLUMNS],
        "width": SPACE_W,
        "height": SPACE_H,
    }
    for i in range(10)
]

CAR_COLORS_BGR = [
    (40, 40, 200),  # red
    (180, 90, 30),  # blue
    (225, 225, 225),  # white
    (35, 35, 35),  # black
    (170, 170, 170),  # silver
    (60, 140, 60),  # green
    (40, 200, 220),  # yellow
]


def _draw_car(img: np.ndarray, space: dict, index: int, seed: int) -> None:
    x, y, w, h = space["x"], space["y"], space["width"], space["height"]
    body = CAR_COLORS_BGR[(index * 3 + seed) % len(CAR_COLORS_BGR)]
    dark = tuple(int(c * 0.45) for c in body)
    light = tuple(min(255, int(c * 1.25) + 15) for c in body)
    glass = (50, 45, 40)

    bx0, bx1, by0, by1 = x + 16, x + w - 16, y + 10, y + h - 10
    # wheels
    for wy in (by0 + 28, by1 - 46):
        cv2.rectangle(img, (bx0 - 6, wy), (bx0 + 2, wy + 26), (20, 20, 20), -1)
        cv2.rectangle(img, (bx1 - 2, wy), (bx1 + 6, wy + 26), (20, 20, 20), -1)
    # body, bonnet and boot lines
    cv2.rectangle(img, (bx0, by0), (bx1, by1), body, -1)
    cv2.rectangle(img, (bx0, by0), (bx1, by1), dark, 2)
    cv2.line(img, (bx0 + 6, by0 + 22), (bx1 - 6, by0 + 22), dark, 2)
    cv2.line(img, (bx0 + 6, by1 - 22), (bx1 - 6, by1 - 22), dark, 2)
    # windscreen, roof, rear window
    cv2.rectangle(img, (bx0 + 8, by0 + 28), (bx1 - 8, by0 + 52), glass, -1)
    cv2.rectangle(img, (bx0 + 8, by0 + 54), (bx1 - 8, by1 - 54), light, -1)
    cv2.rectangle(img, (bx0 + 8, by0 + 54), (bx1 - 8, by1 - 54), dark, 1)
    cv2.rectangle(img, (bx0 + 8, by1 - 52), (bx1 - 8, by1 - 28), glass, -1)
    # lights and number plate
    cv2.rectangle(img, (bx0 + 3, by0 + 3), (bx0 + 16, by0 + 12), (200, 255, 255), -1)
    cv2.rectangle(img, (bx1 - 16, by0 + 3), (bx1 - 3, by0 + 12), (200, 255, 255), -1)
    cv2.rectangle(img, (bx0 + 3, by1 - 12), (bx0 + 16, by1 - 3), (30, 30, 220), -1)
    cv2.rectangle(img, (bx1 - 16, by1 - 12), (bx1 - 3, by1 - 3), (30, 30, 220), -1)
    cv2.rectangle(img, (x + w // 2 - 14, by1 - 12), (x + w // 2 + 14, by1 - 3), (235, 235, 235), -1)


def render_lot(
    occupied_indices: Iterable[int],
    seed: int = 7,
    noise_seed: Optional[int] = None,
) -> np.ndarray:
    """Draw the lot. ``occupied_indices`` are 0-based positions in SAMPLE_SPACES."""
    rng = np.random.default_rng(seed)
    blotch = rng.normal(0, 1, (IMAGE_HEIGHT // 25 + 2, IMAGE_WIDTH // 25 + 2))
    blotch = cv2.resize(
        blotch.astype(np.float32), (IMAGE_WIDTH, IMAGE_HEIGHT), interpolation=cv2.INTER_CUBIC
    )
    asphalt = 100 + blotch * 5
    img = np.clip(np.repeat(asphalt[:, :, None], 3, axis=2), 0, 255).astype(np.uint8)

    # soft shadow across the top row (vacant spaces must survive it)
    shadow = img.copy()
    cv2.fillPoly(shadow, [np.array([[0, 0], [260, 0], [200, 210], [0, 210]])], (70, 70, 70))
    img = cv2.addWeighted(shadow, 0.35, img, 0.65, 0)
    img = cv2.GaussianBlur(img, (0, 0), 6)

    for s in SAMPLE_SPACES:  # painted white lines
        x, y, w, h = s["x"], s["y"], s["width"], s["height"]
        cv2.line(img, (x, y), (x, y + h), (235, 235, 235), 3)
        cv2.line(img, (x + w, y), (x + w, y + h), (235, 235, 235), 3)
        back_y = y if y < IMAGE_HEIGHT // 2 else y + h
        cv2.line(img, (x, back_y), (x + w, back_y), (235, 235, 235), 3)

    for i in sorted(set(occupied_indices)):
        _draw_car(img, SAMPLE_SPACES[i], i, seed)

    noise_rng = np.random.default_rng(seed if noise_seed is None else noise_seed)
    noisy = img.astype(np.float32) + noise_rng.normal(0, 3, img.shape)
    return np.clip(noisy, 0, 255).astype(np.uint8)


def _occupied_at(frame: int) -> set[int]:
    occupied = {0, 2, 3, 6, 8}
    if frame >= 15:
        occupied.add(1)  # a car arrives
    if frame >= 30:
        occupied.discard(0)  # a car leaves
    if frame >= 45:
        occupied.add(4)  # another arrives
    return occupied


def write_video(path: Path, frames: int = 60, fps: int = 10) -> bool:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (IMAGE_WIDTH, IMAGE_HEIGHT)
    )
    if not writer.isOpened():
        return False
    for f in range(frames):
        writer.write(render_lot(_occupied_at(f), noise_seed=1000 + f))
    writer.release()
    return path.exists() and path.stat().st_size > 0


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "parking_images"
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / "empty_lot.png"), render_lot([]))
    cv2.imwrite(str(out / "partial_lot.png"), render_lot([0, 2, 3, 6, 8]))
    cv2.imwrite(str(out / "full_lot.png"), render_lot(range(10)))
    (out / "sample_spaces.json").write_text(json.dumps(SAMPLE_SPACES, indent=2))
    if write_video(out / "sample_parking_video.mp4"):
        print("Wrote sample_parking_video.mp4")
    else:
        print("Could not write the mp4 video with this OpenCV build (skipped).")
    print(f"Sample files written to {out}")
    print("Partial lot has cars in spaces 1, 3, 4, 7 and 9 (5 occupied, 5 vacant).")


if __name__ == "__main__":
    main()
