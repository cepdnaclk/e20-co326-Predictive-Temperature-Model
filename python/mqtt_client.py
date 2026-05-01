"""
mqtt_client.py
--------------
Thin wrapper around paho-mqtt 2.x that handles broker connection, automatic
reconnection, and inbound threshold-control messages.

The module exposes a single `build_client()` factory so that main.py stays
free of MQTT boilerplate.  The active alert threshold is kept in a mutable
dict (`state`) so callbacks can update it without using a global variable.
"""

import json
import paho.mqtt.client as mqtt

import config


def build_client(state: dict) -> mqtt.Client:
    """
    Create, configure, and connect an MQTT client.

    Args:
        state: Shared mutable dict.  The key ``"alert_threshold"`` is updated
               whenever a new threshold arrives on the control topic.
               Initialise it before calling this function, e.g.:
                   state = {"alert_threshold": config.ALERT_THRESHOLD}

    Returns:
        A connected, loop-started mqtt.Client instance.

    Raises:
        SystemExit: If the initial broker connection fails.
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect    = _make_on_connect(state)
    client.on_disconnect = _on_disconnect
    client.on_message    = _make_on_message(state)

    try:
        print(f"[MQTT] Connecting to {config.MQTT_BROKER}:{config.MQTT_PORT}")
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
    except Exception as exc:
        print(f"[MQTT] Connection failed: {exc}")
        raise SystemExit(1) from exc

    client.loop_start()
    return client


# ── Callback factories ────────────────────────────────────────────────────────

def _make_on_connect(state: dict):
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("[MQTT] Connected to broker.")
            client.subscribe(config.CONTROL_TOPIC)
            print(f"[MQTT] Subscribed to control topic: {config.CONTROL_TOPIC}")
        else:
            print(f"[MQTT] Connection refused, rc={rc}")
    return on_connect


def _on_disconnect(client, userdata, disconnect_flags, rc, properties):
    print("[MQTT] Disconnected. Attempting reconnect…")
    try:
        client.reconnect()
    except Exception as exc:
        print(f"[MQTT] Reconnect failed: {exc}")


def _make_on_message(state: dict):
    def on_message(client, userdata, msg):
        if msg.topic != config.CONTROL_TOPIC:
            return
        try:
            payload       = json.loads(msg.payload.decode("utf-8"))
            new_threshold = float(payload["threshold"])
            state["alert_threshold"] = round(new_threshold, 2)
            print(f"[MQTT] Alert threshold updated → {state['alert_threshold']} °C")
        except Exception as exc:
            print(f"[MQTT] Invalid threshold payload on {config.CONTROL_TOPIC}: {exc}")
    return on_message


# ── Publishing helpers ────────────────────────────────────────────────────────

def _format_topic(template: str, device_id: str) -> str:
    return template.format(device_id=device_id)


def publish_data(client: mqtt.Client, payload: dict, device_id: str) -> None:
    """Publish a telemetry payload to the device data topic."""
    topic = _format_topic(config.DATA_TOPIC_TEMPLATE, device_id)
    client.publish(topic, json.dumps(payload))


def publish_alert(client: mqtt.Client, payload: dict, device_id: str) -> None:
    """Publish an alert / status payload to the device alert topic."""
    topic = _format_topic(config.ALERT_TOPIC_TEMPLATE, device_id)
    client.publish(topic, json.dumps(payload))


def publish_health(client: mqtt.Client, payload: dict, device_id: str) -> None:
    """Publish a device health payload."""
    topic = _format_topic(config.HEALTH_TOPIC_TEMPLATE, device_id)
    client.publish(topic, json.dumps(payload))