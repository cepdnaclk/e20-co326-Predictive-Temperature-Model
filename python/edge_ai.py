import paho.mqtt.client as mqtt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import json
import time
import random
import datetime
import os

# Configuration
GROUP_ID = "group_33"  # Replace with your actual group ID if needed
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT = 1883
DATA_TOPIC = f"sensors/{GROUP_ID}/project33/data"
ALERT_TOPIC = f"alerts/{GROUP_ID}/project33/status"
CONTROL_TOPIC = f"controls/{GROUP_ID}/project33/threshold"

# Simulation Parameters
BASE_TEMP = 30.0
AMPLITUDE = 5.0  # Daily variation amplitude
NOISE_LEVEL = 0.5
ANOMALY_PROB = 0.05  # 5% chance of an anomaly spike
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "20"))
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "35.0"))
PREDICTION_HORIZON_SEC = float(os.getenv("PREDICTION_HORIZON_SEC", "60.0"))
AVG_SAMPLE_INTERVAL_SEC = float(os.getenv("AVG_SAMPLE_INTERVAL_SEC", "3.5"))
FORECAST_SMOOTHING_ALPHA = float(os.getenv("FORECAST_SMOOTHING_ALPHA", "0.35"))
OUTLIER_MAD_SCALE = float(os.getenv("OUTLIER_MAD_SCALE", "3.0"))
MAX_FORECAST_SLOPE_PER_STEP = float(os.getenv("MAX_FORECAST_SLOPE_PER_STEP", "0.22"))
FORECAST_VOLATILITY_MULT = float(os.getenv("FORECAST_VOLATILITY_MULT", "1.8"))
FORECAST_MIN_DELTA_C = float(os.getenv("FORECAST_MIN_DELTA_C", "1.0"))
FORECAST_MAX_DELTA_C = float(os.getenv("FORECAST_MAX_DELTA_C", "3.0"))

# Initialize data storage
history = []

def simulate_temperature(step):
    """Simulates realistic temperature with daily cycles, noise, and anomalies."""
    # Sinusoidal wave to simulate daily variation (assuming 24 steps = 1 day)
    # Using a high frequency here for visual effect in the dashboard
    sine_val = AMPLITUDE * np.sin(2 * np.pi * step / 50)
    temp = BASE_TEMP + sine_val
    
    # Add random noise
    temp += random.uniform(-NOISE_LEVEL, NOISE_LEVEL)
    
    # Inject anomaly
    is_anomaly = False
    if random.random() < ANOMALY_PROB:
        temp += random.uniform(5.0, 10.0)
        is_anomaly = True
        
    return round(temp, 2), is_anomaly

def _prepare_forecast_series(history_data):
    """Returns an outlier-robust and smoothed series for stable forecasting."""
    y_raw = np.array(history_data, dtype=float)

    median = float(np.median(y_raw))
    mad = float(np.median(np.abs(y_raw - median)))

    if mad > 1e-9:
        lower = median - OUTLIER_MAD_SCALE * mad
        upper = median + OUTLIER_MAD_SCALE * mad
        y_clipped = np.clip(y_raw, lower, upper)
    else:
        y_clipped = y_raw

    alpha = min(max(FORECAST_SMOOTHING_ALPHA, 0.05), 0.95)
    y_smooth = np.copy(y_clipped)
    for i in range(1, len(y_smooth)):
        y_smooth[i] = alpha * y_clipped[i] + (1.0 - alpha) * y_smooth[i - 1]

    return y_smooth


def predict_temperature(history_data, steps_ahead):
    """Uses linear regression to predict a future value and trend slope."""
    if len(history_data) < WINDOW_SIZE:
        return None, None
    
    # Prepare data for regression (X: indices/timestamps, y: temperatures)
    X = np.array(range(len(history_data))).reshape(-1, 1)
    y = _prepare_forecast_series(history_data)
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict N steps ahead. One-step ahead is index len(history_data).
    next_step_index = len(history_data) + steps_ahead - 1
    raw_slope = float(model.coef_[0])
    slope = max(-MAX_FORECAST_SLOPE_PER_STEP, min(MAX_FORECAST_SLOPE_PER_STEP, raw_slope))

    intercept = float(model.intercept_)
    prediction = intercept + slope * next_step_index

    # Constrain long-horizon forecast to plausible movement from current level.
    # This prevents large divergence when extrapolating minute-ahead on noisy data.
    current_level = float(y[-1])
    recent_std = float(np.std(y[-min(len(y), 8):]))
    dynamic_delta = FORECAST_VOLATILITY_MULT * recent_std
    delta_limit = min(FORECAST_MAX_DELTA_C, max(FORECAST_MIN_DELTA_C, dynamic_delta))
    prediction = max(current_level - delta_limit, min(current_level + delta_limit, prediction))

    return round(prediction, 2), round(slope, 4)


def classify_trend(slope):
    """Maps slope into readable trend labels for dashboard insights."""
    if slope is None:
        return "warming_up"
    if slope > 0.08:
        return "rising"
    if slope < -0.08:
        return "falling"
    return "stable"

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(CONTROL_TOPIC)
        print(f"Subscribed to control topic: {CONTROL_TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, disconnect_flags, rc, properties):
    print("Disconnected from MQTT Broker. Attempting to reconnect...")
    try:
        client.reconnect()
    except Exception as e:
        print(f"Reconnection failed: {e}")


def on_message(client, userdata, msg):
    global ALERT_THRESHOLD
    if msg.topic != CONTROL_TOPIC:
        return

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        new_threshold = float(payload.get("threshold"))
        ALERT_THRESHOLD = round(new_threshold, 2)
        print(f"Updated alert threshold to {ALERT_THRESHOLD}°C")
    except Exception as e:
        print(f"Invalid threshold payload on {CONTROL_TOPIC}: {e}")

# Main Logic
# Updated for paho-mqtt 2.0 compatibility
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

try:
    print(f"Connecting to broker: {MQTT_BROKER}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

client.loop_start()

step = 0
while True:
    try:
        current_temp, was_anomaly = simulate_temperature(step)
        history.append(current_temp)
        
        # Keep window size fixed
        if len(history) > WINDOW_SIZE:
            history.pop(0)

        steps_ahead = max(1, int(round(PREDICTION_HORIZON_SEC / AVG_SAMPLE_INTERVAL_SEC)))
            
        predicted_temp, trend_slope = predict_temperature(history, steps_ahead)
        trend = classify_trend(trend_slope)
        now = datetime.datetime.now()
        timestamp = now.isoformat()
        predicted_for = (now + datetime.timedelta(seconds=PREDICTION_HORIZON_SEC)).isoformat()
        rolling_avg = round(float(np.mean(history)), 2)
        
        # Prepare Data Payload
        payload = {
            "timestamp": timestamp,
            "actual_temp": current_temp,
            "predicted_temp": predicted_temp if predicted_temp is not None else "Calculating...",
            "predicted_for": predicted_for,
            "prediction_horizon_sec": PREDICTION_HORIZON_SEC,
            "is_anomaly": was_anomaly,
            "trend": trend,
            "trend_slope": trend_slope,
            "window_avg": rolling_avg,
            "threshold": ALERT_THRESHOLD
        }
        
        # Publish Data
        client.publish(DATA_TOPIC, json.dumps(payload))
        print(f"Published: {payload}")
        
        # Threshold Alert Check
        if predicted_temp and predicted_temp > ALERT_THRESHOLD:
            alert_payload = {
                "timestamp": timestamp,
                "status": "CRITICAL",
                "message": f"Predicted temperature in {PREDICTION_HORIZON_SEC:.0f}s is {predicted_temp}°C, exceeding threshold {ALERT_THRESHOLD}°C!",
                "predicted_val": predicted_temp,
                "threshold": ALERT_THRESHOLD
            }
            client.publish(ALERT_TOPIC, json.dumps(alert_payload))
            print(f"ALERT PUBLISHED: {alert_payload}")
        elif predicted_temp:
            status_payload = {
                "timestamp": timestamp,
                "status": "NORMAL",
                "message": "System within safe range.",
                "predicted_val": predicted_temp,
                "threshold": ALERT_THRESHOLD
            }
            client.publish(ALERT_TOPIC, json.dumps(status_payload))

        step += 1
        # Random sleep between 2 and 5 seconds as requested
        time.sleep(random.uniform(2.0, 5.0))
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error in loop: {e}")
        time.sleep(5)

client.loop_stop()
client.disconnect()
