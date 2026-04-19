# Node-RED Dashboard and Flow Logic

## 1. Purpose

File: node-red/flows.json

Node-RED provides:

- Real-time dashboard visualization.
- Transformation of telemetry for widget-compatible formats.
- Alert rendering and operator notifications.
- Runtime control input for threshold updates.
- Storage observability and operator-triggered CSV export.

## 2. Dashboard Layout

Single tab:

- Edge Forecast Console

Groups:

1. Forecast Trends
Contains primary trend chart and absolute error chart.

2. Process KPIs
Contains gauges, predicted status, real status, and KPI text fields.

3. Control Panel
Contains threshold slider and operational context text.

## 3. Input Streams

### 3.1 Telemetry input node

- Topic subscription: sensors/+/project33/data
- Datatype: parsed JSON
- Fan-out targets:
  - Format Temp Series
  - Actual Gauge Value
  - Predicted Gauge Value
  - Build Insights
  - Real Temperature Status

### 3.2 Alerts input node

- Topic subscription: alerts/+/project33/status
- Datatype: parsed JSON
- Fan-out targets:
  - Status Display
  - Critical Toast

### 3.3 Storage health input node

- Topic subscription: storage/group_33/project33/health
- Datatype: parsed JSON
- Fan-out targets:
  - Storage row count text
  - Storage last write text

### 3.4 Export result input node

- Topic subscription: storage/group_33/project33/export/result
- Datatype: parsed JSON
- Fan-out targets:
  - Export result text

## 4. Processing Nodes

### 4.1 Format Temp Series

Transforms incoming telemetry into individual chart points:

- Emits topic Actual when actual value exists using sample timestamp.
- Emits topic Predicted when predicted value is numeric using predicted_for timestamp.

Reason:

- Node-RED chart expects point-oriented messages, not mixed object arrays.

### 4.2 Actual Gauge Value

Extracts numeric actual_temp and sets msg.payload for gauge consumption.

### 4.3 Predicted Gauge Value

Extracts numeric predicted_temp and blocks non-numeric warmup values.

### 4.4 Build Insights

Computes and routes multi-output KPI stream:

1. Trend text
2. Rolling average text
3. Cumulative anomaly count
4. Absolute error text
5. Absolute error chart point
6. Active threshold text
7. Last reading timestamp text
8. Forecast validation error text
9. Prediction horizon label text

Internal state:

- Uses Node-RED function context to persist anomalyCount.
- Uses Node-RED function context to keep pending forecast points for lag validation matching.

### 4.5 Real Temperature Status

Computes operational status directly from live actual temperature:

- CRITICAL if actual_temp > threshold
- NORMAL otherwise

Output is rendered in a dedicated Operational Status (Real) widget.

### 4.6 Critical Toast

Filters alert stream:

- If status is CRITICAL, emit alert message to toast widget.
- If NORMAL, suppress toast.

### 4.7 Publish Threshold Control

Control pipeline:

1. Slider emits numeric payload.
2. Function validates and wraps payload as JSON object.
3. Function sets topic controls/group_33/project33/threshold.
4. MQTT out node publishes control command.

### 4.8 Publish Export Command

Export control pipeline:

1. Dashboard button emits payload.
2. Function builds command object with lookback_hours and optional filename.
3. Function sets topic storage/group_33/project33/export.
4. MQTT out node publishes export request to telemetry-store.

## 5. Visualization Nodes

### 5.1 Actual vs Predicted line chart

- Shows both timeseries for quick divergence detection.
- Retention configured using removeOlder fields.

### 5.2 Absolute Prediction Error bar chart

- Visualizes per-step absolute error magnitude.
- Helps operator estimate current model quality.

### 5.3 Gauges

- Actual Temp gauge
- Predicted Temp gauge

Both gauges use segmented color bands for immediate risk perception.

### 5.4 KPI text widgets

Display:

- Trend
- Window average
- Anomaly count
- Abs error
- Active threshold
- Last reading timestamp
- Forecast validation error
- Prediction horizon
- Operational Status (Predicted)
- Operational Status (Real)

### 5.5 Critical popup

Top-right toast appears for each CRITICAL status message.

### 5.6 Storage and export widgets

Display:

- Storage row count
- Storage last write timestamp
- Export result summary (status, file, rows, time)

## 6. Theme Layer

A global ui_template injects custom dashboard CSS and fonts:

- Non-default typography.
- Gradient and radial background composition.
- Card panels with custom border radius and shadows.
- Slider accent styling.
- Subtle card entry animation.
- Mobile and reduced-motion support.

## 7. Flow Safety Considerations

- Numeric checks are performed before chart and gauge emission.
- Warmup values are safely ignored by predicted gauge/chart branch.
- Context-backed anomaly count survives message-by-message processing.
- Predicted chart points are timestamped to future target time, not current sample time.

## 8. Known Constraints

- Anomaly count resets when Node-RED runtime restarts.
- UI controls are open to any dashboard user in current setup.
- Export button currently runs without role-based access control.

## 9. Extension Suggestions

- Add uptime counter and last-control-user metadata.
- Add threshold history mini-chart.
- Add separate alert acknowledgement workflow.
- Add command authentication and per-user audit trail for control/export actions.
