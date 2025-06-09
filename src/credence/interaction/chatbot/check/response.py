import copy
import enum
import re
from dataclasses import dataclass

from credence.interaction.chatbot.check.base import BaseCheck, BaseCheckResult, BaseCheckResultStatus


@dataclass
class ChatbotResponseCheck(BaseCheck):
    """
    @private
    """

    pass


class Response:
    @staticmethod
    def ai_check(should: str, retries: int = 0):
        from credence.interaction.chatbot.check.ai import ChatbotResponseAICheck

        return ChatbotResponseAICheck(prompt=should, retries=retries)

    @staticmethod
    def contains(string: str):
        return ChatbotResponseMessageCheck(value=string, operation=Operation.Contains)

    @staticmethod
    def not_contains(string: str):
        return ChatbotResponseMessageCheck(value=string, operation=Operation.NotContains)

    @staticmethod
    def equals(string: str):
        return ChatbotResponseMessageCheck(value=string, operation=Operation.Equals)

    @staticmethod
    def not_equals(string: str):
        return ChatbotResponseMessageCheck(value=string, operation=Operation.NotEquals)

    @staticmethod
    def re_match(regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotResponseMessageCheck(value=pattern, operation=Operation.RegexMatch)
        except Exception as e:
            try:
                raise Exception(f"Invalid regex: `{regexp}`") from e
            except Exception as e2:
                return e2


class Operation(str, enum.Enum):
    Equals = "equals"
    NotEquals = "not_equals"
    Contains = "contains"
    NotContains = "not_contains"
    RegexMatch = "regex_match"

    def should(self):
        match self:
            case Operation.Equals:
                return "should equal"
            case Operation.NotEquals:
                return "should not equal"
            case Operation.Contains:
                return "should contain"
            case Operation.NotContains:
                return "should not contain"
            case Operation.RegexMatch:
                return "should match the regex"

    def did_not(self):
        match self:
            case Operation.Equals:
                return "did not equal"
            case Operation.NotEquals:
                return "unexpectedly equals"
            case Operation.Contains:
                return "did not contain"
            case Operation.NotContains:
                return "unexpectedly contains"
            case Operation.RegexMatch:
                return "did not match the regex"


@dataclass
class ChatbotResponseMessageCheck(ChatbotResponseCheck):
    """
    @private
    """

    value: str
    operation: Operation

    def __str__(self):
        if self.operation == Operation.RegexMatch:
            return f"Response.re_match({str_repr(self.value.pattern)})"
        return f"Response.{self.operation.value}({str_repr(self.value)})"

    def humanize(self):
        if self.operation == Operation.RegexMatch:
            return f"{self.operation.should()} `{self.value.pattern}`"
        return f"{self.operation.should()} `{self.value}`"

    def to_check_result(self, value: str, skipped: bool = False):
        if skipped:
            return self.skipped()

        match self.operation:
            case Operation.Equals:
                if self.value != value:
                    return self.failed()
            case Operation.NotEquals:
                if self.value == value:
                    return self.failed()
            case Operation.Contains:
                if self.value not in value:
                    return self.failed()
            case Operation.NotContains:
                if self.value in value:
                    return self.failed()
            case Operation.RegexMatch:
                if re.search(self.value, value) is None:
                    return self.failed()
        return self.passed()

    def passed(self):
        return ChatbotResponseMessageCheckResult(
            status=BaseCheckResultStatus.Passed,
            data=copy.deepcopy(self),
        )

    def failed(self):
        return ChatbotResponseMessageCheckResult(
            status=BaseCheckResultStatus.Failed,
            data=copy.deepcopy(self),
        )

    def skipped(self):
        return ChatbotResponseMessageCheckResult(
            status=BaseCheckResultStatus.Skipped,
            data=copy.deepcopy(self),
        )


@dataclass(kw_only=True)
class ChatbotResponseMessageCheckResult(BaseCheckResult):
    data: ChatbotResponseMessageCheck
    status: BaseCheckResultStatus

    def generate_error_messages(self):
        if self.status == BaseCheckResultStatus.Failed:
            return [f"Chatbot response did not meet requirement:\n{self.data.humanize()}"]

        return []


def str_repr(string: str):
    """
    @private
    """
    return f"{string.__repr__()}"
