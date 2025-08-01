# DeepInfra Models Monitor
[![CodeFactor](https://www.codefactor.io/repository/github/amiralimollaei/deepinfra-models-monitor/badge)](https://www.codefactor.io/repository/github/amiralimollaei/deepinfra-models-monitor)

A lightweight, un-opinionated utility for detecting and logging model and pricing changes on the DeepInfra platform.

## Overview

This project provides the core functionality to track the DeepInfra model catalog. It's designed for developers who need a reliable way to detect changes but want to implement their own logic for handling them (e.g., sending alerts, updating a database, or triggering a CI/CD pipeline).

The monitor detects:
- **Price Changes:** Including subtle changes in pricing units.
- **New Models:** When new models are added to the platform.
- **Removed Models:** When models are no longer listed.
- **Quantization Changes:** e.g., a model switching from FP16 to INT8.
- **Deprecation Status:** When a model is marked as deprecated or its replacement model changes.

This utility **only detects and logs changes** to standard output and cache files. What you do with that information is entirely up to you.

## How It Works

The script operates in a simple, robust cycle:

1.  **Fetch:** It requests the complete list of models from the DeepInfra API.
2.  **Normalize:** It intelligently normalizes prices to ensure accurate comparisons. For example, a change from `$1 per 1024x1024 image` to `$1 per 512x512 image` is correctly identified as a 4x price increase, even though the dollar amount is the same.
3.  **Generate Snapshot:** It calculates an order-independent hash of the entire normalized model catalog. This hash represents the unique state of the catalog at a specific point in time.
4.  **Detect & Compare:**
    - It saves the current snapshot to a new file in the `cache/` directory, named `models_{hash}.json`.
    - If this file hash is new, it signifies that a change has occurred.
    - The script then implements basic functionality to perform a diff against any two cached states to identify and report the specific changes.

## Getting Started

### Prerequisites
- Python 3.10 or higher

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/amiralimollaei/deepinfra-models.git
    cd deepinfra-models
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Usage

The primary entry point is `monitor.py`.
It is meant to run periodically in the background.

```bash
python monitor.py
