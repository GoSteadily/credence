import re
from dataclasses import dataclass
from typing import List

from credence.step import Step


class ChatbotCheck:
    pass


@dataclass
class ChatbotResponseAICheck(ChatbotCheck):
    prompt: str


@dataclass
class ChatbotResponseContains(ChatbotCheck):
    string: str


@dataclass
class ChatbotResponseEquals(ChatbotCheck):
    string: str


@dataclass
class ChatbotResponseRegexMatch(ChatbotCheck):
    pattern: re.Pattern


@dataclass
class ChatbotExpectations(Step):
    expectations: List[ChatbotCheck]


class Chatbot(Step):
    @staticmethod
    def expect(expectations: List[ChatbotCheck]):
        return ChatbotExpectations(expectations=expectations)

    @staticmethod
    def ai_check(should: str):
        return ChatbotResponseAICheck(prompt=should)

    @staticmethod
    def contains(string: str):
        return ChatbotResponseContains(string=string)

    @staticmethod
    def equals(string: str):
        return ChatbotResponseEquals(string=string)

    @staticmethod
    def re_match(regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotResponseRegexMatch(pattern=pattern)
        except Exception as e:
            raise Exception(f"Invalid regex: `{regexp}`") from e
