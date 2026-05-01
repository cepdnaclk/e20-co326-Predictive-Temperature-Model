# Deployment, Operations, and Troubleshooting

## 1. Build and Run Procedure

From project root:

1. Build and start services:

docker compose up --build

2. Access endpoints:

- Node-RED editor: http://localhost:1880
- Dashboard: http://localhost:1880/ui
- MQTT broker: localhost:1883

To run detached:

docker compose up --build -d

To stop:

docker compose down

## 2. Service Startup Expectations

Expected container order by dependencies:

1. mqtt broker starts.
2. node-red, python-edge, and telemetry-store start afterwards.

Operational note:

- Python includes reconnect behavior, so transient broker timing is tolerated.

## 3. Health Verification Checklist

### 3.1 Container level

docker compose ps

Expected:

- mqtt_broker is Up
- node_red_ui is Up and eventually healthy
- python_edge_ai is Up
- telemetry_store is Up

### 3.2 Endpoint level

- GET / on 1880 should return 200
- GET /ui should redirect or return dashboard page

### 3.3 Messaging level

Use broker-side subscription checks:

- sensors/group_33/project33/device_01/data receives periodic messages
- alerts/group_33/project33/device_01/status receives NORMAL or CRITICAL after warmup
- storage/group_33/project33/health receives row_count and last_write updates

### 3.4 Control path level

Publish control test message to controls topic and confirm threshold changes in subsequent telemetry payloads.

## 4. Operational Runbook

### 4.1 Daily startup

1. Start compose.
2. Open dashboard.
3. Confirm gauges and charts are moving.
4. Confirm both status lines are updating:
	- Operational Status (Predicted)
	- Operational Status (Real)
5. Confirm Prediction Horizon label shows expected value (for example 60 seconds ahead).

### 4.2 Runtime operation

- Use threshold slider to tune alert sensitivity.
- Observe active threshold text, dual status behavior, and forecast validation error.
- Use critical toast as immediate warning signal.
- Use export button to create CSV snapshots and verify export result text.

### 4.3 Graceful shutdown

1. docker compose down
2. Optionally persist broker volume state between sessions.

## 5. Troubleshooting Guide

### Issue: Node-RED editor not reachable

Checks:

- docker compose ps
- docker logs node_red_ui

Actions:

- Restart node-red service.
- Validate flows.json is valid JSON.

### Issue: Dashboard shows no live data

Checks:

- python_edge_ai running?
- mqtt_broker running?
- telemetry topic receiving messages?

Actions:

- Check python service logs for connection failures.
- Confirm MQTT_BROKER environment variable value.

### Issue: No CRITICAL alerts ever appear

Checks:

- Is threshold set too high?
- Is prediction available (window warmed up)?

Actions:

- Lower slider threshold.
- Wait for at least 20 data points (default window size) for warmup completion.

### Issue: Predicted status and real status disagree frequently

Checks:

- Verify Prediction Horizon value (longer horizon naturally increases divergence).
- Check forecast validation error trend.

Actions:

- Reduce horizon or tighten smoothing/slope cap settings.
- Increase WINDOW_SIZE if process dynamics are slow.

### Issue: Threshold slider changes do not affect behavior

Checks:

- Control topic publish from Node-RED working?
- Python subscribed to controls topic?

Actions:

- Inspect Node-RED function node publish payload.
- Verify Python callback logs threshold update.

### Issue: Export button shows ERROR or no output

Checks:

- telemetry_store running?
- export command topic published from Node-RED?
- storage export directory writable?

Actions:

- Check telemetry_store logs for export exceptions.
- Verify bind mount exists: ./storage/exports:/data/exports.
- Trigger manual export command on topic storage/group_33/project33/export.

### Issue: Random disconnect/reconnect behavior

Checks:

- Broker stability and host resource pressure.
- Network interruptions.

Actions:

- Review reconnect logs in python_edge_ai.
- Restart stack if broker instability persists.

## 6. Performance Notes

Current workload is light and suitable for laptop execution.

Potential hotspots if scaled:

- Refit of regression model each loop.
- Dashboard rendering if message frequency increases significantly.

Current forecast stabilization defaults in compose:

- WINDOW_SIZE=20
- PREDICTION_HORIZON_SEC=60
- SAMPLE_INTERVAL_MIN_SEC=2.5
- SAMPLE_INTERVAL_MAX_SEC=4.5
- FORECAST_SMOOTHING_ALPHA=0.25
- OUTLIER_MAD_SCALE=3.0
- MAX_FORECAST_SLOPE_PER_STEP=0.12
- FORECAST_VOLATILITY_MULT=1.8
- FORECAST_MIN_DELTA_C=1.0
- FORECAST_MAX_DELTA_C=3.0

## 7. Security Hardening Checklist (for productionization)

- Disable anonymous MQTT access.
- Enable broker username/password and ACL.
- Add TLS for MQTT transport.
- Restrict exposed ports by environment.
- Separate dashboard and broker onto controlled network.
- Add authentication for Node-RED editor access.
