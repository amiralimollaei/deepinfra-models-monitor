# DeepInfra Models Monitor

[![CodeFactor](https://www.codefactor.io/repository/github/amiralimollaei/deepinfra-models-monitor/badge)](https://www.codefactor.io/repository/github/amiralimollaei/deepinfra-models-monitor)

A lightweight, un-opinionated utility for detecting and logging model and pricing changes on the DeepInfra platform.

## Overview

This project provides the core functionality to track the DeepInfra model catalog. It's designed for developers who need a reliable way to detect changes but want to implement their own logic for handling them (e.g., sending alerts, updating a database, or triggering a CI/CD pipeline).

The monitor detects:

- **Price Changes:** Including subtle changes in pricing units and cached input rates.
- **New Models:** When new models are added to the platform.
- **Removed Models:** When models are no longer listed.
- **Quantization Changes:** e.g., a model switching from FP16 to INT8.
- **Deprecation Status:** When a model is marked as deprecated or its replacement model changes.

This utility **only detects and logs changes** to standard output and cache files. What you do with that information is entirely up to you.

## How It Works

The script operates in a simple, robust cycle:

1. **Fetch:** It requests the complete list of models from the DeepInfra API.
2. **Normalize:** It intelligently normalizes prices to ensure accurate comparisons. For example, a change from `$1 per 1024x1024 image` to `$1 per 512x512 image` is correctly identified as a 4x price increase, even though the dollar amount is the same.
3. **Generate Snapshot:** It calculates an order-independent hash of the entire normalized model catalog. This hash represents the unique state of the catalog at a specific point in time.
4. **Detect & Compare:**
    - It saves the current snapshot to a new file in the `cache/` directory, named `models_{hash}.json`.
    - If this file hash is new, it signifies that a change has occurred.
    - The script then implements basic functionality to perform a diff against any two cached states to identify and report the specific changes.

## Getting Started

### Prerequisites

- Python 3.10 or higher

### Installation & Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/amiralimollaei/deepinfra-models.git
    cd deepinfra-models
    ```

2. **Install dependencies:**

    ```bash
    pip3 install -r requirements.txt
    ```

### Usage

The primary entry point is `monitor.py`.
It is meant to run periodically in the background and it is recomended to run this with a `cron` task every 5 minutes.

```bash
python3 monitor.py
```

### Executing a Script on Change Detection

You can automatically trigger a script whenever `monitor.py` detects a change in the model catalog. This is useful for sending notifications, updating a database, or triggering other automated workflows.

Use the `--exec-on-change` argument to specify the command to run. You can use the following placeholders in your command:
- `{hash}`: This will be replaced with the hash of the new snapshot.
- `{prev_hash}`: This will be replaced with the hash of the previous snapshot.

**Note:** If you use `{prev_hash}` in your command and there is no previous snapshot (e.g., on the first run), the script will print a notice and will not execute the command.

**Examples:**

1.  **Log new snapshots:**

    ```bash
    python3 monitor.py --exec-on-change "echo 'New model snapshot created: {hash}' >> changes.log"
    ```

2.  **Run a diff script automatically:**

    ```bash
    python3 monitor.py --exec-on-change "./my_diff_script.sh {prev_hash} {hash}"
    ```
    This will execute `my_diff_script.sh` with the old and new hashes as arguments, allowing you to automate comparisons.

3.  **Using `diff.py` to log changes:**
    ```bash
    python3 monitor.py --exec-on-change "python3 diff.py {prev_hash} {hash} --json >> changes.jsonl"
    ```
    This command will automatically run the `diff.py` script and append the JSON output to a log file.

### Comparing Snapshots with `diff.py`

Once you have run `monitor.py` and have multiple snapshots in the `cache/` directory. You can compare any two of these snapshots using `diff.py`.

1. **List available snapshots:**

   To see which snapshots are available for comparison, you can run `diff.py` with the `-h` or `--help` flag. This will list all the hashes of the snapshots found in the `cache/` directory, along with the timestamp of when they were created.

   ```bash
   python3 diff.py -h
   ```

2. **Run the diff:**

   To compare two snapshots, provide their hashes as arguments. The first hash should be the older state and the second hash should be the newer state.

   ```bash
   python3 diff.py <hash1> <hash2>
   ```

   For example:

   ```bash
   python3 diff.py fa4123d0d9f0988df103ef02b78fb0d09f1279be8597831ba5787828d55bc14a 5e8f3c7f9b8d2e1a4c6b8a0d9e8f7c6a5b4d3e2f1a0c9b8d7e6f5a4b3c2d1e0f
   ```

3. **JSON Output:**

   For programmatic use, you can get the output in JSON format using the `--json` flag.

   ```bash
   python3 diff.py <hash1> <hash2> --json
   ```
