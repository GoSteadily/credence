from typing import Dict

from credence.adapter import Adapter

active_adapter: Adapter | None = None
cache: Dict[str, str] = {}


def set_adapter(adapter: Adapter | None):
    global active_adapter
    active_adapter = adapter


def clear_adapter():
    global active_adapter
    active_adapter = None


def clear():
    global cache
    cache = {}


def get_value(key: str):
    try:
        global cache
        return cache[key]
    except KeyError as e:
        raise Exception(f"Could not find {key} in metadata. Available keys are: {list(cache.keys())}") from e


def set_value(key: str, value: str):
    global cache
    cache[key] = value
