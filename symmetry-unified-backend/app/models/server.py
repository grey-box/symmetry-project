from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import wikipediaapi
import re
from app.models.comparison.engine import semantic_compare
from app.models.translation.engine import translate
from huggingface_hub import model_info
from app.core.config import load_config, save_config


def model_exists(model_name: str) -> bool:
    try:
        model_info(model_name)
        return True
    except Exception as e:
        print(e)
        print(
            "You may need to put 'sentence-transformers/' as a prefix before the model name."
        )
        return False


def _load_saved_models() -> dict:
    config = load_config()
    saved_models = config.get("saved_models", {})
    return {
        "huggingface": saved_models.get(
            "huggingface", {"comparison": [], "translation": []}
        ),
        "custom": saved_models.get("custom", {"comparison": [], "translation": []}),
        "selected": saved_models.get(
            "selected",
            {
                "comparison": "sentence-transformers/LaBSE",
                "translation": "/path/to/T5-custom",
            },
        ),
    }


def _save_saved_models(saved_models: dict) -> None:
    config = load_config()
    config["saved_models"] = saved_models
    save_config(config)


def load_saved_models(domain: str, model_type: str):
    saved_models = _load_saved_models()
    return list(saved_models[domain].get(model_type, []))


def update_json(domain: str, model_type: str, new_model_filepath):
    saved_models = _load_saved_models()
    saved_models[domain].setdefault(model_type, [])
    saved_models[domain][model_type].append(str(new_model_filepath))
    _save_saved_models(saved_models)


def update_json_last_selected(domain: str, new_selection):
    saved_models = _load_saved_models()
    if domain == "comparison":
        saved_models["selected"]["comparison"] = new_selection
    else:
        saved_models["selected"]["translation"] = new_selection
    _save_saved_models(saved_models)


def remove_from_json(domain: str, model_type: str, modelname):
    saved_models = _load_saved_models()
    saved_models[domain][model_type] = [
        item
        for item in saved_models[domain].get(model_type, [])
        if item != str(modelname)
    ]
    _save_saved_models(saved_models)


def load_last_selected(for_: str):
    saved_models = _load_saved_models()
    if for_ == "comparison":
        return saved_models["selected"].get("comparison", "sentence-transformers/LaBSE")
    return saved_models["selected"].get("translation", "/path/to/T5-custom")


@dataclass
class ServerModel:
    hf_comparison_models: List[str] = field(
        default_factory=lambda: load_saved_models("huggingface", "comparison")
    )
    hf_translation_models: List[str] = field(
        default_factory=lambda: load_saved_models("huggingface", "translation")
    )

    custom_comparison_models: List[str] = field(
        default_factory=lambda: load_saved_models("custom", "comparison")
    )
    custom_translation_models: List[str] = field(
        default_factory=lambda: load_saved_models("custom", "translation")
    )

    selected_comparison_model: str = field(
        default_factory=lambda: load_last_selected("comparison")
    )
    selected_translation_model: str = field(
        default_factory=lambda: load_last_selected("translation")
    )

    wikipedia: Optional[wikipediaapi.Wikipedia] = field(default=None)

    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        self.wikipedia = wikipediaapi.Wikipedia(
            user_agent="MyApp/2.0 (contact@example.com)", language="en"
        )

    def import_new_translation_model(self, model: str, from_hub: bool) -> bool:
        if not from_hub:
            model_filepath = Path(model)
            if not model_filepath.exists():
                return False

            if model in self.custom_translation_models:
                return True

            update_json("custom", "translation", model_filepath)
            self.custom_translation_models.append(str(model_filepath))

            return True

        if not model_exists(model):
            return False

        if model in self.hf_translation_models:
            return True

        update_json("huggingface", "translation", model)
        self.hf_comparison_models.append(model)

        return True

    def import_new_comparison_model(self, model: str, from_hub: bool) -> bool:
        if not from_hub:
            model_filepath = Path(model)
            if not model_filepath.exists():
                return False

            if model in self.custom_comparison_models:
                return True

            update_json("custom", "comparison", model_filepath)
            self.custom_comparison_models.append(str(model_filepath))

            return True

        if not model_exists(model):
            return False

        if model in self.hf_comparison_models:
            return True

        update_json("huggingface", "comparison", model)
        self.hf_comparison_models.append(model)

        return True

    def select_comparison_model(self, model_name: str) -> bool:
        if model_name in self.hf_comparison_models:
            self.selected_comparison_model = model_name
            update_json_last_selected("comparison", model_name)
            return True

        start_ptr = 0
        end_ptr = len(self.custom_comparison_models) - 1

        while start_ptr <= end_ptr:
            filename = self.custom_comparison_models[start_ptr].split("/")
            if filename == model_name:
                self.selected_comparison_model = self.custom_comparison_models[
                    start_ptr
                ]
                update_json_last_selected("comparison", model_name)
                return True
            start_ptr += 1

            filename = self.custom_comparison_models[end_ptr].split("/")
            if filename == model_name:
                self.selected_comparison_model = self.custom_comparison_models[end_ptr]
                update_json_last_selected("comparison", model_name)
                return True
            end_ptr -= 1
        return False

    def select_translation_model(self, model_name: str) -> bool:
        if model_name in self.hf_translation_models:
            self.selected_translation_model = model_name
            update_json_last_selected("translation", model_name)
            return True

        start_ptr = 0
        end_ptr = len(self.custom_translation_models) - 1

        while start_ptr <= end_ptr:
            filename = self.custom_translation_models[start_ptr].split("/")
            if filename == model_name:
                self.selected_translation_model = self.custom_translation_models[
                    start_ptr
                ]
                update_json_last_selected("translation", model_name)
                return True
            start_ptr += 1

            filename = self.custom_translation_models[end_ptr].split("/")
            if filename == model_name:
                self.selected_translation_model = self.custom_translation_models[
                    end_ptr
                ]
                update_json_last_selected("translation", model_name)
                return True
            end_ptr -= 1
        return False

    def delete_translation_model(self, model: str) -> bool:
        if model in self.hf_translation_models:
            remove_from_json("huggingface", "translation", model)
            self.hf_translation_models.remove(model)
            return True

        start_ptr = 0
        end_ptr = len(self.custom_translation_models) - 1
        found = None

        while start_ptr <= end_ptr:
            filename = self.custom_translation_models[start_ptr].split("/")
            if filename == model:
                found = self.custom_translation_models[start_ptr]
                break
            start_ptr += 1

            filename = self.custom_translation_models[end_ptr].split("/")
            if filename == model:
                found = self.custom_translation_models[end_ptr]
                break
            end_ptr -= 1

        if not found:
            return False

        remove_from_json("custom", "translation", found)
        self.custom_translation_models.remove(found)

        return True

    def delete_comparison_model(self, model: str) -> bool:
        if model in self.hf_comparison_models:
            remove_from_json("huggingface", "comparison", model)
            self.hf_comparison_models.remove(model)
            return True

        start_ptr = 0
        end_ptr = len(self.custom_comparison_models) - 1
        found = None

        while start_ptr <= end_ptr:
            filename = self.custom_comparison_models[start_ptr].split("/")
            if filename == model:
                found = self.custom_comparison_models[start_ptr]
                break
            start_ptr += 1

            filename = self.custom_comparison_models[end_ptr].split("/")
            if filename == model:
                found = self.custom_comparison_models[end_ptr]
                break
            end_ptr -= 1

        if not found:
            return False

        remove_from_json("custom", "comparison", found)
        self.custom_comparison_models.remove(found)

        return True

    def available_comparison_models_list(self) -> List[str]:
        return list(self.hf_comparison_models + self.custom_comparison_models)

    def available_translation_models_list(self) -> List[str]:
        return list(self.hf_translation_models + self.custom_translation_models)

    def extract_title_from_url(self, url: str) -> str:
        match = re.search(r"/wiki/([^#?]*)", url)
        if match:
            return match.group(1).replace("_", " ")
        return None

    def perform_semantic_comparison(
        self,
        original_blob,
        translated_blob,
        source_language,
        target_language,
        sim_threshold,
    ):
        return semantic_compare(
            original_blob,
            translated_blob,
            source_language,
            target_language,
            sim_threshold,
            self.selected_comparison_model,
        )

    def text_translate(self, source_text: str, target_language: str, source_language: str = "en") -> str:
        return translate(source_text, source_language, target_language)
