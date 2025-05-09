# Lambda Labs Watchdog

A simple Python script to monitor GPU availability on Lambda Labs and alert via Slack.

## Features
- Polls `/instance-types` endpoint on Lambda Labs OpenAPI
- Fuzzy matching for instance types and regions (e.g., "us" matches "us-west-1")
- Configurable via `.env`, YAML, or CLI (CLI overrides all)
- Slack alerts with GPU availability info
- Supports one-shot (`--once`) or continuous monitoring

## Requirements
- Python 3.6+
- Install deps:
  ```bash
  pip install -r requirements.txt
  ```

## Config

### 1. `.env`
```ini
LAMBDA_API_KEY=your_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

### 2. YAML (`configs/default.yaml`)
```yaml
api_key: ""
slack_webhook: ""
types: ["h100", "gh200"]
region: "us"
min_gpus: 1
max_gpus: 4
interval: 60
once: false
```

## Usage
Run directly:
```bash
python3 lambda_watchdog.py
```

### CLI Overrides
- `-k`, `--api-key`
- `-w`, `--slack-webhook`
- `-c`, `--config`
- `-t`, `--type`
- `-r`, `--region`
- `--min-gpus`, `--max-gpus`
- `-i`, `--interval`
- `--once`
- `--no-slack`

Example:
```bash
python3 lambda_watchdog.py --type h100 --region us --interval 30
```

## Alerts
Logs to stdout and (optionally) sends a Slack alert like:
```
🚨 H100 available in us-west-1 — go grab it
```
