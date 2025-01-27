from typing import Dict
import json
import random


def execute(prompt_template: str, prompt_state: Dict) -> str:
    prompt = prompt_template
    for k, v in prompt_state.items():
        prompt = prompt.replace("{{" + k + "}}", str(v))
    return prompt


def load_agent_template(template: str, json_path: str) -> tuple[str, str]:
    """
    Load agent personality from JSON and update template with random values.

    Args:
        template (str): The template string containing placeholders
        json_path (str): Path to the JSON file containing agent personality data

    Returns:
        str: Updated template with randomly selected values
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        agent_values = {
            "knowledge": random.choice(data.get("knowledge", [])),
            "agent_name": data.get("name"),
            "system": data.get("system"),
            "bio": random.choice(data.get("bio", [])),
            "lore": random.choice(data.get("lore", [])),
            "topics": random.choice(data.get("topics", [])),
        }

        updated_template = execute(template, agent_values)

        return updated_template, data.get("name")

    except FileNotFoundError:
        raise FileNotFoundError(f"Agent personality file not found: {json_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON file: {json_path}")
    except KeyError as e:
        raise KeyError(f"Missing required key in JSON file: {e}")
