# Python Utilities for Control-M Automation

This directory contains **Python scripts designed to automate and extend BMC Control-M functionality** using the **Control-M Automation API** and supporting utilities.

These scripts help automate common operational tasks such as:

- Monitoring job status
- Detecting schedule delays
- Sending alerts on delay
- Extracting Control-M planning domain information
- Interacting with Control-M services through REST APIs

---

## Purpose

Control-M environments often require custom automation beyond the default UI capabilities.  
The scripts in this directory provide **lightweight command-line utilities** to interact with Control-M programmatically.

Typical use cases include:

- Job monitoring automation
- SLA violation detection
- Alerting systems integration
- Data extraction for reporting
- Operational workflow automation

---

## Scripts

| Script | Description |
|------|-------------|
| `delayedJobAlerts.py` | Detects jobs running beyond expected schedule thresholds |
| `sms_script.py` | Sends SMS alerts when invoked |
| `extrct_dtls_frm_exprtd_plning_file.py` | Extracts job and folder information from exported JSON file from planning domain |
| `export_job_frm_planing.py` | Take configuration backup from Control-M planning
| `exportViewpoint.py` | Export Control-M Viewpoint to a JSON file
| `utils/ctm_submodules.py` | Helper utilities for interacting with the Control-M Automation API |

*(Script names may vary depending on your repository.)*

---

## Requirements

- Python 3.8+
- `requests` library
- `dotenv` library
- `twilio` library
- Network access to the Control-M Automation API server

Install required dependency:

```bash
pip install requests