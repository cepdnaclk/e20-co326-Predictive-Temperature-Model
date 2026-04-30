"""
payloads.py
-----------
Pure functions that build the JSON-serialisable dicts published to MQTT.

Keeping payload construction here means main.py stays readable, and the
schema for each message type is documented in one place.
"""

import datetime


def build_data_payload(
    *,
    device_id: str,
    timestamp: datetime.datetime,
    actual_temp: float,
    predicted_temp: float | None,
    trend: str,
    trend_slope: float | None,
    rolling_avg: float,
    is_anomaly: bool,
    alert_threshold: float,
    prediction_horizon_sec: float,
) -> dict:
    """
    Telemetry payload published to the device data topic on every reading.

    The ``predicted_for`` field is the wall-clock time that the forecast
    targets (timestamp + horizon), so Node-RED can plot both the actual
    and the prediction on the same time axis at their correct positions.
    """
    predicted_for = timestamp + datetime.timedelta(seconds=prediction_horizon_sec)

    return {
        "device_id":             device_id,
        "timestamp":              timestamp.isoformat(),
        "actual_temp":            actual_temp,
        "predicted_temp":         predicted_temp if predicted_temp is not None
                                  else "Calculating…",
        "predicted_for":          predicted_for.isoformat(),
        "prediction_horizon_sec": prediction_horizon_sec,
        "is_anomaly":             is_anomaly,
        "trend":                  trend,
        "trend_slope":            trend_slope,
        "window_avg":             rolling_avg,
        "threshold":              alert_threshold,
    }


def build_alert_payload(
    *,
    device_id: str,
    timestamp: datetime.datetime,
    predicted_temp: float,
    alert_threshold: float,
    prediction_horizon_sec: float,
) -> dict:
    """
    CRITICAL alert payload — published when the predicted temperature exceeds
    the alert threshold.
    """
    return {
        "device_id":  device_id,
        "timestamp":   timestamp.isoformat(),
        "status":      "CRITICAL",
        "message": (
            f"{device_id}: predicted temperature in {prediction_horizon_sec:.0f}s is "
            f"{predicted_temp} °C, exceeding threshold {alert_threshold} °C!"
        ),
        "predicted_val": predicted_temp,
        "threshold":     alert_threshold,
    }


def build_normal_payload(
    *,
    device_id: str,
    timestamp: datetime.datetime,
    predicted_temp: float,
    alert_threshold: float,
) -> dict:
    """
    NORMAL status payload — published when the system is within safe limits.
    """
    return {
        "device_id":    device_id,
        "timestamp":     timestamp.isoformat(),
        "status":        "NORMAL",
        "message":       f"{device_id}: system within safe range.",
        "predicted_val": predicted_temp,
        "threshold":     alert_threshold,
    }