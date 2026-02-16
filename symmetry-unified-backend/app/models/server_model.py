from dataclasses import dataclass, field
from typing import List, Optional
import wikipediaapi
import re
import json
from pathlib import Path
from ..ai.semantic_comparison import semantic_compare
from ..ai.translation import translate_text
from huggingface_hub import model_info

def model_exists(model_name: str) -> bool:
    try:
        model_info(model_name)
        return True
    except Exception as e:
        print(e)
        print("You may need to put 'sentence-transformers/' as a prefix before the model name.")
        return False

def load_saved_models(domain: str, model_type: str):
    current_dir = Path(__file__).parent
    filepath = current_dir / "saved_models.json"
    with open(filepath, 'r') as file:
        data = json.load(file)
        return list[str](data[domain][model_type])

def update_json(domain: str, model_type: str, new_model_filepath):
    current_dir = Path(__file__).parent
    filepath = current_dir / "saved_models.json"
    with open(filepath, 'r') as f:
        data = json.load(f)
    data[domain][model_type].append(str(new_model_filepath))
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def update_json_last_selected(domain: str, new_selection):
    current_dir = Path(__file__).parent
    filepath = current_dir / "saved_models.json"
    with open(filepath, 'r') as f:
        data = json.load(f)
    if domain == "comparison":
        data["comp_last_selected"] = new_selection
    else:
        data["trans_last_selected"] = new_selection
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def remove_from_json(domain: str, model_type: str, modelname):
    current_dir = Path(__file__).parent
    filepath = current_dir / "saved_models.json"
    with open(filepath, 'r') as f:
        data = json.load(f)
    data[domain][model_type].remove(str(modelname))
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_last_selected(for_: str):
    current_dir = Path(__file__).parent
    filepath = current_dir / "saved_models.json"
    with open(filepath, 'r') as f:
        data = json.load(f)

    if for_ == "comparison":
        return data['comp_last_selected']
    else:
        return data['trans_last_selected']

@dataclass
class ServerModel:
    hf_comparison_models: List[str] = field(default_factory=lambda: load_saved_models("huggingface", "comparison")) 
    hf_translation_models: List[str] = field(default_factory=lambda: load_saved_models("huggingface", "translation"))

    custom_comparison_models: List[str] = field(default_factory=lambda: load_saved_models("custom", "comparison"))
    custom_translation_models: List[str] = field(default_factory=lambda: load_saved_models("custom", "translation"))

    selected_comparison_model: str = field(default_factory=lambda: load_last_selected("comparison"))
    selected_translation_model: str = field(default_factory=lambda: load_last_selected("translation"))

    wikipedia: Optional[wikipediaapi.Wikipedia] = field(default=None)

    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        self.wikipedia = wikipediaapi.Wikipedia(user_agent='MyApp/2.0 (contact@example.com)', language='en')



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

        # write model name to comparison models in json
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
                self.selected_comparison_model = self.custom_comparison_models[start_ptr]
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
                self.selected_translation_model = self.custom_translation_models[start_ptr]
                update_json_last_selected("translation", model_name)
                return True
            start_ptr += 1

            filename = self.custom_translation_models[end_ptr].split("/")
            if filename == model_name:
                self.selected_translation_model = self.custom_translation_models[end_ptr]
                update_json_last_selected("translation", model_name)
                return True
            end_ptr -= 1
        return False

    def delete_translation_model(self, model:str) -> bool:
        if model in self.hf_translation_models:
            # remove from json
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

    def delete_comparison_model(self, model:str) -> bool:
        if model in self.hf_comparison_models:
            # remove from json
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
        match = re.search(r'/wiki/([^#?]*)', url)
        if match:
            return match.group(1).replace('_', ' ')
        return None

    def perform_semantic_comparison(        
        self,
        original_blob,
        translated_blob,
        source_language,
        target_language,
        sim_threshold):

        return semantic_compare(
            original_blob, 
            translated_blob, 
            source_language, 
            target_language, 
            sim_threshold, 
            self.selected_comparison_model
        )

    def text_translate(self, target_text: str, target_language: str):
        return translate_text(target_text, target_language)