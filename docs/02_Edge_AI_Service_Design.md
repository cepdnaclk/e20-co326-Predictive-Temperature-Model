# Edge AI Service Design

## 1. Purpose of the Service

File: python/main.py

The Edge AI service is responsible for:

- Generating synthetic temperature telemetry.
- Estimating temperature approximately 60 seconds ahead using stabilized linear extrapolation.
- Assigning trend class from model slope.
- Publishing telemetry and status messages via MQTT.
- Accepting runtime threshold control updates from MQTT.

## 2. Core Configuration

Key constants and environment values:

- GROUP_ID: group_33
- MQTT_BROKER: from environment, default mqtt
- MQTT_PORT: 1883
- DATA_TOPIC_TEMPLATE: sensors/group_33/project33/{device_id}/data
- ALERT_TOPIC_TEMPLATE: alerts/group_33/project33/{device_id}/status
- CONTROL_TOPIC: controls/group_33/project33/threshold
- DEVICE_COUNT: configurable, default 1
- DEVICE_ID_PREFIX: configurable, default device_
- DEVICE_ID_PAD: configurable, default 2
- WINDOW_SIZE: configurable, default 20
- ALERT_THRESHOLD: from environment, default 35.0
- PREDICTION_HORIZON_SEC: configurable, default 60
- SAMPLE_INTERVAL_MIN_SEC: configurable, default 2.0
- SAMPLE_INTERVAL_MAX_SEC: configurable, default 5.0
- FORECAST_SMOOTHING_ALPHA: configurable, default 0.25
- OUTLIER_MAD_SCALE: configurable, default 3.0
- MAX_FORECAST_SLOPE_PER_STEP: configurable, default 0.12
- FORECAST_VOLATILITY_MULT: configurable, default 1.8
- FORECAST_MIN_DELTA_C: configurable, default 1.0
- FORECAST_MAX_DELTA_C: configurable, default 3.0

## 3. Synthetic Signal Model

### 3.1 Temperature generation

Function: simulate_temperature(step)

Signal composition:

- Baseline: 30.0
- Periodic component: amplitude 5.0 using sine wave
- Random noise: uniform in range [-0.5, +0.5]
- Anomaly injection: 5 percent probability adds random spike [5.0, 10.0]

This design gives:

- Trend-like movement for prediction visualization.
- Small local noise to avoid a perfect model fit.
- Rare outliers to exercise anomaly and alert behavior.

### 3.2 Rounding strategy

Generated temperature and predictions are rounded to 2 decimals for stable UI readability and payload compactness.

## 4. Prediction Pipeline

Functions: _prepare_forecast_series(history_data), predict_temperature(history_data, steps_ahead)

Algorithm:

1. If history is shorter than WINDOW_SIZE, return no prediction.
2. Build feature matrix X as integer index positions [0..n-1].
3. Build target y from recent temperature values.
4. Apply median/MAD clipping to reduce outlier impact from anomaly spikes.
5. Apply exponential smoothing to reduce short-term noise.
6. Fit scikit-learn LinearRegression on smoothed series.
7. Compute steps_ahead from horizon and average sample interval.
8. Clamp slope to max absolute slope per step to prevent aggressive extrapolation.
9. Predict at index n + steps_ahead - 1.
10. Apply dynamic delta guard relative to current smoothed level using recent volatility bounds.
11. Return forecast and capped slope coefficient.

Outputs:

- predicted_temp: estimated value at configured horizon
- trend_slope: linear slope per index step

## 5. Trend Classification Logic

Function: classify_trend(slope)

Rules:

- slope is None: warming_up (window not full)
- slope > 0.08: rising
- slope < -0.08: falling
- else: stable

Reasoning:

- Introduces deadband to avoid flickering between rising and falling due to small noise.

## 6. MQTT Lifecycle

### 6.1 Client callbacks

- on_connect:
  - Confirms connection.
  - Subscribes to control topic.

- on_disconnect:
  - Attempts reconnect.

- on_message:
  - Parses threshold control payload.
  - Updates ALERT_THRESHOLD in process memory.

### 6.2 Expected control payload

JSON object with numeric threshold field:

{
  "threshold": 31.5
}

Invalid payload handling:

- Exception is logged.
- Previous threshold remains active.

## 7. Main Runtime Loop

Pseudo-flow:

1. Generate sample.
2. Append to history.
3. Trim to window size.
4. Compute steps_ahead from configured horizon.
5. Predict horizon value and classify trend.
6. Compute rolling average.
7. Publish telemetry payload.
8. Evaluate threshold and publish NORMAL/CRITICAL status.
9. Sleep random 2-5 seconds.

Loop guardrails:

- KeyboardInterrupt exits loop.
- Unexpected exceptions are logged and retried after 5 seconds.

## 8. Telemetry Payload Construction

Fields currently published in sensors topic:

- timestamp: ISO 8601 string
- actual_temp: number
- predicted_temp: number or Calculating... while warming up
- predicted_for: ISO 8601 string for forecast target time
- prediction_horizon_sec: numeric horizon in seconds
- is_anomaly: boolean
- trend: warming_up, rising, falling, stable
- trend_slope: number or null while warming up
- window_avg: number
- threshold: active threshold

## 9. Alert Decision Logic

Rules:

- If prediction exists and predicted_temp > ALERT_THRESHOLD:
  - status CRITICAL
  - descriptive warning message indicating horizon

- Else if prediction exists:
  - status NORMAL

Status payload includes:

- timestamp
- status
- message
- predicted_val
- threshold

## 10. Design Strengths

- Small and explainable model with deterministic behavior.
- Online retraining each cycle keeps model aligned with local trend.
- Outlier clipping and smoothing improve horizon forecast stability.
- Slope capping improves industrial realism for minute-ahead extrapolation.
- Dynamic delta guard limits prediction divergence from current process behavior.
- Threshold can be changed live without restart.
- Topic-level decoupling between analytics and UI.

## 11. Known Technical Debt

- pandas is imported but not used.
- matplotlib is listed in requirements but unused.
- Refit-per-iteration is simple but not computationally optimal for larger windows.
- Forecast step conversion currently depends on a configured average interval, not adaptive measured interval.

## 12. Suggested Future Enhancements

- Move to robust regression or seasonal model for non-linear cycles.
- Add debounce/rate-limit on threshold updates.
- Add explicit QoS policy per topic.
- Add structured logger with severity and service context.
- Add graceful shutdown hook and last-will message.
- Replace fixed average sample interval with adaptive interval estimation from timestamps.
