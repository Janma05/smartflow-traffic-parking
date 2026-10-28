from pathlib import Path

import cv2

from .vehicle_detection import VEHICLE_CLASSES
from .density import classify_density


def process_video(
    source,
    detector,
    display=False,
    output_path=None,
    sample_every=1,
    quit_key="q",
):
    """Process a recorded video or camera source."""

    if sample_every < 1:
        raise ValueError("sample_every must be at least 1")

    cap = cv2.VideoCapture(
        str(source) if isinstance(source, Path) else source
    )

    if not cap.isOpened():
        cap.release()
        raise ValueError(
            f"Could not open video/camera source: {source}"
        )

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    names = list(VEHICLE_CLASSES.values())

    totals = {name: 0 for name in names}
    max_counts = {name: 0 for name in names}
    unique_ids = {name: set() for name in names}

    frames_processed = 0
    max_total = 0
    max_frame_number = None

    max_frame_counts = {name: 0 for name in names}
    last_frame_counts = {name: 0 for name in names}

    frame_index = 0
    writer = None

    if output_path:
        if width <= 0 or height <= 0:
            cap.release()
            raise ValueError(
                "Could not read video dimensions for output."
            )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        output_fps = fps if fps > 0 else 25.0

        writer = cv2.VideoWriter(
            str(output),
            cv2.VideoWriter_fourcc(*"mp4v"),
            output_fps,
            (width, height),
        )

        if not writer.isOpened():
            cap.release()
            raise ValueError(
                f"Could not create annotated output video: {output}"
            )

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            current_index = frame_index
            frame_index += 1

            if current_index % sample_every != 0:
                continue

            annotated, counts, tracks = detector.process_frame(frame)

            frames_processed += 1
            total = sum(counts.values())

            last_frame_counts = dict(counts)

            for name in names:
                totals[name] += counts[name]
                max_counts[name] = max(
                    max_counts[name],
                    counts[name],
                )

            if max_frame_number is None or total > max_total:
                max_total = total
                max_frame_number = current_index
                max_frame_counts = dict(counts)

            for track in tracks:
                track_id = track.get("track_id")
                vehicle_class = track.get("class")

                if (
                    track_id is not None
                    and vehicle_class in unique_ids
                ):
                    unique_ids[vehicle_class].add(track_id)

            # Calculate current-frame traffic density.
            density = classify_density(total)

            # Compact information panel: four lines instead of eight.
            panel_lines = [
                "TRAFFIQ | LIVE TRAFFIC",
                (
                    f"Cars: {counts.get('car', 0)}  |  "
                    f"Bikes: {counts.get('bicycle', 0)}  |  "
                    f"Motorcycles: {counts.get('motorcycle', 0)}"
                ),
                (
                    f"Buses: {counts.get('bus', 0)}  |  "
                    f"Trucks: {counts.get('truck', 0)}"
                ),
                f"Vehicles: {total}  |  Density: {density}",
            ]

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.43
            thickness = 1
            padding = 8
            line_height = 19
            margin = 10

            frame_height, frame_width = annotated.shape[:2]

            # Keep the panel within the video frame.
            available_width = max(1, frame_width - 2 * margin)

            text_widths = [
                cv2.getTextSize(
                    line,
                    font,
                    font_scale,
                    thickness,
                )[0][0]
                for line in panel_lines
            ]

            panel_width = min(
                max(text_widths) + 2 * padding,
                available_width,
            )

            panel_height = min(
                len(panel_lines) * line_height + 2 * padding,
                max(1, frame_height - 2 * margin),
            )

            # Position at the top-left to avoid covering road traffic
            # near the bottom of the frame.
            panel_x = margin
            panel_y = margin

            panel_right = min(
                panel_x + panel_width,
                frame_width - 1,
            )
            panel_bottom = min(
                panel_y + panel_height,
                frame_height - 1,
            )

            # Draw a dark translucent background.
            overlay = annotated.copy()

            cv2.rectangle(
                overlay,
                (panel_x, panel_y),
                (panel_right, panel_bottom),
                (25, 25, 25),
                -1,
            )

            cv2.addWeighted(
                overlay,
                0.78,
                annotated,
                0.22,
                0,
                annotated,
            )

            # Draw panel text.
            for index, line in enumerate(panel_lines):
                text_x = panel_x + padding
                text_y = (
                    panel_y
                    + padding
                    + (index + 1) * line_height
                    - 4
                )

                if text_y >= frame_height:
                    break

                # Keep text within the right edge of the frame.
                max_text_width = max(
                    1,
                    frame_width - text_x - padding,
                )

                if index == 0:
                    text_color = (255, 255, 255)
                elif index == len(panel_lines) - 1:
                    if density == "Low":
                        text_color = (0, 255, 0)
                    elif density == "Medium":
                        text_color = (0, 165, 255)
                    else:
                        text_color = (0, 0, 255)
                else:
                    text_color = (0, 255, 0)

                # If a line is too long, shorten it safely.
                display_line = line

                while display_line and cv2.getTextSize(
                    display_line,
                    font,
                    font_scale,
                    thickness,
                )[0][0] > max_text_width:
                    display_line = display_line[:-1]

                cv2.putText(
                    annotated,
                    display_line,
                    (text_x, text_y),
                    font,
                    font_scale,
                    text_color,
                    thickness,
                    cv2.LINE_AA,
                )

            if writer is not None:
                writer.write(annotated)

            if display:
                cv2.imshow(
                    "TraffiQ - AI Traffic Monitoring",
                    annotated,
                )

                if cv2.waitKey(1) & 0xFF == ord(quit_key):
                    break

    finally:
        cap.release()

        if writer is not None:
            writer.release()

        if display:
            cv2.destroyAllWindows()

    # Calculate average vehicle counts across processed frames.
    averages = {
        name: (
            round(totals[name] / frames_processed, 2)
            if frames_processed
            else 0
        )
        for name in names
    }

    average_total = round(sum(averages.values()), 2)

    return {
        "frames_processed": frames_processed,
        "source_fps": round(fps, 2),
        "average_vehicles_per_frame_by_class": averages,
        "average_vehicles_per_frame": average_total,
        "max_vehicles_in_frame": max_total,
        "max_count_frame_number": max_frame_number,
        "max_frame_counts_by_class": max_frame_counts,
        "maximum_per_class_counts": max_counts,
        "last_frame_counts_by_class": last_frame_counts,
        "unique_tracked_vehicles_by_class": {
            name: len(unique_ids[name])
            for name in names
        },
        "traffic_density": classify_density(average_total),
        "density_note": (
            "Demo thresholds; calibrate for each camera/road."
        ),
    }