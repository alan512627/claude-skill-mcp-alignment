---
name: overview
description: Callan HRU cooling rack test automation — purpose, connection details, active scripts, current state of TC3642020 work
project: Callan — Python/paramiko test automation for Callan HRU cooling rack firmware updates and telemetry
aliases: [Callan HRU automation, TC3642020, HRU firmware update validation]
---
- [stated] Alan is a hardware/firmware test engineer working on Callan cooling rack systems (Heat Rejection Unit / HRU)
- [stated] Projects involve RSCM (Rack System Controller Module) consoles
- [stated] Work centers on automating test cases for HRU firmware update validation and system telemetry monitoring

## Connection details
- [stated] RSCM IP 192.9.13.8 (Cooling Rack) and 192.9.13.1 (IT Rack), port 22, credentials: <REDACTED — not stored in git>
- [stated] BMC host 192.168.1.2 (credentials: <REDACTED>) for Redfish API progress monitoring

## Current state
- [stated] Automating test case TC3642020 (HRU firmware update validation + telemetry monitoring)
- [stated] Scripts developed in Python using paramiko
- [stated] Moved away from VBScript/MobaXterm macros and TTY macros due to MobaXterm free version limitations
- [stated] Active script: `Callan_status_modbus_V0_3.py` — infinite loop modbus register reads via `RScmCli#` prompt
- [stated] Active script: `Callan_status_HRU_V0_3.py` — infinite loop HRU sensor/control commands via `HRU {admin}>` prompt
- [stated] Active script: `Callan_Setpoint_Check.py` — single-run setpoint check
- [stated] Active script: `TC3642020_HRU_FW_Update.py` — full FW update script with pre/post version comparison, dynamic task number parsing, bash shell curl polling to 100%, `.txt` log and styled `.html` report output
- [stated] Active script: `Launch_FW_Update_with_Monitoring_standalone.py` — standalone launcher opening 4 independent Windows console windows, no MobaXterm dependency
- [stated] Log directory standardized to `r"C:\TestLogs"` across all scripts
- [stated] Pending: alarm list command to be added in HRU console after `hru selftest` in `TC3642020_RSCM_Telemetry.py`

## Tools & resources
- [stated] Python with paramiko for SSH automation; Redfish API for BMC FW update progress polling
- [stated] Windows console environment for multi-window test launching; `.txt` and styled `.html` reports
