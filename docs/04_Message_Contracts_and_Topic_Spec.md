# Message Contracts and Topic Specifications

## 1. MQTT Namespace Overview

Current topic namespace:

- Telemetry: sensors/group_33/project33/device_01/data
- Alerts: alerts/group_33/project33/device_01/status
- Controls: controls/group_33/project33/threshold
- Storage health: storage/group_33/project33/health
- Export command: storage/group_33/project33/export
- Export result: storage/group_33/project33/export/result

Wildcard subscriptions used by Node-RED:

- sensors/+/project33/+/data
- alerts/+/project33/+/status
- storage/group_33/project33/health
- storage/group_33/project33/export/result

## 2. Telemetry Contract

Topic:

- sensors/group_33/project33/device_01/data

Producer:

- Python Edge AI service

Consumers:

- Node-RED telemetry flow
- Any future analytics/storage subscriber

Payload schema:

- device_id: string
- timestamp: string, ISO 8601
- actual_temp: number
- predicted_temp: number or string Calculating...
- predicted_for: string, ISO 8601 target time of the forecast
- prediction_horizon_sec: number, forecast horizon in seconds
- is_anomaly: boolean
- trend: string in warming_up, rising, falling, stable
- trend_slope: number or null
- window_avg: number
- forecast_error: number or null (absolute error when a forecast target is reached)
- forecast_mae: number or null (rolling mean absolute error)
- threshold: number

Example:

{
  "device_id": "device_01",
  "timestamp": "2026-04-19T05:09:44.608310",
  "actual_temp": 34.58,
  "predicted_temp": 35.62,
  "predicted_for": "2026-04-19T05:10:44.608310",
  "prediction_horizon_sec": 60.0,
  "is_anomaly": false,
  "trend": "rising",
  "trend_slope": 0.4104,
  "window_avg": 33.36,
  "threshold": 31.5
}

## 3. Status Alert Contract

Topic:

- alerts/group_33/project33/device_01/status

Producer:

- Python Edge AI service

Consumer:

- Node-RED alert flow

Payload schema:

- device_id: string
- timestamp: string, ISO 8601
- status: string, NORMAL or CRITICAL
- message: string
- predicted_val: number
- threshold: number

CRITICAL example:

{
  "device_id": "device_01",
  "timestamp": "2026-04-19T04:57:23.925533",
  "status": "CRITICAL",
  "message": "device_01: predicted temperature in 60s is 35.61C, exceeding threshold 35.0C!",
  "predicted_val": 35.61,
  "threshold": 35.0
}

NORMAL example:

{
  "device_id": "device_01",
  "timestamp": "2026-04-19T04:57:29.781991",
  "status": "NORMAL",
  "message": "device_01: system within safe range.",
  "predicted_val": 34.82,
  "threshold": 35.0
}

## 4. Threshold Control Contract

Topic:

- controls/group_33/project33/threshold

Producer:

- Node-RED control slider pipeline

Consumer:

- Python Edge AI subscribed callback

Payload schema:

- threshold: number

Example:

{
  "threshold": 31.5
}

Expected behavior:

- Python updates in-memory ALERT_THRESHOLD immediately.
- New threshold appears in next telemetry payload.
- Next alert status evaluation uses updated threshold.

## 5. Storage Health Contract

Topic:

- storage/group_33/project33/health

Producer:

- telemetry-store service

Consumer:

- Node-RED storage health panel

Payload schema:

- device_id: string
- timestamp: string, ISO 8601
- row_count: integer
- last_write: string, ISO 8601 or null

Example:

{
  "timestamp": "2026-04-19T07:51:16.152694",
  "row_count": 161,
  "last_write": "2026-04-19T07:51:15.900107"
}

## 6. Export Command and Result Contracts

### 6.1 Export command

Topic:

- storage/group_33/project33/export

Producer:

- Node-RED export button flow

Consumer:

- telemetry-store command handler

Payload schema:

- lookback_hours: number (optional, default 1)
- filename: string (optional)

Example:

{
  "lookback_hours": 1
}

### 6.2 Export result

Topic:

- storage/group_33/project33/export/result

Producer:

- telemetry-store after export attempt

Consumer:

- Node-RED export result text widget

Payload schema:

- timestamp: string, ISO 8601
- status: string, OK or ERROR
- file: string when status is OK
- rows: integer when status is OK
- error: string when status is ERROR

OK example:

{
  "timestamp": "2026-04-19T07:52:11.473120",
  "status": "OK",
  "file": "/data/exports/telemetry_20260419_075211.csv",
  "rows": 118
}

ERROR example:

{
  "timestamp": "2026-04-19T07:52:11.473120",
  "status": "ERROR",
  "error": "database is locked"
}

## 7. Contract Compatibility Rules

To preserve compatibility:

1. Do not remove existing required keys.
2. Additive changes should be optional for consumers.
3. Keep numeric fields numeric where dashboard expects numbers.
4. Keep predicted_temp warmup behavior documented if using non-numeric placeholder.
5. Keep predicted_for and prediction_horizon_sec aligned with the same forecast target.

## 8. QoS and Retention

Current settings:

- QoS: 0 for publish and subscriptions.
- Retain: false on control publish.

Implications:

- Best-effort delivery is acceptable for demonstration.
- Last control command is not retained for late-joining consumers.

## 9. Validation Checklist for Integrators

Before integrating a new consumer or producer:

- Confirm topic exactness.
- Confirm JSON parseability.
- Confirm predicted_temp can be non-numeric during warmup.
- Confirm status enum handling for NORMAL and CRITICAL.
- Confirm threshold updates can occur at runtime.
- Confirm storage health payload parses row_count and last_write.
- Confirm export result handler covers both OK and ERROR states.
