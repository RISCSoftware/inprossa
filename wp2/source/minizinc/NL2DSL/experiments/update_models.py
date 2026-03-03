import json
import os

from model_reuser import ModelReuser


def update_models(directories: list[str]):
    for directory in directories:
        files = [
            os.path.join(root, file)
            for root, dirs, files in os.walk(directory)
            for file in files
            if file.endswith(".json")
        ]
        for filepath in files:
            with open(filepath, "r", encoding="utf-8") as f:
                models = json.load(f)
            for i, model in enumerate(models):
                models[i] = ModelReuser._execute_and_validate_model(model)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(models, f, indent=4)

if __name__ == "__main__":
    update_models(["testset_paper_2D-BPP_CLASS_update_models_test"])
