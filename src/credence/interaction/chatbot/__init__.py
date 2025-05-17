from dataclasses import dataclass
from typing import List, Tuple

from credence.interaction import Interaction
from credence.interaction.chatbot.check import BaseCheck
from credence.interaction.chatbot.check.metadata import ChatbotMetadataCheck
from credence.interaction.chatbot.check.response import ChatbotResponseAICheck, ChatbotResponseCheck
from credence.role import Role


class Chatbot:
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
        messages: List[Tuple[int, Role, str]],
        chatbot_response: Tuple[int, str],
    ) -> List[Exception]:
        from credence import metadata

        exceptions = []
        for expectation in self.expectations:
            if isinstance(expectation, ChatbotResponseAICheck):
                exceptions.extend(
                    expectation.check(value=messages, adapter=adapter),
                )

            elif isinstance(expectation, ChatbotResponseCheck):
                exceptions.extend(
                    expectation.check(value=chatbot_response),
                )

            elif isinstance(expectation, ChatbotMetadataCheck):
                value = metadata.get_value(expectation.key)
                exceptions.extend(
                    expectation.check(value),
                )

        metadata.clear()
        return exceptions

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return True


@dataclass
class ChatbotIgnoresMessage(Interaction):
    """@private"""

    def __str__(self):
        return "Chatbot.ignores_mesage()"

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return False
