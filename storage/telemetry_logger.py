import datetime
import csv
import json
import os
import sqlite3
import time

import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "sensors/+/project33/+/data")
DB_PATH = os.getenv("DB_PATH", "/data/telemetry.db")
HEALTH_TOPIC = os.getenv("HEALTH_TOPIC", "storage/group_33/project33/health")
EXPORT_CMD_TOPIC = os.getenv("EXPORT_CMD_TOPIC", "storage/group_33/project33/export")
EXPORT_RESULT_TOPIC = os.getenv(
    "EXPORT_RESULT_TOPIC", "storage/group_33/project33/export/result"
)


def to_float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ensure_db_schema(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            source_timestamp TEXT,
            actual_temp REAL,
            predicted_temp REAL,
            predicted_for TEXT,
            prediction_horizon_sec REAL,
            threshold REAL,
            trend TEXT,
            trend_slope REAL,
            is_anomaly INTEGER,
            window_avg REAL,
            forecast_error REAL,
            forecast_mae REAL,
            raw_payload TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )
        """
    )
    _ensure_column(conn, "telemetry", "forecast_error", "REAL")
    _ensure_column(conn, "telemetry", "forecast_mae", "REAL")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_source_ts ON telemetry(source_timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_ingested_at ON telemetry(ingested_at)"
    )
    conn.commit()


def _ensure_column(conn, table, column, col_type):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    conn.commit()


def insert_telemetry(conn, topic, payload_obj):
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """
        INSERT INTO telemetry (
            topic,
            source_timestamp,
            actual_temp,
            predicted_temp,
            predicted_for,
            prediction_horizon_sec,
            threshold,
            trend,
            trend_slope,
            is_anomaly,
            window_avg,
            forecast_error,
            forecast_mae,
            raw_payload,
            ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic,
            payload_obj.get("timestamp"),
            to_float_or_none(payload_obj.get("actual_temp")),
            to_float_or_none(payload_obj.get("predicted_temp")),
            payload_obj.get("predicted_for"),
            to_float_or_none(payload_obj.get("prediction_horizon_sec")),
            to_float_or_none(payload_obj.get("threshold")),
            payload_obj.get("trend"),
            to_float_or_none(payload_obj.get("trend_slope")),
            1 if bool(payload_obj.get("is_anomaly")) else 0,
            to_float_or_none(payload_obj.get("window_avg")),
            to_float_or_none(payload_obj.get("forecast_error")),
            to_float_or_none(payload_obj.get("forecast_mae")),
            json.dumps(payload_obj),
            now_iso,
        ),
    )
    conn.commit()


def publish_storage_health(client, conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(ingested_at) FROM telemetry")
    row_count, last_write = cur.fetchone()

    payload = {
        "row_count": int(row_count or 0),
        "last_write": last_write,
        "db_path": DB_PATH,
        "status": "OK",
    }
    client.publish(HEALTH_TOPIC, json.dumps(payload))


def export_recent_csv(conn, minutes, export_dir="/data/exports"):
    os.makedirs(export_dir, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(export_dir, f"telemetry_{ts}.csv")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_timestamp, actual_temp, predicted_temp, predicted_for,
               prediction_horizon_sec, threshold, trend, trend_slope,
             is_anomaly, window_avg, forecast_error, forecast_mae, ingested_at
        FROM telemetry
        WHERE ingested_at >= datetime('now', ?)
        ORDER BY id ASC
        """,
        (f"-{minutes} minutes",),
    )
    rows = cur.fetchall()

    headers = [
        "source_timestamp",
        "actual_temp",
        "predicted_temp",
        "predicted_for",
        "prediction_horizon_sec",
        "threshold",
        "trend",
        "trend_slope",
        "is_anomaly",
        "window_avg",
        "forecast_error",
        "forecast_mae",
        "ingested_at",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return out_path, len(rows)


def publish_export_result(client, status, minutes, csv_path=None, row_count=0, error=None):
    payload = {
        "status": status,
        "minutes": minutes,
        "csv_path": csv_path,
        "row_count": row_count,
        "error": error,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    client.publish(EXPORT_RESULT_TOPIC, json.dumps(payload))


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(TELEMETRY_TOPIC)
        client.subscribe(EXPORT_CMD_TOPIC)
        print(f"Subscribed to topic: {TELEMETRY_TOPIC}")
        print(f"Subscribed to topic: {EXPORT_CMD_TOPIC}")
        try:
            publish_storage_health(client, userdata["conn"])
        except Exception as exc:
            print(f"Failed to publish initial health: {exc}")
    else:
        print(f"Failed to connect. rc={rc}")


def on_disconnect(client, userdata, disconnect_flags, rc, properties):
    print("Disconnected from broker. Retrying...")
    try:
        client.reconnect()
    except Exception as exc:
        print(f"Reconnect attempt failed: {exc}")


def on_message(client, userdata, msg):
    conn = userdata["conn"]
    try:
        payload_obj = json.loads(msg.payload.decode("utf-8"))
    except Exception as exc:
        print(f"Failed to parse payload on {msg.topic}: {exc}")
        return

    if msg.topic == EXPORT_CMD_TOPIC:
        try:
            minutes = int(payload_obj.get("minutes", 60))
            minutes = max(1, min(minutes, 1440))
            csv_path, row_count = export_recent_csv(conn, minutes)
            publish_export_result(
                client,
                status="OK",
                minutes=minutes,
                csv_path=csv_path,
                row_count=row_count,
            )
            print(f"Exported CSV rows={row_count} path={csv_path}")
        except Exception as exc:
            publish_export_result(
                client,
                status="ERROR",
                minutes=payload_obj.get("minutes", 60),
                error=str(exc),
            )
            print(f"Failed to export CSV: {exc}")
        return

    if msg.topic != TELEMETRY_TOPIC and "+" in TELEMETRY_TOPIC:
        # Wildcard subscriptions arrive as concrete topics.
        pass

    try:
        insert_telemetry(conn, msg.topic, payload_obj)
        publish_storage_health(client, conn)
        print(
            f"Stored row topic={msg.topic} actual={payload_obj.get('actual_temp')} predicted={payload_obj.get('predicted_temp')}"
        )
    except Exception as exc:
        print(f"Failed to store message on {msg.topic}: {exc}")


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    ensure_db_schema(conn)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={"conn": conn})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    while True:
        try:
            print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except Exception as exc:
            print(f"Initial connect failed: {exc}. Retrying in 5s")
            time.sleep(5)

    client.loop_start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        conn.close()


if __name__ == "__main__":
    main()
