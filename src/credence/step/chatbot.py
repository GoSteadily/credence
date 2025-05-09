from dataclasses import dataclass
from typing import List

from credence.step import Step
from credence.step.checks.chatbot_check import ChatbotCheck


class Chatbot(Step):
    @staticmethod
    def expect(expectations: List[ChatbotCheck]) -> Step:
        return ChatbotExpectations(expectations=expectations)

    @staticmethod
    def ignores_mesage() -> Step:
        return ChatbotIgnoresMessage()


@dataclass
class ChatbotExpectations(Step):
    expectations: List[ChatbotCheck]

    def __str__(self):
        expectations_str = ""
        for expectation in self.expectations:
            expectations_str += f"\n"
            for line in str(expectation).splitlines(keepends=True):
                expectations_str += f"    {line}"
            expectations_str += f","

        closing_str = "]\n"
        if len(self.expectations) > 0:
            closing_str = "\n]"

        return f"""
Chatbot.expect([{expectations_str}{closing_str})
""".strip()


@dataclass
class ChatbotIgnoresMessage(Step):
    def __str__(self):
        return "Chatbot.ignores_mesage()"
