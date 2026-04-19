# Design Decisions and Tradeoffs

## 1. Decision Log Summary

This section records key architecture decisions and why they were chosen.

### D1. Use MQTT as integration backbone

Decision:

- Use broker-mediated pub/sub between analytics and UI.

Why:

- Loose coupling.
- Easy fan-out to additional consumers.
- Common industrial IoT pattern.

Tradeoff:

- Requires broker operations and topic governance.

### D2. Use synthetic data generation in edge service

Decision:

- Embed simulator in Python service.

Why:

- Enables full pipeline validation without hardware.
- Reproducible demonstrations and testing.

Tradeoff:

- Signal realism is bounded by simulation model.

### D3. Use linear regression with sliding window

Decision:

- Fit horizon-based linear model on recent 20 points with stabilization.

Why:

- Explainable and lightweight.
- Adequate for educational and trend-focused use.
- Better matches industrial need for minute-ahead awareness.

Tradeoff:

- Limited for non-linear seasonal dynamics.
- Raw linear extrapolation can still drift if process dynamics shift quickly.

### D3b. Stabilize one-minute forecast before extrapolation

Decision:

- Add outlier clipping, exponential smoothing, slope capping, and a dynamic delta guard before publishing minute-ahead predictions.

Why:

- Reduces anomaly-driven spikes in minute-ahead predictions.
- Improves operator trust in predictive status behavior.

Tradeoff:

- Stabilization introduces lag and can underreact to rapid real process changes.

### D3c. Constrain minute-ahead divergence by volatility

Decision:

- Limit forecast-to-current delta by combining minimum and maximum delta bounds with recent volatility scaling.

Why:

- Prevents implausible prediction jumps when recent data is noisy or transitioning.
- Improves trust in predictive alerts without removing horizon awareness.

Tradeoff:

- Can suppress genuine sharp transitions if they occur faster than configured bounds.

### D4. Keep prediction warmup explicit

Decision:

- Before window fills, publish Calculating... for predicted_temp.

Why:

- Honest signal that model is not ready.
- Avoids fake predictions from insufficient context.

Tradeoff:

- Consumer branches must handle non-numeric field variant.

### D5. Add trend slope classification

Decision:

- Derive trend labels from slope with deadband.

Why:

- Human-readable dashboard insight.
- Deadband reduces noisy label flipping.

Tradeoff:

- Threshold values are heuristic and may need calibration.

### D5b. Add explicit forecast horizon metadata

Decision:

- Include predicted_for and prediction_horizon_sec in telemetry.

Why:

- Makes it explicit how far into the future a value is predicted.
- Enables charting predicted points at future timestamp instead of current sample time.

Tradeoff:

- Requires consumers to interpret timestamped prediction semantics correctly.

### D6. Add runtime threshold control via dashboard

Decision:

- Slider in dashboard publishes control topic consumed by Python.

Why:

- Operator can tune sensitivity without service restart.
- Demonstrates closed-loop control capability.

Tradeoff:

- Without authn/authz, any dashboard user can alter threshold.

### D7. Keep QoS at 0 for all flows

Decision:

- Use best-effort delivery.

Why:

- Simplicity and low overhead for local demo.

Tradeoff:

- Possible message loss under stress.

### D8. Keep broker anonymous for class environment

Decision:

- allow_anonymous true in mosquitto config.

Why:

- Lower setup friction for classroom usage.

Tradeoff:

- Not suitable for production or shared networks.

### D9. Add lightweight telemetry persistence and CSV export

Decision:

- Introduce a dedicated telemetry-store service using SQLite and MQTT command/result topics for exports.

Why:

- Enables historical inspection and CSV extraction without adding heavyweight infra.
- Keeps architecture aligned with publish/subscribe boundaries already used by the stack.

Tradeoff:

- Single-file database can become a bottleneck at higher write rates.

## 2. Detailed Flow Decisions

### Telemetry fan-out in Node-RED

Decision:

- One telemetry stream split into chart, gauges, and KPI transform nodes.

Why:

- Isolates transformation responsibilities.
- Reduces coupling between widgets.

Tradeoff:

- More nodes to maintain.

### Dual operational status model

Decision:

- Show two statuses in dashboard:
  - Predicted status from alerts topic.
  - Real status computed from actual temperature versus threshold.

Why:

- Helps operators compare future risk with current condition.
- Exposes divergence between predictive warning and present-state safety.

Tradeoff:

- Two statuses can appear contradictory without operator training.

### KPI aggregation in one function node

Decision:

- Build Insights node computes and routes multiple KPI outputs including forecast validation error and horizon label.

Why:

- Centralized metric logic and shared parsing.

Tradeoff:

- Single node grows in complexity over time.

### Critical toast filter

Decision:

- Toast only for CRITICAL messages.

Why:

- Avoid alert fatigue from NORMAL messages.

Tradeoff:

- Normal transitions are less prominent.

### Storage health and export feedback in dashboard

Decision:

- Expose storage row count, last write timestamp, and export command results directly in Node-RED UI.

Why:

- Gives operators immediate feedback that persistence and export paths are functioning.

Tradeoff:

- Adds dashboard complexity and new user-facing states to maintain.

## 3. Known Gaps and Rationale

- No automated test suite:
  - Current focus is functional integration and visualization.
- No schema registry:
  - Topic contracts are documented in markdown for now.
- No role-based authorization for control/export actions:
  - Dashboard controls are still open to authenticated UI users only at platform level.

## 4. Evolution Plan

Suggested next decision path:

1. Introduce payload schema validation for publisher and consumer.
2. Add secure broker authentication and ACLs.
3. Add role-aware authorization and audit trails for control/export commands.
4. Evaluate time-series database migration path for higher throughput.
5. Upgrade prediction model with retained explainability.
6. Add CI checks for flow JSON validity and Python lint/tests.
