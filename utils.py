from typing import Optional
from dataclasses import dataclass, asdict
from enum import StrEnum
import json

import requests


class DeepinfraModelPricingType(StrEnum):
    TIME = "time"
    TOKENS = "tokens"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    INPUT_CHARACTER_LENGTH = "input_character_length"
    OUTPUT_CHARACTER_LENGTH = "output_character_length"  # doesn't exist in the API, but is used for consistency with other types
    INPUT_LENGTH = "input_length"
    OUTPUT_LENGTH = "output_length"  # doesn't exist in the API, but is used for consistency with other types
    IMAGE_UNITS = "image_units"

    @property
    def input_price_key(self) -> Optional[str]:
        """
        Input price is the price that is directly predictable with the input to the model.

        It is used to calculate the cost of processing the input data.

        For example, inference time is NOT an input price, becuase it is not directly associated
        with the input data.
        """
        match self:
            case DeepinfraModelPricingType.IMAGE_UNITS:
                return "cents_per_image_unit"
            case DeepinfraModelPricingType.TIME:
                return None
            case DeepinfraModelPricingType.TOKENS:
                return "cents_per_input_token"
            case DeepinfraModelPricingType.INPUT_TOKENS:
                return "cents_per_input_token"
            case DeepinfraModelPricingType.OUTPUT_TOKENS:
                return None
            case DeepinfraModelPricingType.INPUT_CHARACTER_LENGTH:
                return "cents_per_input_chars"
            case DeepinfraModelPricingType.OUTPUT_CHARACTER_LENGTH:
                return None
            case DeepinfraModelPricingType.INPUT_LENGTH:
                return "cents_per_input_sec"
            case DeepinfraModelPricingType.OUTPUT_LENGTH:
                return None

    @property
    def output_price_key(self) -> Optional[str]:
        """
        Output price is the price that is associated with the output of the model in runtime
        and is not predictable.

        It is used to calculate the cost of processing the output data.

        For example, inference time is an output price, because it is not directly associated
        with the runtime.
        """
        match self:
            case DeepinfraModelPricingType.IMAGE_UNITS:
                return None
            case DeepinfraModelPricingType.TIME:
                return "cents_per_sec"
            case DeepinfraModelPricingType.TOKENS:
                return "cents_per_output_token"
            case DeepinfraModelPricingType.INPUT_TOKENS:
                return None
            case DeepinfraModelPricingType.OUTPUT_TOKENS:
                return "cents_per_output_token"
            case DeepinfraModelPricingType.INPUT_CHARACTER_LENGTH:
                return None
            case DeepinfraModelPricingType.OUTPUT_CHARACTER_LENGTH:
                return "cents_per_output_chars"
            case DeepinfraModelPricingType.INPUT_LENGTH:
                return None
            case DeepinfraModelPricingType.OUTPUT_LENGTH:
                return "cents_per_output_sec"

    @property
    def is_input_priced(self) -> bool:
        return self.input_price_key is not None

    @property
    def is_output_priced(self) -> bool:
        return self.output_price_key is not None

    @property
    def is_priced(self) -> bool:
        return self.is_input_priced or self.is_output_priced

    @property
    def image_unit_default_width_key(self) -> str:
        return "default_width"

    @property
    def image_unit_default_height_key(self) -> str:
        return "default_height"

    @property
    def image_unit_default_iterations_key(self) -> str:
        return "default_iterations"


@dataclass(frozen=True)
class DeepinfraImageUnitDefaults:
    width: float
    height: float
    iterations: float

    @property
    def pixel_ops(self) -> float:
        return (self.width * self.height * self.iterations) or 1024 * 1024 * 25


@dataclass(frozen=True)
class DeepinfraModelPricing:  # prices are in cents
    type: DeepinfraModelPricingType
    normalized_input_price: Optional[float]
    normalized_output_price: Optional[float]


@dataclass(frozen=True)
class DeepinfraModelPriced:
    """ 
    Represents a Deepinfra model with all the information we want to hash and compare.
    This includes the model name, pricing information, deprecation status, and quantization.
    """
    name: str
    pricing: DeepinfraModelPricing
    deprecated: int  # the timestamp when the model was deprecated, or 0 if not deprecated
    replaced_by: Optional[str] = None
    quantization: Optional[str] = None  # e.g. "fp16", "int8", etc.


def fetch_models() -> set[DeepinfraModelPriced]:
    response = requests.get(
        url="https://api.deepinfra.com/models/list",
        headers={
            "Content-Type": "application/json"
        }
    )
    if response.status_code == 200:
        responce_data = response.json()
        models = set()
        for model_data in responce_data:
            pricing_data = model_data["pricing"]
            pricing_type = DeepinfraModelPricingType(pricing_data["type"])
            input_price = pricing_data[pricing_type.input_price_key] if pricing_type.input_price_key else None
            output_price = pricing_data[pricing_type.output_price_key] if pricing_type.output_price_key else None
            image_unit_defaults = DeepinfraImageUnitDefaults(
                width=pricing_data[pricing_type.image_unit_default_width_key],
                height=pricing_data[pricing_type.image_unit_default_height_key],
                iterations=pricing_data[pricing_type.image_unit_default_iterations_key]
            ) if pricing_type == DeepinfraModelPricingType.IMAGE_UNITS else None
            # normalize prices
            normalized_input_price = input_price
            normalized_output_price = output_price
            match pricing_type:
                case DeepinfraModelPricingType.IMAGE_UNITS:
                    assert input_price is not None, "Input price must be specified for image units pricing type"
                    assert image_unit_defaults is not None, "Image unit defaults must be specified for image units pricing type"
                    # convert to price per megapixel iteration
                    normalized_input_price = input_price / (image_unit_defaults.pixel_ops / 1024 / 1024)
                case DeepinfraModelPricingType.TOKENS:
                    # convert to price per 1M tokens
                    normalized_input_price = input_price * 1000000 if input_price else None 
                    normalized_output_price = output_price * 1000000 if output_price else None
                case DeepinfraModelPricingType.INPUT_TOKENS:
                    # convert to price per 1M tokens
                    normalized_input_price = input_price * 1000000 if input_price else None
                case DeepinfraModelPricingType.OUTPUT_TOKENS:
                    # convert to price per 1M tokens
                    normalized_output_price = output_price * 1000000 if output_price else None
                case DeepinfraModelPricingType.INPUT_CHARACTER_LENGTH:
                    # convert to price per 1M characters
                    normalized_input_price = input_price / 1000000 if input_price else None
                case DeepinfraModelPricingType.OUTPUT_CHARACTER_LENGTH:
                    # convert to price per 1M characters
                    normalized_output_price = output_price / 1000000 if output_price else None
                case DeepinfraModelPricingType.INPUT_LENGTH:
                    # convert to price per minute
                    normalized_input_price = input_price / 60 if input_price else None
                case DeepinfraModelPricingType.OUTPUT_LENGTH:
                    # convert to price per minute
                    normalized_output_price = output_price / 60 if output_price else None
            pricing = DeepinfraModelPricing(
                type=pricing_type,
                normalized_input_price=normalized_input_price,
                normalized_output_price=normalized_output_price,
            )
            model = DeepinfraModelPriced(
                name=model_data["model_name"],
                pricing=pricing,
                deprecated=model_data["deprecated"],
                replaced_by=model_data["replaced_by"],
                quantization=model_data["quantization"]
            )
            models.add(model)
        return models
    else:
        raise requests.HTTPError(f"Failed to fetch models: {response.status_code} {response.text}")


def save_models_to_file(models: set[DeepinfraModelPriced] | list[DeepinfraModelPriced], filename: str) -> None:
    # sort models for consistent output
    sorted_models = sorted(models, key=lambda m: m.name)
    models_serialized = [asdict(model) for model in sorted_models]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(models_serialized, f, ensure_ascii=False, indent=2)


def load_models_from_file(filename: str) -> set[DeepinfraModelPriced]:
    with open(filename, "r", encoding="utf-8") as f:
        models_loaded = json.load(f)
        models_set_loaded = set()
        for model_kwargs in models_loaded:
            # deserialize pricing
            pricing = DeepinfraModelPricing(**model_kwargs["pricing"])
            model_kwargs["pricing"] = pricing
            # deserialize DeepinfraModel
            models_set_loaded.add(DeepinfraModelPriced(**model_kwargs))
    return models_set_loaded


if __name__ == "__main__":
    # Example usage of the fetch_models function

    models_set = fetch_models()

    print(f"Fetched {len(models_set)} models:")
    models_serialized = []
    for model in models_set:
        print(model)
        models_serialized.append(asdict(model))

    # test serialization and deserialization

    save_models_to_file(models_set, "models.json")
    print("Models saved to models.json")

    models_set_loaded = load_models_from_file("models.json")
    print(f"Loaded {len(models_set_loaded)} models from file.")

    assert models_set == models_set_loaded, "Models loaded from file do not match the original set"
