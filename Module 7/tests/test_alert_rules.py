from app.main import read, check_parking, check_roads, check_devices
def test_parking_alert(): assert any(a['alert_type']=='parking_nearly_full' for a in check_parking(read()))
def test_congestion_alert(): assert any(a['alert_type']=='severe_congestion' for a in check_roads(read()))
def test_device_alert(): assert any(a['alert_type'] in ('camera_unavailable','sensor_failure') for a in check_devices(read()))
