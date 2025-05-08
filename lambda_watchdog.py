#!/usr/bin/env python3
"""Lambda Labs watchdog script: notify Slack when specified instance types become available."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import logging

from dotenv import load_dotenv

load_dotenv()

DEFAULT_INTERVAL = 60

API_URL = "https://cloud.lambda.ai/api/v1/instance-types"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("lambda_watchdog")


def get_instance_types(api_key):
    api_key = api_key.strip() if api_key else api_key
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "curl/7.79.1",
    }
    logger.info(f"Requesting: {API_URL}")
    req = urllib.request.Request(API_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        logger.error(f"Error fetching instance types: {e.code} {e.reason}")
        if e.code == 403:
            logger.error("--- Response body ---")
            logger.error(e.read().decode())
            logger.error("---------------------")
        sys.exit(1)
    data = json.loads(body)
    return data.get("data", {})


def send_slack_notification(webhook_url, message):
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.getcode() < 200 or resp.getcode() >= 300:
                logger.error(
                    f"Slack notification failed with status {resp.getcode()}"
                )
    except urllib.error.HTTPError as e:
        logger.error(f"Error sending Slack notification: {e.code} {e.reason}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lambda Labs instance availability watchdog"
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=os.getenv("LAMBDA_API_KEY"),
        help="Lambda Labs API key (or set LAMBDA_API_KEY env)",
    )
    parser.add_argument(
        "-w",
        "--slack-webhook",
        default=os.getenv("SLACK_WEBHOOK_URL"),
        help="Slack webhook URL (or set SLACK_WEBHOOK_URL env)",
    )
    parser.add_argument(
        "-t",
        "--type",
        action="append",
        help=(
            "Instance type pattern to watch (can specify multiple, "
            "matches name or description, case-insensitive)"
        ),
    )
    parser.add_argument(
        "-r",
        "--region",
        default=None,
        help="Region filter (fuzzy, e.g., 'us' matches 'us-west-1')",
    )
    parser.add_argument(
        "--min-gpus",
        type=int,
        default=None,
        help="Minimum number of GPUs per instance type to watch",
    )
    parser.add_argument(
        "--max-gpus",
        type=int,
        default=None,
        help="Maximum number of GPUs per instance type to watch",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (do not loop)"
    )
    parser.add_argument(
        "--no-slack",
        action="store_true",
        help="Disable Slack notifications; only log availability to CLI",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    api_key = args.api_key
    if not api_key:
        logger.error(
            "Missing API key. Provide via --api-key or LAMBDA_API_KEY env"
        )
        sys.exit(1)

    slack_webhook = args.slack_webhook
    if not slack_webhook:
        logger.error(
            "Missing Slack webhook URL. Provide via --slack-webhook or SLACK_WEBHOOK_URL env"
        )
        sys.exit(1)

    patterns = args.type
    if not patterns:
        logger.error(
            "Missing instance type patterns. Provide via --type"
        )
        sys.exit(1)
    patterns = [p.lower() for p in patterns]
    logger.info(f"Watching for patterns: {patterns}")

    region_pattern = args.region
    if region_pattern:
        region_pattern = region_pattern.lower()

    interval = args.interval
    once = args.once
    min_gpus = args.min_gpus
    max_gpus = args.max_gpus
    notify_slack = not args.no_slack
    try:
        available_set = set()  # (name, region) tuples currently available and notified
        while True:
            items = get_instance_types(api_key)
            available = {}
            current_found = set()
            for key, info in items.items():
                inst = info.get("instance_type", {})
                name = inst.get("name", "")
                desc = inst.get("description", "")
                gpu_desc = inst.get("gpu_description", "")
                specs = inst.get("specs", {})
                gpus = specs.get("gpus", 0)
                vcpus = specs.get("vcpus", "?")
                memory = specs.get("memory_gib", "?")
                storage = specs.get("storage_gib", "?")
                text = f"{name} {desc}".lower()
                if any(p in text for p in patterns):
                    if min_gpus is not None and gpus < min_gpus:
                        continue
                    if max_gpus is not None and gpus > max_gpus:
                        continue
                    regions = info.get("regions_with_capacity_available", [])
                    if region_pattern:
                        regions = [
                            r
                            for r in regions
                            if r.get("name", "").lower().startswith(region_pattern)
                        ]
                    region_names = [r.get("name") for r in regions]
                    if region_names:
                        available[name] = {
                            "gpus": gpus,
                            "gpu_desc": gpu_desc,
                            "memory": memory,
                            "vcpus": vcpus,
                            "storage": storage,
                            "desc": desc,
                            "regions": region_names,
                        }
                        for region in region_names:
                            current_found.add((name, region))

            # Find new availabilities (newly available)
            new_avail = [ (name, region)
                          for name, info in available.items()
                          for region in info["regions"]
                          if (name, region) not in available_set ]

            # Find disappearances (were available, now gone)
            disappeared = [ (name, region)
                            for (name, region) in available_set
                            if (name, region) not in current_found ]

            if new_avail:
                for name, info in available.items():
                    for region in info["regions"]:
                        if (name, region) in new_avail:
                            gpus = info.get("gpus", 0)
                            gpu_desc = info.get("gpu_desc", "")
                            memory = info.get("memory", "?")
                            vcpus = info.get("vcpus", "?")
                            storage = info.get("storage", "?")
                            desc = info.get("desc", "")
                            logger.info(f"FOUND: {gpus}×{name} ({gpu_desc}) | {memory} GiB RAM | {vcpus} vCPUs | {storage} GiB storage | {desc} | Region: {region}")
                if notify_slack:
                    alerts = []
                    for name, info in available.items():
                        for region in info["regions"]:
                            if (name, region) in new_avail:
                                gpus = info.get("gpus", 0)
                                header = f"🚨🚨🚨 MAJOR BAG ALERT: {gpus}×{name.upper()} 🚨🚨🚨"
                                body = (
                                    f"BRUH MOMENT! {gpus}×{name} is AVAILABLE in {region}! "
                                    "Time to hop on the grind and secure that GPU!"
                                )
                                alerts.append(header)
                                alerts.append(body)
                    if alerts:
                        message = "\n\n".join(alerts)
                        send_slack_notification(slack_webhook, message)
                else:
                    logger.info("Slack notifications are disabled; skipping Slack alert.")
                # Mark these as available
                available_set.update(new_avail)

            if disappeared:
                for name, region in disappeared:
                    logger.info(f"GONE: {name} in {region} is NO LONGER AVAILABLE!")
                if notify_slack:
                    gone_alerts = []
                    for name, region in disappeared:
                        header = f"❌❌❌ GPU GONE: {name.upper()} ❌❌❌"
                        body = f"{name} in {region} is NO LONGER AVAILABLE!"
                        gone_alerts.append(header)
                        gone_alerts.append(body)
                    if gone_alerts:
                        message = "\n\n".join(gone_alerts)
                        send_slack_notification(slack_webhook, message)
                # Remove from available_set
                for pair in disappeared:
                    available_set.discard(pair)

            if not new_avail and not disappeared:
                logger.info(
                    f"No new matching instances available. Retrying in {interval} seconds..."
                )
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Interrupted by user, exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
