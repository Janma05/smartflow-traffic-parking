def classify_density(average_vehicles: float) -> str:
    """Classify traffic density using the current demo thresholds.

    Calibrate these thresholds for the selected camera/road before production use.
    """
    if average_vehicles < 5:
        return "Low"
    if average_vehicles < 15:
        return "Medium"
    return "High"

