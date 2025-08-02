from utils import load_models_from_file, load_timestamp_from_file, DeepinfraModelPriced
import time
import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Set

# Add the project root to the path to allow a direct run
sys.path.append(str(Path(__file__).parent))

CACHE_DIR = Path(os.path.join(str(Path(__file__).parent), "cache"))

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def find_cache_files() -> List[str]:
    """Finds all cache files and returns their hashes."""
    if not CACHE_DIR.exists():
        return []
    # Extracts the hash from filenames like 'models_{hash}.json'
    return [p.stem.split('_')[1] for p in CACHE_DIR.glob("models_*.json")]


def compare_models(old: DeepinfraModelPriced, new: DeepinfraModelPriced) -> List[str]:
    """Compares two model objects and returns a list of formatted diff strings."""
    changes = []

    # Compare pricing
    if old.pricing.type != new.pricing.type:
        changes.append(f"{RED}  - type: {old.pricing.type}{RESET}")
        changes.append(f"{GREEN}  + type: {new.pricing.type}{RESET}")

    if old.pricing.normalized_input_price != new.pricing.normalized_input_price:
        changes.append(f"{RED}  - normalized_input_price: {old.pricing.normalized_input_price:0.3f}{RESET}")
        changes.append(f"{GREEN}  + normalized_input_price: {new.pricing.normalized_input_price:0.3f}{RESET}")

    if old.pricing.normalized_output_price != new.pricing.normalized_output_price:
        changes.append(f"{RED}  - normalized_output_price: {old.pricing.normalized_output_price:0.3f}{RESET}")
        changes.append(f"{GREEN}  + normalized_output_price: {new.pricing.normalized_output_price:0.3f}{RESET}")

    # Compare other attributes
    if old.quantization != new.quantization:
        changes.append(f"{RED}  - quantization: {old.quantization}{RESET}")
        changes.append(f"{GREEN}  + quantization: {new.quantization}{RESET}")

    if old.deprecated != new.deprecated:
        changes.append(f"{RED}  - deprecated (timestamp): {old.deprecated}{RESET}")
        changes.append(f"{GREEN}  + deprecated (timestamp): {new.deprecated}{RESET}")

    if old.replaced_by != new.replaced_by:
        changes.append(f"{RED}  - replaced_by: {old.replaced_by}{RESET}")
        changes.append(f"{GREEN}  + replaced_by: {new.replaced_by}{RESET}")

    return changes


def main():
    available_hashes = find_cache_files()
    if not available_hashes:
        print("No cache files found in `cache/`. Run `monitor.py` first.")
        sys.exit(1)
    
    available_hashes_list = []
    for _hash in available_hashes:
        hash_timestamp = load_timestamp_from_file(os.path.join(CACHE_DIR, f"models_{_hash}.json"))
        available_hash_str = f"{_hash}"
        if hash_timestamp:
            available_hash_str += " - " + time.strftime("%a %b %d %H:%M:%S %Y", time.gmtime(hash_timestamp))
        available_hashes_list.append("\n\t" + available_hash_str)
        
    available_hashes = ''.join(available_hashes_list)

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
    args = parser.parse_args()

    hash1, hash2 = args.hash1, args.hash2

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

    print(f"\nComparing states: {YELLOW}{hash1}{RESET} -> {YELLOW}{hash2}{RESET}")
    print("---")

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
        print(f"{GREEN}[ADDED] Model: '{name}'{RESET}")
        print(f"{GREEN}  + {model}{RESET}")

    # 2. Report Removed Models
    for name in sorted(list(removed_models)):
        changes_found = True
        model = models_old[name]
        print(f"{RED}[REMOVED] Model: '{name}'{RESET}")
        print(f"{RED}  - {model}{RESET}")

    # 3. Report Modified Models
    for name in sorted(list(common_models)):
        old_model = models_old[name]
        new_model = models_new[name]

        if old_model != new_model:
            changes_found = True
            diffs = compare_models(old_model, new_model)

            # Use a special tag for deprecation events
            if old_model.deprecated == 0 and new_model.deprecated > 0:
                print(f"{YELLOW}[DEPRECATED] Model: '{name}'{RESET}")
            else:
                print(f"{BLUE}[CHANGE] Model: '{name}'{RESET}")

            for line in diffs:
                print(line)

    if not changes_found:
        print("No differences found between the two snapshots.")
    else:
        print("---")


if __name__ == "__main__":
    main()
