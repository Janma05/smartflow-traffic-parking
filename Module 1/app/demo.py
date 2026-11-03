import argparse
from app.traffic_service import analyze_video

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TraffiQ traffic-monitoring demo")
    parser.add_argument("video", help="Path to a traffic video")
    args = parser.parse_args()
    result = analyze_video(args.video, show_window=True)
    print("\\n=== TraffiQ Traffic Monitoring Result ===")
    for key, value in result.items():
        print(f"{key}: {value}")
