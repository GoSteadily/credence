from dataclasses import dataclass
from typing import List

from credence.interaction import InteractionResult
from credence.message import Message


@dataclass
class Result:
    conversation_id: str | None
    version_id: str | None
    title: str
    messages: List[Message]
    failed: bool
    interaction_results: List[InteractionResult]
    chatbot_time_ms: int
    testing_time_ms: int

    def to_stdout(self):
        from credence.result.text import TextRenderer

        return TextRenderer.to_stdout(self)

    def to_markdown(self, index=None):
        from credence.result.markdown import MarkdownRenderer

        return MarkdownRenderer.to_markdown(self, index)

    def to_json(self, index=None):
        from credence.result.json import JsonRenderer

        return JsonRenderer.to_json(self, index or 0)
