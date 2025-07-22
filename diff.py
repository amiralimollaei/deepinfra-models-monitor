import json
from utils import load_models_from_file


hash1 = "ff10b2935fc09bc72f3cf259eaa6f1aea7efc247fd5797fa0e75c1b1bbcdfcec"
hash2 = "0c0d22bb68f2e47248f9cad32fb17e3f07ad8b610f46ad626a1fb9bcc486845f"

checkpoint1 = load_models_from_file(f"cache/models_{hash1}.json")
checkpoint2 = load_models_from_file(f"cache/models_{hash2}.json")

for diff in checkpoint1.difference(checkpoint2):
    print(f"Removed: {diff}")

for diff in checkpoint2.difference(checkpoint1):
    print(f"Added: {diff}")