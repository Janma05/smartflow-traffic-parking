
from pathlib import Path
from app.ml.traffic_prediction import analyze_history, load_data

def test_history_file_loads():
    path = Path(__file__).resolve().parents[1] / "data" / "traffic_history.csv"
    df = load_data(str(path))
    assert len(df) > 0
    assert {"timestamp", "vehicle_count", "location_id"}.issubset(df.columns)

def test_analysis_has_peak_and_patterns():
    path = Path(__file__).resolve().parents[1] / "data" / "traffic_history.csv"
    result = analyze_history(str(path))
    assert result["records_analyzed"] > 0
    assert "busiest_average_hour" in result
    assert len(result["recurring_busy_periods"]) > 0
