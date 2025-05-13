from typing import Dict

from credence.adapter import Adapter

active_adapter: Adapter | None = None
"""@private"""

metadata: Dict[str, str] = {}
"""@private"""


def set_adapter(adapter: Adapter | None):
    global active_adapter
    active_adapter = adapter


def clear_adapter():
    global active_adapter
    active_adapter = None


def clear():
    global metadata
    metadata = {}


def get_value(key: str):
    try:
        global metadata
        return metadata[key]
    except KeyError as e:
        raise Exception(f"Could not find {key} in metadata. Available keys are: {list(metadata.keys())}") from e


def set_value(key: str, value: str):
    global metadata
    metadata[key] = value
