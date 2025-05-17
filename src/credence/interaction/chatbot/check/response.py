import re
from dataclasses import dataclass
from typing import List, Tuple

from credence.exceptions import ChatbotIndexedException
from credence.interaction.chatbot.check.ai_content_check import AIContentCheck
from credence.interaction.chatbot.check.base import BaseCheck
from credence.message import Message
from credence.role import Role


@dataclass
class ChatbotResponseCheck(BaseCheck):
    """
    @private
    """

    pass


class Response:
    @staticmethod
    def ai_check(should: str, retries: int = 0):
        return ChatbotResponseAICheck(prompt=should, retries=retries)

    @staticmethod
    def contains(string: str):
        return ChatbotResponseContains(string=string)

    @staticmethod
    def not_contains(string: str):
        return ChatbotResponseNotContain(string=string)

    @staticmethod
    def equals(string: str):
        return ChatbotResponseEquals(string=string)

    @staticmethod
    def not_equals(string: str):
        return ChatbotResponseNotEquals(string=string)

    @staticmethod
    def re_match(regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotResponseRegexMatch(pattern=pattern)
        except Exception as e:
            try:
                print(e)
                raise Exception(f"Invalid regex: `{regexp}`") from e
            except Exception as e2:
                print(e2)
                return e2


@dataclass
class ChatbotResponseAICheck(BaseCheck):
    """
    @private
    """

    prompt: str
    # Increase the number of retries for brittle tests
    retries: int = 0

    def __str__(self):
        if self.retries > 0:
            return f"""Response.ai_check(
    should={str_repr(self.prompt)},
    retries={self.retries},
)""".strip()
        else:
            return f"Response.ai_check(should={str_repr(self.prompt)})"

    def humanize(self):
        return f"should {self.prompt}"

    def find_error(self, messages: List[Message], adapter):
        from credence.adapter import Adapter

        if not isinstance(adapter, Adapter):
            raise Exception(f"{adapter} is not a valid Adapter")

        result = AIContentCheck.check_requirement(
            client=adapter.get_client(),
            model_name=adapter.model_name(),
            messages=messages,
            requirement=self.prompt,
        )

        last_assistant_message = (0, "None")
        for message in reversed(messages):
            if message.role == Role.Chatbot:
                last_assistant_message = (message.index, message.body)
                break

        return result.generate_error(chatbot_response=last_assistant_message)


@dataclass
class ChatbotResponseContains(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f"Response.contains({str_repr(self.string)})"

    def humanize(self):
        return f"response should contain '{self.string}'"

    def find_error(self, value: Tuple[int, str]):
        if self.string not in value[1]:
            return ChatbotIndexedException(value[0], f"Expected chatbot response to contain `{str_repr(self.string)}`, but found `{str_repr(value[1])}`")


@dataclass
class ChatbotResponseNotContain(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Response.not_contain("{str_repr(self.string)}")'

    def humanize(self):
        return f"response should not contain '{self.string}'"

    def find_error(self, value: Tuple[int, str]):
        if self.string in value[1]:
            return ChatbotIndexedException(value[0], f"Expected chatbot response to not contain `{str_repr(self.string)}`, but found `{str_repr(value[1])}`")


@dataclass
class ChatbotResponseEquals(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f"Response.equals({str_repr(self.string)})"

    def humanize(self):
        return f"should respond with '{self.string}'"

    def find_error(self, value: Tuple[int, str]):
        if self.string != value[1]:
            return ChatbotIndexedException(value[0], f"Expected chatbot response to equal `{str_repr(self.string)}`, but found `{str_repr(value[1])}`")


@dataclass
class ChatbotResponseNotEquals(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Response.not_equals("{str_repr(self.string)}")'

    def humanize(self):
        return f"response should not be '{self.string}'"

    def find_error(self, value: Tuple[int, str]):
        if self.string == value[1]:
            return ChatbotIndexedException(value[0], f"Expected chatbot response to not equal `{self.string}`, but found `{str_repr(value[1])}`")


@dataclass
class ChatbotResponseRegexMatch(ChatbotResponseCheck):
    """
    @private
    """

    pattern: re.Pattern

    def __str__(self):
        return f'Response.re_match("{self.pattern.pattern}")'

    def humanize(self):
        return f"should match '{self.pattern.pattern}'"

    def find_error(self, value):
        value: Tuple[int, str] = value
        if re.search(self.pattern, value[1]) is None:
            return ChatbotIndexedException(value[0], f"Expected chatbot response to match the regex {self.pattern.pattern}, but found `{value[1]}`")


def str_repr(string: str):
    """
    @private
    """
    return f"{string.__repr__()}"
