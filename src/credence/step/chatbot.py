import re
from dataclasses import dataclass
from typing import List

from credence.step import Step


class ChatbotCheck:
    pass


@dataclass
class ChatbotMetadataContains(ChatbotCheck):
    key: str
    string: str


@dataclass
class ChatbotMetadataEquals(ChatbotCheck):
    key: str
    string: str


@dataclass
class ChatbotMetadataRegexMatch(ChatbotCheck):
    key: str
    pattern: re.Pattern


@dataclass
class ChatbotResponseAICheck(ChatbotCheck):
    prompt: str
    # Increase the number of retries for brittle tests
    retries: int = 0


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


@dataclass
class ChatbotIgnoresMessage(Step):
    pass


class Chatbot(Step):
    @staticmethod
    def expect(expectations: List[ChatbotCheck]):
        return ChatbotExpectations(expectations=expectations)

    @staticmethod
    def ignores_mesage():
        return ChatbotIgnoresMessage()


@dataclass
class Metadata(Step):
    field: str

    def contains(self, value: str):
        if not isinstance(value, str):
            try:
                string = str(value)
            except Exception as e:
                raise Exception('`Metadata("...").contains` could not convert value into str') from e

        else:
            string = value
        return ChatbotMetadataContains(key=self.field, string=string)

    def equals(self, value: str):
        if not isinstance(value, str):
            try:
                string = str(value)
            except Exception as e:
                raise Exception('`Metadata("...").equals` could not convert value into str') from e

        else:
            string = value
        return ChatbotMetadataEquals(key=self.field, string=string)

    def re_match(self, regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotMetadataRegexMatch(key=self.field, pattern=pattern)
        except Exception as e:
            raise Exception(f"Invalid regex: `{regexp}`") from e


class Response(Step):
    @staticmethod
    def ai_check(should: str, retries: int = 0):
        return ChatbotResponseAICheck(prompt=should, retries=retries)

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
