# Project Title
**33. Predictive Temperature Model**

## Group Members
* [Member 1 Name]
* [Member 2 Name]
* [Member 3 Name]
* [Member 4 Name]

## Project Description
This project implements an **Edge AI Predictive Temperature System** designed for industrial IoT monitoring. The core objective is to analyze and forecast time-series temperature data to proactively identify potential overheating events.

The system is fully containerized using Docker and follows a decoupled microservices architecture centered around an MQTT message broker.

## AI and Predictive Model
The intelligence of this project resides in the `python/main.py` entrypoint and its supporting modules. It uses a machine learning pipeline to deliver reliable forecasts.

**1. Data Preprocessing:**
To ensure forecast stability, the raw sensor data undergoes two preprocessing steps:
*   **Outlier Removal:** It uses **Median Absolute Deviation (MAD)**, a robust statistical method, to identify and clip anomalous spikes in the data. This prevents single outlier events from corrupting the underlying trend.
*   **Data Smoothing:** **Exponential Smoothing** is applied to the cleaned data to reduce random noise and help the model focus on the primary trend.

**2. Predictive Model:**
*   **Algorithm:** The system uses an **Echo State Network (ESN)** style reservoir forecaster to model the temperature trend.
*   **Training:** The readout layer is updated continuously as new samples arrive, using a short rolling history.
*   **Forecasting:** It predicts the temperature at a future point in time (defined by `PREDICTION_HORIZON_SEC`) and calculates the trend slope to classify it as "rising," "falling," or "stable."

**3. Predictive Alerting:**
The primary goal of the AI is to enable proactive alerts. If the forecasted temperature exceeds a configurable safety threshold, the system publishes a **"CRITICAL"** alert. This allows for intervention *before* an issue occurs, moving from reactive to predictive monitoring.

## System Architecture
The system is composed of four main containerized services:

1.  **`mqtt` (Eclipse Mosquitto):** The central MQTT message broker that enables communication between all services.
2.  **`node-red` (Node-RED):** Provides a low-code environment for creating the dashboard UI and managing data flow logic.
3.  **`python-edge` (Python/scikit-learn):** The edge AI service that runs the temperature simulation, data preprocessing, and predictive modeling.
4.  **`telemetry-store` (Python):** A service responsible for subscribing to telemetry topics and logging the data to a persistent database.

**Data Flow:**
`Python (Sim + AI) -> MQTT Broker -> Node-RED -> Dashboard UI`
`Python (Sim + AI) -> MQTT Broker -> Telemetry Store -> Database`

## Potential Use Cases
This project serves as a template for various real-world applications where predictive monitoring is valuable:

*   **Predictive Maintenance:** Monitor industrial machinery (engines, servers) to forecast overheating events, allowing for proactive maintenance that prevents downtime and equipment failure.
*   **Smart Building & HVAC:** Optimize energy consumption by pre-heating or pre-cooling rooms based on predicted temperature trends, enhancing comfort while saving costs.
*   **Cold Chain Logistics:** Ensure the integrity of sensitive goods (food, pharmaceuticals) by predicting temperature deviations in refrigerated containers and alerting operators to take corrective action.
*   **Precision Agriculture:** Manage greenhouse or soil temperatures by predicting harmful conditions, allowing automated systems to trigger irrigation, ventilation, or heating to protect crops.

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
| `sensors/group_33/project33/device_01/data` | JSON containing `device_id`, `timestamp`, `actual_temp`, `predicted_temp`, and `is_anomaly`. |
| `alerts/group_33/project33/device_01/status` | JSON containing `device_id`, `status` (NORMAL/CRITICAL), `message`, and `predicted_val`. |
| `storage/group_33/project33/export` | Topic to command the telemetry-store to export data to a CSV file. |

**Multi-device simulation:** Set `DEVICE_COUNT` to the number of simulated edge devices (default 1). Device IDs use `DEVICE_ID_PREFIX` and `DEVICE_ID_PAD` (e.g., `device_01`).

## Future Improvements & Additional Edge Services
The architecture can be extended with more specialized services:

*   **Advanced Anomaly Detection Service:** Implement more sophisticated unsupervised learning models (e.g., **Isolation Forest**, **One-Class SVM**) to detect complex, non-linear anomaly patterns that simple trends might miss.
*   **Automated Control Service:** Create a "closed-loop" system by adding a service that subscribes to alerts and automatically triggers actuators (e.g., turn on a fan, reduce machine load) in response to critical predictions.
*   **Data Summarizer Service:** Add a service that runs periodically to aggregate raw telemetry into hourly or daily summaries (avg, min, max), enabling efficient long-term analysis and reducing storage needs.
*   **Advanced AI Models:** Replace Linear Regression with an **LSTM (Long Short-Term Memory)** neural network for better handling of complex, non-linear seasonal patterns in the data.
*   **Edge-to-Cloud Integration:** Forward critical alerts to a cloud-based notification system (like AWS SNS or a Telegram Bot) for wider visibility.
