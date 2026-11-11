# SMARTFLOW
## Machine Learning Module 4
### Parking Availability Prediction

## 1. Project Overview
SmartFlow is a smart parking prediction project that uses
Machine Learning and Computer Vision to estimate parking
availability from recorded parking videos.

## 2. Objectives
- Detect vehicles from parking videos.
- Collect vehicle detection observations.
- Estimate occupied and available parking slots.
- Train a Machine Learning prediction model.
- Visualize parking observations.
- Generate a parking prediction report.

## 3. Technologies Used
- Python
- OpenCV
- YOLO
- Pandas
- NumPy
- Scikit-learn
- Matplotlib
- Joblib

## 4. Dataset
Parking lot videos are used to extract frames.
YOLO detects vehicles in the extracted frames.
The observations are stored in a CSV dataset.

## 5. Machine Learning Algorithm
Random Forest Regressor is used to predict
estimated occupied parking slots based on elapsed
video time.

## 6. Prediction
The system accepts video time in seconds and predicts
estimated occupied and available parking slots.

Total Parking Capacity: 20

## 7. Visualization
A graph displays estimated occupied and available
parking slots over video time.

## 8. Output Files
- video_parking_model.pkl
- parking_video_observations.csv
- video_parking_visualization.png
- parking_prediction_report.txt

## 9. Limitations
Vehicle detections are used as estimates of parking
occupancy. The system does not yet verify whether
each detected vehicle is inside a marked parking slot.

The model is a demonstration using a small dataset.
More labelled parking data is required for reliable
real-world predictions.

## 10. Conclusion
SmartFlow Module 4 demonstrates video-based vehicle
detection, parking availability estimation, Machine
Learning prediction, visualization, and report generation.