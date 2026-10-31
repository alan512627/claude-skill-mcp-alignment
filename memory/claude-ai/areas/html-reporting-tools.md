---
name: html-reporting-tools
description: Suite of HTML reporting and visualization tools across hardware test domains
sources: [backfill]
aliases: [gpu_top_viewer.html]
---
- [stated] Building and refining a suite of HTML reporting and visualization tools across multiple hardware test domains
- [stated] Recurring deliverable pattern: fully self-contained dark-themed HTML files with no external CDN dependencies
- [stated] Built a dark-themed side-by-side GPU+CPU log viewer (gpu_top_viewer.html) parsing nvidia-smi and Linux `top` outputs for U27/U28 systems, with color-coded highlights and timestamp-aligned blocks
- [stated] Worked on NVQual PCIe SBR qualification test log analysis for a C4A15 (GB110) platform, generating a multi-tab HTML report with collapsible raw log sections for failed BDFs
- [stated] Produced a standalone self-contained HTML reference guide for NVIDIA NemoClaw architecture, covering its agent, sandbox, and API/MCP patterns
- [stated] (Earlier) Built a firmware Recipe comparison tool for Azure GPU Compute GB300 ARM Gen11 platform firmware recipes — first as Python/Excel comparison with openpyxl highlighting, then as a full two-version web app with LCS character-level diff, severity classification, and multi-file timeline tracking
- [stated] (Earlier) Refactored a LINE chat command reference tool (line_cmd_report_v2.html) with cross-tab search, click-to-copy, and collapsible fields
- [stated] (Long-term) Built Excel and interactive HTML dashboards with Chart.js for RSCM CLI command validation test logs — multi-session DUT test results, file renaming pipelines keyed to golden command lists, and cross-session failure diff analysis
- [stated] (Long-term) Developed an offline OCR web tool using Tesseract.js with parallel Web Workers, image preprocessing pipelines, and Claude API integration for result aggregation
- [stated] (Long-term) Built Linux system administration tooling for Ubuntu 24.04 — sysinfo dashboards, sysctl analysis, NUMA/CPU freq visualization
