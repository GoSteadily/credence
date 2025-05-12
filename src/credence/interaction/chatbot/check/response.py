import re
from dataclasses import dataclass

from credence.interaction.chatbot.check.ai_content_check import AIContentCheck
from credence.interaction.chatbot.check.base import BaseCheck
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
    def equals(string: str):
        return ChatbotResponseEquals(string=string)

    def not_equals(string: str):
        return ChatbotResponseNotEquals(string=string)

    @staticmethod
    def re_match(regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotResponseRegexMatch(pattern=pattern)
        except Exception as e:
            try:
                raise Exception(f"Invalid regex: `{regexp}`") from e
            except Exception as e2:
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

    def find_error(self, messages, adapter):
        from credence.adapter import Adapter

        if not isinstance(adapter, Adapter):
            raise Exception(f"{adapter} is not a valid Adapter")

        result = AIContentCheck.check_requirement(
            client=adapter.get_client(),
            model_name=adapter.model_name(),
            messages=messages,
            requirement=self.prompt,
        )

        last_assistant_message = "None"
        for role, message in reversed(messages):
            if role == Role.Chatbot:
                last_assistant_message = message
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

    def find_error(self, value):
        if self.string not in value:
            return Exception(f"`Expected chatbot response to contain `{str_repr(self.string)}`, but found `{str_repr(value)}`")


@dataclass
class ChatbotResponseEquals(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f"Response.equals({str_repr(self.string)})"

    def find_error(self, value):
        if self.string != value:
            return Exception(f"Expected chatbot response to equal `{str_repr(self.string)}`, but found `{str_repr(value)}`")


@dataclass
class ChatbotResponseNotEquals(ChatbotResponseCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Response.not_equals("{str_repr(self.string)}")'

    def find_error(self, value):
        if self.string == value:
            return Exception(f"Expected chatbot response to not equal `{self.string}`, but found `{str_repr(value)}`")


@dataclass
class ChatbotResponseRegexMatch(ChatbotResponseCheck):
    """
    @private
    """

    pattern: re.Pattern

    def __str__(self):
        return f'Response.re_match("{self.pattern.pattern}")'

    def find_error(self, value):
        if re.search(self.pattern, value) is None:
            return Exception(f"Expected chatbot response to match the regex {self.pattern.pattern}, but found `{value}`")


def str_repr(string: str):
    """
    @private
    """
    return f"{string.__repr__()}"
