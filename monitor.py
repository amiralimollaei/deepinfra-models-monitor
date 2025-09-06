from dataclasses import asdict
import sys
from pathlib import Path
import os
import hashlib
import argparse
import subprocess

# Add the project root to the path to allow a direct run
sys.path.append(str(Path(__file__).parent))
from utils import DeepinfraModelPriced, fetch_models, save_models_to_file, load_timestamp_from_file

CACHE_DIR = Path(os.path.join(str(Path(__file__).parent), "cache"))


def create_order_independent_hash(models: set[DeepinfraModelPriced]) -> str:
    """
    Creates a hash that is independent of the order of models.
    """
    model_hashes = [str(asdict(model)) for model in models]
    model_hashes.sort()
    return hashlib.sha256(("\n".join(model_hashes)).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor DeepInfra models for changes and run a script if a change is detected.")
    parser.add_argument("--exec-on-change", dest="exec_script", type=str, help="The script to execute when a change is detected. Use {hash} as a placeholder for the new cache file hash and {prev_hash} for the previous one.")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)


    models = fetch_models()
    order_independant_hash = create_order_independent_hash(models)

    # Save models to a file
    cache_file_path = os.path.join(CACHE_DIR, f"models_{order_independant_hash}.json")
    if os.path.exists(cache_file_path):
        print(f"Cache file already exists: {cache_file_path}")
        print("Pricing is not updated, skipping saving to file.")
    else:
        print(f"Cache file does not exist: {cache_file_path}")
        print("Pricing is updated, saving models to file.")
        save_models_to_file(models, cache_file_path)

        if args.exec_script:
            command = args.exec_script
            if "{prev_hash}" in command:
                # Find previous hash
                cache_files = [f for f in CACHE_DIR.glob("models_*.json") if f.is_file()]
                prev_hash = None
                if cache_files:
                    latest_cache_file = max(cache_files, key=lambda f: load_timestamp_from_file(str(f)) or 0)
                    prev_hash = latest_cache_file.stem.split('_', 1)[1]

                if prev_hash:
                    command = command.replace("{prev_hash}", prev_hash)
                else:
                    print("Notice: --exec-on-change command contains {prev_hash} but no previous cache file was found. Skipping execution.")
                    sys.exit(0)
            
            command = command.replace("{hash}", order_independant_hash)
            print(f"Executing command: {command}")
            try:
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                print("Script executed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error executing script: {e}")
                print(f"Stdout: {e.stdout}")
                print(f"Stderr: {e.stderr}")
