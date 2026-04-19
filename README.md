# Project Title
**33. Predictive Temperature Model**

## Group Members
* [Member 1 Name]
* [Member 2 Name]
* [Member 3 Name]

## Project Description
This project implements an **Edge AI Predictive Temperature System** designed for industrial IoT monitoring. The core objective is to predict the next temperature value in a time-series sequence based on historical sensor data.

**Regression Logic:**
The system uses a **Simple Linear Regression** model implemented with `scikit-learn`. 
1. **Data Ingestion:** The system maintains a sliding window of the last 10 temperature readings.
2. **Feature Engineering:** Each reading is indexed sequentially (time-steps).
3. **Model Training:** For every new sensor reading, the regression model is re-fitted to the current window.
4. **Prediction:** The model extrapolates the trend to predict the value of the next time-step.
5. **Threshold Monitoring:** The system proactively checks if the predicted value exceeds a safety threshold (35°C) and issues alerts before the anomaly potentially occurs.

## System Architecture
The system is fully containerized using Docker and follows a decoupled microservices architecture:

1.  **Sensor Simulation (Python):** Generates realistic temperature data (sine wave + noise + anomalies) and runs the Edge AI logic.
2.  **MQTT Broker (Mosquitto):** Acts as the central communication hub, allowing the Python service to publish data and alerts.
3.  **Data Pipeline (Node-RED):** Subscribes to MQTT topics, processes incoming JSON payloads, and routes data to the dashboard.
4.  **Dashboard (Node-RED Dashboard):** Provides real-time visualization of actual vs. predicted temperatures, system status, and gauge readings.

**Data Flow:**
`Python (Sim + AI) -> MQTT (sensors/...) -> Node-RED -> Dashboard UI`

## How to Run
Ensure you have **Docker** and **Docker Compose** installed on your system.

1. **Clone the repository** (or navigate to the project folder).
2. **Build and start the containers:**
   ```bash
   docker-compose up --build
   ```
3. **Access the Dashboard:**
   * **Node-RED Editor:** [http://localhost:1880](http://localhost:1880)
   * **Dashboard UI:** [http://localhost:1880/ui](http://localhost:1880/ui)
4. **Access the Broker (Optional):**
   * **MQTT Port:** `1883`

## MQTT Topics Used
| Topic | Payload Description |
|-------|---------------------|
| `sensors/group_33/project33/data` | JSON containing `timestamp`, `actual_temp`, `predicted_temp`, and `is_anomaly`. |
| `alerts/group_33/project33/status` | JSON containing `status` (NORMAL/CRITICAL), `message`, and `predicted_val`. |

## Results (screenshots)
*(Place your dashboard screenshots here after running the system)*
- **Main Dashboard:** `docs/dashboard_main.png`
- **Predictive Chart:** `docs/chart_comparison.png`
- **Alert Status:** `docs/alert_view.png`

## Challenges
* **Noise Handling:** Balancing the regression model to follow the trend without being over-sensitive to random sensor noise.
* **Anomaly Detection vs. Prediction:** Distinguishing between a temporary spike (anomaly) and a genuine upward trend that requires an alert.
* **Container Synchronization:** Ensuring the MQTT broker is fully initialized before the Python service attempts to connect.

## Future Improvements
* **Advanced AI Models:** Replacing Linear Regression with an LSTM (Long Short-Term Memory) neural network for better handling of non-linear seasonal patterns.
* **Edge-to-Cloud Integration:** Forwarding filtered alerts to a cloud-based notification system (like AWS SNS or Telegram Bot).
* **Self-Healing:** Implementing logic to recalibrate the model parameters automatically if prediction error (RMSE) exceeds a certain limit.
