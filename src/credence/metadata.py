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


def get_value(path: str):
    global cache
    return cache[path]


def set_value(path: str, value: str):
    global cache
    cache[path] = value
