from dataclasses import asdict
import json
import time
import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Set

# Add the project root to the path to allow a direct run
sys.path.append(str(Path(__file__).parent))
from utils import DeepinfraModelPricingType, load_models_from_file, load_timestamp_from_file, DeepinfraModelPriced

CACHE_DIR = Path(os.path.join(str(Path(__file__).parent), "cache"))

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_json(**kwargs):
    """Prints data in JSON format."""
    print(json.dumps(kwargs, ensure_ascii=False))


def find_cache_files() -> List[str]:
    """Finds all cache files and returns their hashes."""
    if not CACHE_DIR.exists():
        return []
    # Extracts the hash from filenames like 'models_{hash}.json'
    return [p.stem.split('_')[1] for p in CACHE_DIR.glob("models_*.json")]


def format_pricing(type: DeepinfraModelPricingType, value: float) -> str:
    """Formats a pricing value based on its type."""

    unit = None
    match type:
        case DeepinfraModelPricingType.TIME:
            unit = "runtime seconds"
        case DeepinfraModelPricingType.TOKENS | DeepinfraModelPricingType.INPUT_TOKENS | DeepinfraModelPricingType.OUTPUT_TOKENS:
            unit = "1M tokens"
        case DeepinfraModelPricingType.INPUT_CHARACTER_LENGTH | DeepinfraModelPricingType.OUTPUT_CHARACTER_LENGTH:
            unit = "1M characters"
        case DeepinfraModelPricingType.INPUT_LENGTH | DeepinfraModelPricingType.OUTPUT_LENGTH:
            unit = "audio minutes"
        case DeepinfraModelPricingType.IMAGE_UNITS:
            unit = "1024x1024 image itereation"
        case _:
            raise ValueError(f"Unsupported pricing type: {type}")

    if value is None:
        return f"0.00000 per {unit}"
    return f"${value/100:.5f} per {unit}"


def format_timestamp(value: float) -> str:
    """Formats a timestamp value to a human-readable string."""
    if value is None:
        return "N/A"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(value))


def format_quantization(value: float) -> str:
    """Formats a quantization value."""
    if value is None:
        return "float32"
    return value


def format_multiplier(value: float) -> str:
    """Formats a multiplier (percentage) value."""
    if value is None:
        return "NaN"
    return f"{value*100:0.2f}%"


def compare_models(old: DeepinfraModelPriced, new: DeepinfraModelPriced) -> List[str]:
    """Compares two model objects and returns a list of formatted diff strings."""
    changes = []

    # Compare pricing
    if old.pricing.type != new.pricing.type:
        changes.append(f"{RED}  - Pricing Type: {old.pricing.type}{RESET}")
        changes.append(f"{GREEN}  + Pricing Type: {new.pricing.type}{RESET}")

    if old.pricing.normalized_input_price != new.pricing.normalized_input_price:
        changes.append(
            f"{RED}  - Input Price: {format_pricing(old.pricing.type, old.pricing.normalized_input_price)}{RESET}")
        changes.append(
            f"{GREEN}  + Input Price: {format_pricing(new.pricing.type, new.pricing.normalized_input_price)}{RESET}")

    if old.pricing.normalized_output_price != new.pricing.normalized_output_price:
        changes.append(
            f"{RED}  - Output Price: {format_pricing(old.pricing.type, old.pricing.normalized_output_price)}{RESET}")
        changes.append(
            f"{GREEN}  + Output Price: {format_pricing(new.pricing.type, new.pricing.normalized_output_price)}{RESET}")

    if old.pricing.rate_per_input_price_cached != new.pricing.rate_per_input_price_cached:
        changes.append(
            f"{RED}  - Cached Input Rate: {format_multiplier(old.pricing.rate_per_input_price_cached)}{RESET}")
        changes.append(
            f"{GREEN}  + Cached Input Rate: {format_multiplier(new.pricing.rate_per_input_price_cached)}{RESET}")

    if old.pricing.rate_per_input_price_cache_write != new.pricing.rate_per_input_price_cache_write:
        changes.append(
            f"{RED}  - Cache Write Input Rate: {format_multiplier(old.pricing.rate_per_input_price_cache_write)}{RESET}")
        changes.append(
            f"{GREEN}  + Cache Write Input Rate: {format_multiplier(new.pricing.rate_per_input_price_cache_write)}{RESET}")

    # Compare other attributes
    if old.quantization != new.quantization:
        changes.append(f"{RED}  - Quantization: {format_quantization(old.quantization)}{RESET}")
        changes.append(f"{GREEN}  + Quantization: {format_quantization(new.quantization)}{RESET}")

    if old.deprecated != new.deprecated:
        changes.append(f"{RED}  - Deprecated (timestamp): {format_timestamp(old.deprecated)}{RESET}")
        changes.append(f"{GREEN}  + Deprecated (timestamp): {format_timestamp(new.deprecated)}{RESET}")

    if old.replaced_by != new.replaced_by:
        changes.append(f"{RED}  - Replaced by: {old.replaced_by}{RESET}")
        changes.append(f"{GREEN}  + Replaced by: {new.replaced_by}{RESET}")

    return changes


def parse_args():
    available_hashes = find_cache_files()
    if not available_hashes:
        print("No cache files found in `cache/`. Run `monitor.py` first.")
        sys.exit(1)

    available_hashes_timestamps = [load_timestamp_from_file(
        os.path.join(CACHE_DIR, f"models_{_hash}.json")
    ) for _hash in available_hashes]

    available_hashes_str_list = []
    for _hash, hash_timestamp in sorted(zip(available_hashes, available_hashes_timestamps), key=lambda x: x[1]):
        available_hash_str = f"{_hash}"
        if hash_timestamp:
            available_hash_str += " - " + time.strftime("%a %b %d %H:%M:%S %Y", time.gmtime(hash_timestamp))
        available_hashes_str_list.append("\n\t" + available_hash_str)
    available_hashes = ''.join(available_hashes_str_list)

    parser = argparse.ArgumentParser(
        description=f"Compare two DeepInfra model snapshots from the cache. \nAvailable: {available_hashes}",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "hash1",
        help=f"The first (older) state hash."
    )
    parser.add_argument(
        "hash2",
        help=f"The second (newer) state hash."
    )
    parser.add_argument("--json",
                        action="store_true",
                        help="Output the differences in JSON format instead of plain text."
                        )
    args = parser.parse_args()
    return args


def diff_modified_models(should_output_json, name, old_model, new_model):
    if should_output_json:
        modified_details = dict()  # only contain modified fields
        if old_model.deprecated != new_model.deprecated:
            modified_details["deprecated"] = dict(
                old=old_model.deprecated,
                new=new_model.deprecated
            )
        if old_model.replaced_by != new_model.replaced_by:
            modified_details["replaced_by"] = dict(
                old=old_model.replaced_by,
                new=new_model.replaced_by
            )
        if old_model.quantization != new_model.quantization:
            modified_details["quantization"] = dict(
                old=old_model.quantization,
                new=new_model.quantization
            )
        if old_model.pricing != new_model.pricing:
            modified_details["pricing"] = dict(
                old=old_model.pricing,
                new=new_model.pricing,
            )
        print_json(event="modified", model=name, details=modified_details)
    else:
        # Use a special tag for deprecation events in plain text output
        if old_model.deprecated == 0 and new_model.deprecated > 0:
            print(f"{YELLOW}[DEPRECATED] Model: '{name}'{RESET}")
        else:
            print(f"{BLUE}[CHANGE] Model: '{name}'{RESET}")

        diffs = compare_models(old_model, new_model)
        for line in diffs:
            print(line)


def main():
    args = parse_args()

    should_output_json = args.json

    hash1, hash2 = args.hash1, args.hash2

    print(f"\nComparing states: {YELLOW}{hash1}{RESET} -> {YELLOW}{hash2}{RESET}")
    print("---")

    if hash1 == hash2:
        print("same hashes provided. No comparison needed.")
        print("---")
        sys.exit(0)

    try:
        models_old_set = load_models_from_file(os.path.join(CACHE_DIR, f"models_{hash1}.json"))
        models_new_set = load_models_from_file(os.path.join(CACHE_DIR, f"models_{hash2}.json"))
    except FileNotFoundError as e:
        print(f"Error: {e}. Make sure the hashes are correct and the cache files exist.")
        sys.exit(1)

    # Convert sets to dictionaries keyed by model name for easy lookup
    models_old: Dict[str, DeepinfraModelPriced] = {m.name: m for m in models_old_set}
    models_new: Dict[str, DeepinfraModelPriced] = {m.name: m for m in models_new_set}

    # --- --- --- --- ---

    old_names: Set[str] = set(models_old.keys())
    new_names: Set[str] = set(models_new.keys())

    removed_models = old_names - new_names
    added_models = new_names - old_names
    common_models = old_names & new_names

    changes_found = False

    # 1. Report Added Models
    for name in sorted(list(added_models)):
        changes_found = True
        model = models_new[name]
        if should_output_json:
            print_json(event="added", model=name, details=asdict(model))
        else:
            print(f"{BLUE}[ADDED] Model: '{name}'{RESET}")
            print(f"{GREEN}  + {model}{RESET}")

    # 2. Report Removed Models
    for name in sorted(list(removed_models)):
        changes_found = True
        model = models_old[name]
        if should_output_json:
            print_json(event="removed", model=name)
        else:
            print(f"{BLUE}[REMOVED] Model: '{name}'{RESET}")
            print(f"{RED}  - {model}{RESET}")

    # 3. Report Modified Models
    for name in sorted(list(common_models)):
        old_model = models_old[name]
        new_model = models_new[name]

        if old_model != new_model:
            changes_found = True
            diff_modified_models(should_output_json, name, old_model, new_model)

    if not changes_found:
        print("No differences found between the two snapshots.")
    print("---")


if __name__ == "__main__":
    main()
