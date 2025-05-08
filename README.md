 # Lambda Labs Watchdog

 A simple Python script to monitor availability of specific GPU instance types on Lambda Labs and send a hilarious Slack alert when they become available.

 ## Features
 - Polls Lambda Labs OpenAPI `/instance-types` endpoint at regular intervals
 - Fuzzy matching on instance type names/descriptions and regions (e.g., "us" matches "us-west-1")
 - Configurable via `.env`, YAML configs, and CLI flags (CLI overrides config)
 - Funny Slack alerts with alarm emojis and humorous text
 - Supports one-shot mode (`--once`) or continuous monitoring

 ## Requirements
 - Python 3.6+
 - Dependencies listed in `requirements.txt`:
   ```
   python-dotenv  # load credentials from .env
   PyYAML         # parse YAML config
   ```

 ### Install
 ```bash
 pip install -r requirements.txt
 ```

 ## Configuration

 ### 1. Environment Variables (.env)
 Create a file named `.env` in the project root with your credentials:
 ```ini
 LAMBDA_API_KEY=your_lambda_api_key_here
 SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
 ```
 These will be auto-loaded by `python-dotenv`.

 ### 2. YAML Config (optional)
 Default config is at `configs/default.yaml`. Copy or edit this file to customize:
 ```yaml
 # configs/default.yaml
 api_key: ""              # or set in .env
 slack_webhook: ""       # or set in .env
 types:
   - "h100"
   - "gh200"
 region: "us"            # fuzzy filter: "us" matches "us-west-1"
 min_gpus: 1              # minimum GPUs per instance type to watch (optional)
 max_gpus: 4              # maximum GPUs per instance type to watch (optional)
 interval: 60             # seconds between polls
 once: false              # true = run once and exit
 ```

 ## Usage
 Run the script directly:
 ```bash
 python3 lambda_watchdog.py
 ```

 ### Override Settings via CLI
 - `-k`, `--api-key`: Lambda Labs API key
 - `-w`, `--slack-webhook`: Slack webhook URL
 - `-c`, `--config`: Path to YAML config file (default `configs/default.yaml`)
 - `-t`, `--type`: Instance type substring to watch (can specify multiple)
 - `-r`, `--region`: Fuzzy region filter (e.g., `eu`, `us`)
 - `--min-gpus`: Minimum GPUs per instance type to watch
 - `--max-gpus`: Maximum GPUs per instance type to watch
 - `--no-slack`: Disable Slack notifications; only log to CLI
 - `-i`, `--interval`: Polling interval in seconds
 - `--once`: Run once and exit (no loop)

 #### Example
 ```bash
 python3 lambda_watchdog.py \
   --type h100 --type gh200 \
   --region us \
   --interval 30
 ```

 ## Logging & Output
 The script logs to stdout with timestamps. When an instance match is found, it sends a Slack message and exits with status 0.

 ## Slack Alert Style
 The Slack message has a header and body per GPU type, e.g.:
 ```
 🚨🚨🚨 MAJOR BAG ALERT: H100 🚨🚨🚨
 BRUH MOMENT! h100 is AVAILABLE in us-west-1! Time to hop on the grind and secure that GPU!
 ```

 Enjoy your 🚀 GPU hunting! Feel free to tweak the messages or add more features.