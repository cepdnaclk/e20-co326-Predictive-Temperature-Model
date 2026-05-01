---
layout: home
permalink: index.html

# Please update this with your repository name and title
repository-name: e20-co326-Predictive-Temperature-Model
title: Predictive Temperature Model
---
[comment]: # "This is the standard layout for the project, but you can clean this and use your own template"

# Predictive Temperature Model

## Team
- Group 33
- (Add member names and emails)

## Overview
This project implements an Edge AI predictive temperature monitoring system for industrial IoT. It simulates temperature telemetry, forecasts near-future temperatures, and raises alerts before an overheating event happens. The system is fully containerized and communicates over MQTT.

## System Architecture
- MQTT broker (Mosquitto) for message transport
- Node-RED for dashboard and flow orchestration
- Python edge service for simulation, preprocessing, and forecasting
- Telemetry store for persisting data and CSV export

## Data Flow
Python (Sim + AI) -> MQTT Broker -> Node-RED -> Dashboard UI
Python (Sim + AI) -> MQTT Broker -> Telemetry Store -> SQLite/CSV

## MQTT Topics
- sensors/group_33/project33/device_01/data
- alerts/group_33/project33/device_01/status
- controls/group_33/project33/threshold
- storage/group_33/project33/export
- storage/group_33/project33/export/result

## Multi-device Simulation
Set `DEVICE_COUNT` to the number of simulated edge devices (default 1). Device IDs use `DEVICE_ID_PREFIX` and `DEVICE_ID_PAD` (e.g., `device_01`).

## Links
- [Project Repository](https://github.com/cepdnaclk/{{ page.repository-name }}){:target="_blank"}
- [Project Page](https://cepdnaclk.github.io/{{ page.repository-name}}){:target="_blank"}
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)

[//]: # (Please refer this to learn more about Markdown syntax)
[//]: # (https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
