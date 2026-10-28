
from app.traffic_service import classify_density

test_values = [0, 3, 4.9, 5, 10, 14.9, 15, 20]

for vehicles in test_values:
    result = classify_density(vehicles)
    print(f"{vehicles} vehicles -> {result}")
