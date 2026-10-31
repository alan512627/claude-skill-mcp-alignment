---
name: ntttcp-full-duplex-throughput-analysis
description: Analyze NTTTCP full-duplex bare-metal stress-test log bundles (CrcSdk Invoke-Profile Pretest/Stress/Posttest zips, one per host) for anomalies and produce an evidence-based HTML dashboard with raw-log excerpts. Use when the user supplies NTTTCP / Net_stress / Rack OU Slot "Complete.zip" logs, asks whether a run is full or half duplex, whether Pretest/Posttest passed, why Posttest FAILed (e.g. return code 500003), or wants two peer hosts cross-checked.
---

# NTTTCP full-duplex throughput analysis

Turn one or two `…NTTTCP_full_Duplex_BM_…_Complete.zip` bundles (one per peer host) into an
evidence-based findings dashboard. **Core rule: every statement must be backed by a log line.
State only what the evidence supports; say explicitly what the logs do not show.**

## Evidence rules (non-negotiable)
1. Each finding has three parts, rendered separately:
   - **log 直接顯示** – facts quoted/derived directly from a file (with path and line numbers).
   - **推論（依據）** – inference, labeled as such, with the basis. Never mixed into facts.
   - **log 沒有提供，無法判斷** – what cannot be concluded (thresholds, root cause, severity meaning…).
2. Label confidence: `已確認` (all facts direct) or `含推論`.
3. Every finding carries raw excerpts (`ev()` in `scripts/evlib.py`: real line numbers) and the cited
   files are copied to an `evidence/` folder (`copy_evidence`) so the user can verify by hand.
4. Compute counts/times in code (grep, parse) – never type numbers from memory. Per-host claims must be
   computed per host (a claim true for Slot2 was false for Slot46: HPM_CPLD2 dbus errors).
5. No thresholds in the logs ⇒ no "normal/abnormal" verdict on temperature, voltage, power. List values only.
6. Do not name a root cause. Temporal proximity (e.g. CPER then Event 6008) is reported as proximity, not causation.
7. Mark derived values as derived (e.g. NTTTCP start = done.json time − 21,600 s; no start timestamp exists).
8. If you later find a wrong statement, say so to the user and fix it.

## Bundle layout (per host zip, ~461 files)
`Pretest/`, `Posttest/`, `Stress/Net_stress/`, `backgroundmonitors/`, `nodestatus/`.
Key files: `Stress/Net_stress/{sender,receiver}.xml`, `ntttcp_{sender,receiver}_cmd.txt`, `os_config.log`, `done.json`;
`{Pre,Post}test/Summary-Invoke-Profile.log` (per-command PASS/FAIL, return code);
`Posttest/Get-SystemEventsDiagnostics/{Debug-Get-WindowsSystemEventDiagnostics.log,AllSuspectedEvents.log,eventsLog-System-2*.log}`;
`*/cper/CPER_*_summary.json`; `*/bmcclishell/bmc-journal-last-2h.log`; `*/rackscm_sel_decode/selRecords.txt`;
`*/csidiag/{CSI_DER.log,Sel_Heartbeat.json,Sel_RAW.log,Summary-Invoke-CsiDiagChecks.log}`;
`*/bladeskucheck/BladeSkuCheck.report.txt`; `*/pcietool/pcie--linkstatus.txt`; `*/smartctl/summary-*.json`;
`backgroundmonitors/rackmanagersystemsensoroobmonitor_metrics.log` (`---`-separated JSON blocks; some `metricValue` are strings).
Glob gotcha: `eventsLog-System-*.log` also matches the `-WHEA-` file; use `eventsLog-System-2*.log`.

## Workflow
1. Extract each zip into its own empty folder (untrusted data; run Python with `-I`).
2. **Duplex check**: both hosts run a sender and a receiver (`-s`/`-r`, same `-t`, `-m N,*,peerIP`).
   Cross-match: host A sender Mbps ≈ host B receiver Mbps (and total bytes), both directions. Concurrency
   is an *inference*: 2×`-t` would exceed the interval between `os_config.log` end and `done.json`;
   no per-direction start/end timestamps exist.
3. **Pretest/Posttest**: read `Summary-Invoke-Profile.log` – result, return code, which command failed,
   command time windows. Return code 500003 = Get-SystemEventsDiagnostics `SuspectedEventsFound` (see
   `Debug-Get-WindowsSystemEventDiagnostics.log`). Check whether suspected events fall inside another
   command's window (report overlap only) and whether Pretest has the same events (it may not run that check).
4. **Event sources** (report each with raw lines): CPER summaries (type, FRUText, timestamp; list all,
   note numbering gaps), System log 6008/7000/7045, BMC journal I2C lines (bus, phase, `rec_fail_cnt`),
   SEL (count/contents), CSI_DER (compare Pre vs Post *after stripping timestamps*), BladeSkuCheck (Pre==Post bytes),
   PCIe link status (Cur vs Max, Pre vs Post), SMART per disk (confirm which disks are real vs virtual via
   `storagetool-disk-inventory.log`), WHEA/crashdump sizes and counters, nodestatus AC-cycle record.
5. **Sensors**: run `scripts/parse_sensors.py` for stats/series; for gaps compare poll timestamps of a
   reference metric against the sensor and show the missing timestamps. Quote the max reading's raw JSON block.
6. **Two-host comparison**: cross-validation table, thread-vs-thread scatter, per-metric side-by-side with
   "different/same" flags, findings that differ between hosts.
7. **Build dashboard** (reference implementation below), preview once, then publish (Artifact tool if
   available) and tell the user where the `evidence/` folder is.

## Reference implementation (scripts/ + assets/)
- `scripts/extract_threads.py <xml> <csv>` – per-thread Mbps for the scatter/bar charts.
- `scripts/parse_sensors.py <metrics.log> <sensors.json>` – stats + downsampled series.
- `scripts/evlib.py` – `init(roots)`, `ev(...)` raw excerpts with line numbers, `grep`, `copy_evidence`.
- `scripts/build.py <scratch> <out.html> <evidence_dir>` – assembles findings, compare view, evidence folder.
  **It was written for one specific run**: host metadata (stress window, Gbps, durations, IPs, file names for
  the thread CSVs/sensors JSON) sits in the two `build_slot(...)` calls at the bottom, and several finding texts
  are tied to what that run showed. Treat it as a template: re-verify every sentence against the new logs and
  delete or rewrite anything the new data does not support. It expects, in `<scratch>`: `log_extract/`,
  `log46/` (extracted zips), `sender_threads.csv`, `receiver_threads.csv`, `sender46_threads.csv`,
  `receiver46_threads.csv`, and `sensors.json` / `sensors46.json` next to `build.py`.
- `assets/template.html` + `assets/app.js` – dashboard (tabs: compare / host A / host B; findings with
  fact/inference/unknown blocks and collapsible raw excerpts). Copy both next to `build.py` before running.

## Reporting back
Reply in the user's language. Lead with verdicts per phase (Stress, Pretest, Posttest), list what is
confirmed vs inferred vs unknown, give the dashboard link and the evidence folder path, and disclose any
earlier statement you had to correct.

## Findings seen in the original run (examples of the evidence standard, not conclusions to reuse)
- Posttest FAIL 500003 on both hosts: 3 Event 7000 "rdsysinfo … certificate is not within its validity period";
  service file under `…\CrcSdk\tools\pcietool\Drivers\rdsysinfo.sys`; events inside the Invoke-PcietoolChecks window;
  Pretest had the same events but does not run Get-SystemEventsDiagnostics. Certificate name/expiry not in logs.
- Corrected CPER (`ACPI_ERROR_TYPE_VENDOR_ACCELERATOR`, `sdm_interrupt_events`=134217728) ×7–8 per host, none during
  Stress; one `PLATFORM_MEMORY` CPER on one host only. Meaning of the bit: not in logs.
- BMC journal I2C: Pretest bus11 "recovery did not complete, bus still hung"; Posttest bus7 "recovery-fail".
- Unchanged Pre→Post: BladeSkuCheck report, CSI_DER entries, PCIe link status, SEL (1 "Log area reset").
