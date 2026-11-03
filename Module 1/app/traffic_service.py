import cv2
from pathlib import Path

from app.ai_component import VehicleDetector, process_video
from app.ai_component.density import classify_density


def analyze_video(
    video_path,
    show_window=False,
    output_path=None,
):
    """Analyze a traffic video using the TraffiQ AI component."""

    video_path = Path(video_path)

    if not video_path.is_file():
        raise RuntimeError(
            "Video file not found. Check the uploaded file."
        )

    # Read the video's metadata.
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(
            "Could not open video. Check the video file and path."
        )

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        total_frames = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        )
    finally:
        cap.release()

    # Calculate the video duration.
    duration = (
        round(total_frames / fps, 2)
        if fps > 0 and total_frames > 0
        else None
    )

    # Initialize the vehicle detector.
    detector = VehicleDetector()

    try:
        result = process_video(
            source=str(video_path),
            detector=detector,
            display=show_window,
            output_path=output_path,
        )

    except (ValueError, OSError) as exc:
        raise RuntimeError(str(exc)) from exc

    # Retrieve the average vehicle count.
    average_total = result["average_vehicles_per_frame"]

    # Use the shared density-classification function.
    traffic_density = classify_density(average_total)

    # Return the API analysis results.
    return {
        "frames_processed": result["frames_processed"],

        "video_duration_seconds": duration,

        "fps": round(fps, 2) if fps > 0 else None,

        "average_vehicles_per_frame_by_class":
            result["average_vehicles_per_frame_by_class"],

        "average_vehicles_per_frame": average_total,

        "max_vehicles_in_frame":
            result["max_vehicles_in_frame"],

        # Convert the zero-based index into a one-based frame number.
        "max_count_frame_number": (
            result["max_count_frame_number"] + 1
            if result["max_count_frame_number"] is not None
            else None
        ),

        # Counts from the frame with the highest total.
        "max_frame_counts_by_class":
            result["max_frame_counts_by_class"],

        # Maximum count observed for each vehicle class.
        "maximum_per_class_counts":
            result["maximum_per_class_counts"],

        # Estimated distinct vehicles based on tracking IDs.
        "unique_tracked_vehicles_by_class":
            result["unique_tracked_vehicles_by_class"],

        # Counts from the last processed frame.
        "last_frame_counts_by_class":
            result["last_frame_counts_by_class"],

        "traffic_density": traffic_density,

        "density_note": (
            "Demo thresholds only; calibrate for each camera/road."
        ),

        "counting_note": (
            "Per-frame counts, maximum frame count, and unique "
            "tracked IDs are different measures. Tracking estimates "
            "distinct vehicles and can be affected by occlusion "
            "or ID switches."
        ),
    }