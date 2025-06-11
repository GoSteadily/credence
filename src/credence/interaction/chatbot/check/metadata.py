import copy
import enum
import re
from dataclasses import dataclass
from typing import Any, List

from credence.interaction.chatbot.check.base import BaseCheckResult, BaseCheckResultStatus
from credence.interaction.chatbot.check.response import ChatbotResponseCheck


@dataclass
class Metadata:
    """
    Checks the value of Metadata set by the chatbot.

    ### Usage
    ```python
    # somewhere inside your chatbot
    credence.collect_metadata({"premium_user_flow": True})

    # In your tests
    Conversation(
        title: "Paid users have access to premium flow",
        interactions: [
            FunctionCall("register_and_upgrade", {"user": "John"}),
            User.message("Hi"),
            Chatbot.responds([
                Metadata("premium_user_flow").equals("True")
            ])
        ],
    )
    ```
    """

    field: str
    """The name of the metadata field to check"""

    def contains(self, string: str):
        if not isinstance(string, str):
            raise Exception('`Metadata("...").contains` expects a str')

        return ChatbotResponseMetadataCheck(
            key=self.field,
            value=string,
            operation=Operation.Contains,
        )

    def equals(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").equals` expects a string or value with a `__str__` implementation.') from e
                except Exception as e2:
                    return e2

        return ChatbotResponseMetadataCheck(
            key=self.field,
            value=string,
            operation=Operation.Equals,
        )

    def not_equals(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").not_equals` could not convert value into str') from e
                except Exception as e2:
                    return e2

        return ChatbotResponseMetadataCheck(
            key=self.field,
            value=string,
            operation=Operation.NotEquals,
        )

    def one_of(self, strings: list):
        values = strings
        for value in values:
            if not isinstance(value, str):
                try:
                    str(value)
                except Exception as e:
                    try:
                        raise Exception(f'`Metadata("...").one_of` could not convert `{value}` into str') from e
                    except Exception as e2:
                        return e2

            # else:
            #     str_values.append(value)
        return ChatbotResponseMetadataCheck(
            key=self.field,
            value=values,
            operation=Operation.OneOf,
        )

    def re_match(self, regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotResponseMetadataCheck(
                key=self.field,
                value=pattern,
                operation=Operation.RegexMatch,
            )
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
    OneOf = "one_of"

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
            case Operation.OneOf:
                return "should be one of"

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
            case Operation.OneOf:
                return "is not one of"


@dataclass(kw_only=True)
class ChatbotResponseMetadataCheck(ChatbotResponseCheck):
    """
    @private
    """

    key: str
    value: str | re.Pattern | List[str]
    operation: Operation
    type: str = "metadata_check"

    def __str__(self):
        if isinstance(self.value, re.Pattern):
            return f"Metadata({str_repr(self.key)}).{self.operation.value}({str_repr(self.value.pattern)})"
        else:
            return f"Metadata({str_repr(self.key)}).{self.operation.value}({str_repr(self.value)})"

    def humanize(self):
        if isinstance(self.value, re.Pattern):
            return f'metadata["{self.key}"] {self.operation.should()} `{self.value.pattern}`'
        else:
            return f'metadata["{self.key}"] {self.operation.should()} `{self.value}`'

    def to_check_result(self, value, skipped=False):
        if skipped:
            return self.skipped()

        match self.operation:
            case Operation.Equals:
                if self.value != value:
                    return self.failed_check()
            case Operation.NotEquals:
                if self.value == value:
                    return self.failed_check()
            case Operation.Contains:
                if self.value not in value:
                    return self.failed_check()
            case Operation.NotContains:
                if self.value in value:
                    return self.failed_check()
            case Operation.RegexMatch:
                if isinstance(self.value, re.Pattern) and re.search(self.value, value) is None:
                    return self.failed_check()
            case Operation.OneOf:
                possible_values = self.value
                if not isinstance(possible_values, list):
                    return self.failed_check()

                str_values = [str(v) for v in possible_values]
                try:
                    str_value = str(value)
                    if value not in possible_values and str_value not in str_values:
                        return self.failed_check()
                except Exception:
                    if value not in possible_values:
                        return self.failed_check()
        return self.passed()

    def passed(self):
        return ChatbotResponseMetadataCheckResult(
            status=BaseCheckResultStatus.Passed,
            data=copy.deepcopy(self),
        )

    def failed_missing_key(self):
        return ChatbotResponseMetadataCheckResult(
            status=BaseCheckResultStatus.Failed,
            data=copy.deepcopy(self),
            missing_key=True,
        )

    def failed_check(self):
        return ChatbotResponseMetadataCheckResult(
            status=BaseCheckResultStatus.Failed,
            data=copy.deepcopy(self),
        )

    def skipped(self):
        return ChatbotResponseMetadataCheckResult(
            status=BaseCheckResultStatus.Skipped,
            data=copy.deepcopy(self),
        )


@dataclass(kw_only=True)
class ChatbotResponseMetadataCheckResult(BaseCheckResult):
    data: ChatbotResponseMetadataCheck
    status: BaseCheckResultStatus
    missing_key: bool = False
    type: str = "metadata_check"

    def generate_error_messages(self):
        if self.missing_key:
            return [f"Metadata key is missing:\n'{self.data.key}'"]

        if self.status == BaseCheckResultStatus.Failed:
            return [f"Metadata value for {self.data.key} did not meet requirement:\n{self.data.humanize()}"]

        return []


def str_repr(string: str|List[str]):
    """
    @private
    """
    return f"{string.__repr__()}"
