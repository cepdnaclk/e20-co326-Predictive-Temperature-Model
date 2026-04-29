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
from simulation import simulate_temperature


def main() -> None:
    # ── Shared mutable state ──────────────────────────────────────────────────
    # The MQTT on_message callback updates alert_threshold whenever a control
    # message arrives, so we pass a dict rather than a bare float.
    state: dict = {"alert_threshold": config.ALERT_THRESHOLD}

    # ── MQTT setup ────────────────────────────────────────────────────────────
    client = mqtt_client.build_client(state)

    # ── History buffer: list of (unix_timestamp_float, temperature_float) ─────
    # Storing real timestamps (not indices) lets the forecaster regress over
    # actual elapsed seconds, making "60 s ahead" genuinely mean 60 seconds.
    history: list[tuple[float, float]] = []

    step = 0

    print("[MAIN] Sensor loop started.")

    while True:
        try:
            now          = datetime.datetime.now()
            current_temp, was_anomaly = simulate_temperature(step)

            # Append (unix_ts, temp) and cap the buffer at WINDOW_SIZE
            history.append((time.time(), current_temp))
            if len(history) > config.WINDOW_SIZE:
                history.pop(0)

            # ── Forecast ──────────────────────────────────────────────────────
            predicted_temp, trend_slope = predict_temperature(
                history, config.PREDICTION_HORIZON_SEC
            )
            trend       = classify_trend(trend_slope)
            rolling_avg = round(float(np.mean([h[1] for h in history])), 2)
            threshold   = state["alert_threshold"]

            # ── Build & publish telemetry ─────────────────────────────────────
            data_payload = payloads.build_data_payload(
                timestamp              = now,
                actual_temp            = current_temp,
                predicted_temp         = predicted_temp,
                trend                  = trend,
                trend_slope            = trend_slope,
                rolling_avg            = rolling_avg,
                is_anomaly             = was_anomaly,
                alert_threshold        = threshold,
                prediction_horizon_sec = config.PREDICTION_HORIZON_SEC,
            )
            mqtt_client.publish_data(client, data_payload)
            print(f"[MAIN] Published: {data_payload}")

            # ── Alert check (predicted value vs threshold) ────────────────────
            if predicted_temp is not None:
                if predicted_temp > threshold:
                    alert = payloads.build_alert_payload(
                        timestamp              = now,
                        predicted_temp         = predicted_temp,
                        alert_threshold        = threshold,
                        prediction_horizon_sec = config.PREDICTION_HORIZON_SEC,
                    )
                    mqtt_client.publish_alert(client, alert)
                    print(f"[MAIN] ALERT published: {alert}")
                else:
                    normal = payloads.build_normal_payload(
                        timestamp       = now,
                        predicted_temp  = predicted_temp,
                        alert_threshold = threshold,
                    )
                    mqtt_client.publish_alert(client, normal)

            step += 1

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