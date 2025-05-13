from dataclasses import dataclass
from typing import List, Tuple

from credence.interaction import Interaction
from credence.interaction.chatbot.check import BaseCheck
from credence.interaction.chatbot.check.metadata import ChatbotMetadataCheck
from credence.interaction.chatbot.check.response import ChatbotResponseAICheck, ChatbotResponseCheck
from credence.role import Role


class Chatbot(Interaction):
    @staticmethod
    def responds(expectations: List[BaseCheck]) -> Interaction:
        return ChatbotResponds(expectations=expectations)

    @staticmethod
    def ignores_mesage() -> Interaction:
        return ChatbotIgnoresMessage()


@dataclass
class ChatbotResponds(Interaction):
    """@private"""

    expectations: List[BaseCheck]

    def __str__(self):
        """@private"""
        expectations_str = ""
        for expectation in self.expectations:
            expectations_str += "\n"
            for line in str(expectation).splitlines(keepends=True):
                expectations_str += f"    {line}"
            expectations_str += ","

        closing_str = "]\n"
        if len(self.expectations) > 0:
            closing_str = "\n]"

        return f"""
Chatbot.responds([{expectations_str}{closing_str})
""".strip()

    def _check(
        self,
        adapter,
        messages: List[Tuple[Role, str]],
        chatbot_response: str,
    ):
        from credence import metadata

        for expectation in self.expectations:
            if isinstance(expectation, ChatbotResponseAICheck):
                expectation.check(value=messages, adapter=adapter)

            elif isinstance(expectation, ChatbotResponseCheck):
                expectation.check(value=chatbot_response)

            elif isinstance(expectation, ChatbotMetadataCheck):
                value = metadata.get_value(expectation.key)
                expectation.check(value)

        metadata.clear()


@dataclass
class ChatbotIgnoresMessage(Interaction):
    """@private"""

    def __str__(self):
        return "Chatbot.ignores_mesage()"
