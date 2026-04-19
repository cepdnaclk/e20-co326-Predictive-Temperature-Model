# Predictive Temperature System - Technical Documentation Index

This documentation set explains the system end-to-end, including architecture, runtime flow, design decisions, and operational behavior.

## Document Map

1. [01_System_Architecture_and_Dataflow.md](01_System_Architecture_and_Dataflow.md)
Purpose: End-to-end architecture, container topology, and runtime data path.

2. [02_Edge_AI_Service_Design.md](02_Edge_AI_Service_Design.md)
Purpose: Deep technical explanation of the Python simulation and prediction service.

3. [03_Node_RED_Dashboard_and_Flow_Logic.md](03_Node_RED_Dashboard_and_Flow_Logic.md)
Purpose: Full Node-RED flow decomposition, node responsibilities, and UI behavior.

4. [04_Message_Contracts_and_Topic_Spec.md](04_Message_Contracts_and_Topic_Spec.md)
Purpose: MQTT topics, payload schemas, examples, and compatibility notes.

5. [05_Deployment_Operations_and_Troubleshooting.md](05_Deployment_Operations_and_Troubleshooting.md)
Purpose: Build/run lifecycle, operational checks, and incident handling.

6. [06_Design_Decisions_and_Tradeoffs.md](06_Design_Decisions_and_Tradeoffs.md)
Purpose: Decision rationale, tradeoffs, known limitations, and future path.

## Reading Order

Recommended order for a new engineer:

1. System architecture and dataflow
2. Message contracts and topic specifications
3. Edge AI service design
4. Node-RED flow logic
5. Deployment and operations
6. Design decisions and tradeoffs

## Scope Covered

This set covers:

- Why the system was designed this way.
- How every major runtime step executes.
- How data transforms across services.
- How control messages alter behavior at runtime.
- How to operate, debug, and extend the platform safely.

## Source of Truth

All documents are based on current implementation in:

- docker-compose.yml
- mosquitto/mosquitto.conf
- python/edge_ai.py
- node-red/flows.json
- storage/telemetry_logger.py
- storage/query_recent.py
- storage/export_csv.py
