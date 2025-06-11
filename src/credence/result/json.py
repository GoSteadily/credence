import dataclasses
import enum
import json
import re
from typing import Any, Dict, List

from credence.interaction import InteractionResult, InteractionResultStatus
from credence.interaction.chatbot import ChatbotRespondsResult
from credence.interaction.chatbot.check.base import BaseCheckResult
from credence.message import Message
from credence.result import Result


class JsonRenderer:
    @staticmethod
    def to_json(result: Result, index: int):
        # ------------------------------------------------------------------ #
        # Build the top-level structure
        # ------------------------------------------------------------------ #
        payload: Dict[str, Any] = {
            "conversation_id": result.conversation_id,
            "version_id": result.version_id,
            "index": index - 1,
            "title": result.title,
            "failed": result.failed,
            "chatbot_time_ms": result.chatbot_time_ms,
            "testing_time_ms": result.testing_time_ms,
            "total_time_ms": result.chatbot_time_ms + result.testing_time_ms,
            "interactions": _serialise(result.interaction_results),
        }

        if result.failed:
            errors: List[str] = []
            for interaction in result.interaction_results:
                if interaction.status == InteractionResultStatus.Failed:
                    errors.extend(interaction.generate_error_messages())

            payload["errors"] = errors
        else:
            payload["errors"] = []

        return json.dumps(payload, indent=2, ensure_ascii=False)


def _serialise(obj: Any, serialize_index: int | None = None):
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, re.Pattern):
        return obj.pattern

    # enums → their value
    if isinstance(obj, enum.Enum):
        return obj.value

    # InteractionResult (is a dataclass, but may hold nested Results)
    if isinstance(obj, InteractionResult) or isinstance(obj, BaseCheckResult):
        if isinstance(obj, ChatbotRespondsResult):
            values = {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}
            values["checks"] = _serialise(obj.checks)
            values["interaction_id"] = obj.data.id

        elif isinstance(obj, InteractionResult):
            values = {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}
            values["interaction_id"] = obj.data.id

        elif isinstance(obj, BaseCheckResult):
            values = {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}
            values["check_id"] = obj.data.id

        del values["data"]

        return {
            obj.type: values,
            "index": serialize_index,
        }

    # dataclasses → asdict + recurse
    if dataclasses.is_dataclass(obj):
        return {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}

    if isinstance(obj, Message):
        d: Dict[str, Any] = {
            "role": _serialise(obj.role),
            "body": obj.body,
            "index": obj.index,
        }
        if obj.metadata:
            d["metadata"] = _serialise(obj.metadata)
        return d

    # containers
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_serialise(v, index) for index, v in enumerate(obj)]

    # fall-back
    return str(obj)
