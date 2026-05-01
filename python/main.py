"""
main.py
-------
Entry point for the predictive temperature sensor pipeline.

Responsibilities
----------------
* Initialise shared state and the MQTT client.
* Run the main sensing loop: simulate → forecast → publish → sleep.
* Delegate all domain logic to the purpose-built modules:
    config       – environment-driven constants
    simulation   – temperature generation
    forecasting  – polynomial regression forecast & trend classification
    mqtt_client  – broker connection and message I/O
    payloads     – JSON payload construction

Drop-in replacement
-------------------
This file (together with the sibling modules in the same directory) is a
complete, self-contained replacement for the original single-file script.
No external modifications (broker config, topics, Docker env vars) are needed.
"""

import datetime
import random
import time

import numpy as np

import config
import mqtt_client
import payloads
from forecasting import classify_trend, predict_temperature
from simulation import TemperatureSimulator


def main() -> None:
    # ── Shared mutable state ──────────────────────────────────────────────────
    # The MQTT on_message callback updates alert_threshold whenever a control
    # message arrives, so we pass a dict rather than a bare float.
    state: dict = {"alert_threshold": config.ALERT_THRESHOLD}

    # ── MQTT setup ────────────────────────────────────────────────────────────
    client = mqtt_client.build_client(state)

    # ── Per-device state ─────────────────────────────────────────────────────
    # Each device gets its own simulator, history buffer, and step counter.
    devices = []
    for idx in range(1, config.DEVICE_COUNT + 1):
        device_id = f"{config.DEVICE_ID_PREFIX}{idx:0{config.DEVICE_ID_PAD}d}"
        devices.append(
            {
                "device_id": device_id,
                "simulator": TemperatureSimulator(),
                "history": [],
                "step": 0,
                "pending_predictions": [],
                "error_history": [],
                "start_ts": time.time(),
                "last_publish_ts": None,
            }
        )

    print("[MAIN] Sensor loop started.")

    while True:
        try:
            for device in devices:
                now = datetime.datetime.now()
                now_ts = time.time()
                device_id = device["device_id"]
                current_temp, was_anomaly = device["simulator"].simulate(device["step"])

                history = device["history"]

                # Append (unix_ts, temp) and cap the buffer at WINDOW_SIZE
                history.append((time.time(), current_temp))
                if len(history) > config.WINDOW_SIZE:
                    history.pop(0)

                # ── Forecast ──────────────────────────────────────────────────
                predicted_temp, trend_slope = predict_temperature(
                    history, config.PREDICTION_HORIZON_SEC, device_id
                )
                trend = classify_trend(trend_slope)
                rolling_avg = round(float(np.mean([h[1] for h in history])), 2)
                threshold = state["alert_threshold"]

                # ── Forecast accuracy (match due predictions) ──────────────
                forecast_error = None
                pending = device["pending_predictions"]
                error_history = device["error_history"]

                if pending and pending[0]["target_ts"] <= now_ts:
                    matched = pending.pop(0)
                    forecast_error = round(
                        abs(current_temp - matched["predicted_temp"]), 3
                    )
                    error_history.append(forecast_error)
                    if len(error_history) > config.FORECAST_ERROR_WINDOW:
                        error_history.pop(0)

                forecast_mae = None
                if error_history:
                    forecast_mae = round(sum(error_history) / len(error_history), 3)

                # ── Build & publish telemetry ─────────────────────────────────
                data_payload = payloads.build_data_payload(
                    device_id              = device_id,
                    timestamp              = now,
                    actual_temp            = current_temp,
                    predicted_temp         = predicted_temp,
                    trend                  = trend,
                    trend_slope            = trend_slope,
                    rolling_avg            = rolling_avg,
                    is_anomaly             = was_anomaly,
                    alert_threshold        = threshold,
                    prediction_horizon_sec = config.PREDICTION_HORIZON_SEC,
                    forecast_error          = forecast_error,
                    forecast_mae            = forecast_mae,
                )
                mqtt_client.publish_data(client, data_payload, device_id)
                print(f"[MAIN] Published {device_id}: {data_payload}")

                if predicted_temp is not None:
                    pending.append(
                        {
                            "target_ts": now_ts + config.PREDICTION_HORIZON_SEC,
                            "predicted_temp": predicted_temp,
                        }
                    )

                # ── Device health ─────────────────────────────────────────
                last_publish_ts = device["last_publish_ts"]
                if last_publish_ts is None:
                    health_status = "STARTING"
                    last_gap_sec = None
                    last_seen_dt = now
                else:
                    last_gap_sec = round(now_ts - last_publish_ts, 3)
                    health_status = (
                        "OK"
                        if last_gap_sec <= config.HEALTH_STALE_THRESHOLD_SEC
                        else "STALE"
                    )
                    last_seen_dt = datetime.datetime.fromtimestamp(last_publish_ts)

                health_payload = payloads.build_health_payload(
                    device_id=device_id,
                    timestamp=now,
                    status=health_status,
                    last_seen=last_seen_dt,
                    uptime_sec=round(now_ts - device["start_ts"], 1),
                    last_gap_sec=last_gap_sec,
                )
                mqtt_client.publish_health(client, health_payload, device_id)

                # ── Alert check (predicted value vs threshold) ────────────────
                if predicted_temp is not None:
                    if predicted_temp > threshold:
                        alert = payloads.build_alert_payload(
                            device_id              = device_id,
                            timestamp              = now,
                            predicted_temp         = predicted_temp,
                            alert_threshold        = threshold,
                            prediction_horizon_sec = config.PREDICTION_HORIZON_SEC,
                        )
                        mqtt_client.publish_alert(client, alert, device_id)
                        print(f"[MAIN] ALERT published {device_id}: {alert}")
                    else:
                        normal = payloads.build_normal_payload(
                            device_id        = device_id,
                            timestamp        = now,
                            predicted_temp   = predicted_temp,
                            alert_threshold  = threshold,
                        )
                        mqtt_client.publish_alert(client, normal, device_id)

                    device["last_publish_ts"] = now_ts

                device["step"] += 1

            # Random sample interval: jitter prevents aliasing with the
            # sinusoidal signal and exercises the time-aware forecaster.
            time.sleep(
                random.uniform(
                    config.SAMPLE_INTERVAL_MIN_SEC,
                    config.SAMPLE_INTERVAL_MAX_SEC,
                )
            )

        except KeyboardInterrupt:
            print("\n[MAIN] Interrupted by user. Shutting down…")
            break
        except Exception as exc:
            print(f"[MAIN] Loop error: {exc}")
            time.sleep(5)

    client.loop_stop()
    client.disconnect()
    print("[MAIN] MQTT client disconnected. Bye.")


if __name__ == "__main__":
    main()