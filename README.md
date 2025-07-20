# DeepInfra Models Monitor

This project is designed to monitor price changes, additions, removals, quantization changes, and deprecations of models available on DeepInfra. It helps users stay up-to-date with the latest changes in the DeepInfra model catalog.

## Features

- **Price Change Detection:** Tracks and reports any changes in model pricing.
- **New Model Detection:** Identifies and lists newly added models.
- **Model Removal Detection:** Alerts when models are removed from the catalog.
- **Quantization Change Detection:** Detects changes in model quantization (e.g., from FP16 to INT8).
- **Deprecation Alerts:** Notifies when models are marked as deprecated.

## Usage

1. **Setup:**
   - Ensure you have Python 3.8+ installed.
   - Clone this repository and install any required dependencies (see below).

2. **Running the Monitor:**
   - Execute `monitor.py` to start monitoring DeepInfra models.
   - The script will compare the current model list with the cached data and report any changes.

3. **Cache:**
   - Model data is cached in the `cache/` directory for change detection between runs.

## Requirements

- Python 3.10 or higher

## File Structure

- `monitor.py` — Main script for monitoring and reporting changes.
- `utils.py` — Utility functions used by the monitor.
- `cache/` — Stores cached model data for comparison.

## License

MIT License. See `LICENSE` file for details.
