"""
config.py
---------
Central configuration for the predictive temperature sensor pipeline.
All tuneable parameters are read from environment variables with safe defaults,
so the service can be configured via Docker / docker-compose without code changes.
"""

import os

# ── Identity ──────────────────────────────────────────────────────────────────
GROUP_ID = os.getenv("GROUP_ID", "group_33")
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", "1"))
DEVICE_ID_PREFIX = os.getenv("DEVICE_ID_PREFIX", "device_")
DEVICE_ID_PAD = int(os.getenv("DEVICE_ID_PAD", "2"))

# ── MQTT ─────────────────────────────────────────────────────────────────────
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT    = int(os.getenv("MQTT_PORT", "1883"))

# Topic templates — group ID injected at runtime
DATA_TOPIC_TEMPLATE  = f"sensors/{GROUP_ID}/project33/{{device_id}}/data"
ALERT_TOPIC_TEMPLATE = f"alerts/{GROUP_ID}/project33/{{device_id}}/status"
CONTROL_TOPIC        = f"controls/{GROUP_ID}/project33/threshold"

# ── Prediction ────────────────────────────────────────────────────────────────
WINDOW_SIZE              = int(os.getenv("WINDOW_SIZE", "30"))
ALERT_THRESHOLD          = float(os.getenv("ALERT_THRESHOLD", "35.0"))
PREDICTION_HORIZON_SEC   = float(os.getenv("PREDICTION_HORIZON_SEC", "60.0"))

# Forecast quality controls
FORECAST_SMOOTHING_ALPHA    = float(os.getenv("FORECAST_SMOOTHING_ALPHA",    "0.35"))
OUTLIER_MAD_SCALE           = float(os.getenv("OUTLIER_MAD_SCALE",           "3.0"))
MAX_FORECAST_SLOPE_PER_STEP = float(os.getenv("MAX_FORECAST_SLOPE_PER_STEP", "0.22"))
FORECAST_VOLATILITY_MULT    = float(os.getenv("FORECAST_VOLATILITY_MULT",    "1.8"))
FORECAST_MIN_DELTA_C        = float(os.getenv("FORECAST_MIN_DELTA_C",        "1.0"))
FORECAST_MAX_DELTA_C        = float(os.getenv("FORECAST_MAX_DELTA_C",        "3.0"))

# Trend classification: slope magnitude (°C/s) below which the signal is
# considered stable.  Exposed here so it can be tuned alongside the other
# forecast parameters without touching forecasting.py.
TREND_SLOPE_THRESHOLD_C_PER_SEC = float(os.getenv("TREND_SLOPE_THRESHOLD_C_PER_SEC", "0.05"))

# ── Sampling ──────────────────────────────────────────────────────────────────
SAMPLE_INTERVAL_MIN_SEC = float(os.getenv("SAMPLE_INTERVAL_MIN_SEC", "2.0"))
SAMPLE_INTERVAL_MAX_SEC = float(os.getenv("SAMPLE_INTERVAL_MAX_SEC", "5.0"))