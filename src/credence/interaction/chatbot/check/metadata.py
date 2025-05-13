import re
from dataclasses import dataclass
from typing import Any

from credence.interaction.chatbot.check.base import BaseCheck


@dataclass
class ChatbotMetadataCheck(BaseCheck):
    """
    @private
    """

    key: str


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
            External("register_and_upgrade", {"user": "John"}),
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

        return ChatbotMetadataContains(key=self.field, string=string)

    def equals(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").equals` expects a string or value with a `__str__` implementation.') from e
                except Exception as e2:
                    return e2

        return ChatbotMetadataEquals(key=self.field, string=string)

    def not_equals(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").not_equals` could not convert value into str') from e
                except Exception as e2:
                    return e2

        return ChatbotMetadataNotEquals(key=self.field, string=string)

    def one_of(self, strings: list):
        values = strings
        str_values = []
        for value in values:
            if not isinstance(value, str):
                try:
                    str_values.append(str(value))
                except Exception as e:
                    try:
                        raise Exception(f'`Metadata("...").one_of` could not convert `{value}` into str') from e
                    except Exception as e2:
                        return e2

            else:
                str_values.append(value)
        return ChatbotMetadataOneOf(
            key=self.field,
            values=values,
            str_values=str_values,
        )

    def re_match(self, regexp: str):
        try:
            pattern = re.compile(regexp)
            return ChatbotMetadataRegexMatch(key=self.field, pattern=pattern)
        except Exception as e:
            try:
                raise Exception(f"Invalid regex: `{regexp}`") from e
            except Exception as e2:
                return e2


@dataclass
class ChatbotMetadataEquals(ChatbotMetadataCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Metadata("{self.key}").equals("{self.string}")'

    def humanize(self):
        return f"metadata `{self.key}` should be '{self.string}'"

    def find_error(self, value):
        if str(value) != self.string:
            return Exception(f"Expected metadata[`{self.key}`] to equal `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataNotEquals(ChatbotMetadataCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Metadata("{self.key}").not_equals("{self.string}")'

    def humanize(self):
        return f"metadata `{self.key}` should not be '{self.string}'"

    def find_error(self, value):
        if str(value) == self.string:
            return Exception(f"Expected metadata[`{self.key}`] to not equal `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataContains(ChatbotMetadataCheck):
    """
    @private
    """

    string: str

    def __str__(self):
        return f'Metadata("{self.key}").contains("{self.string}")'

    def humanize(self):
        return f"metadata `{self.key}` should contain '{self.string}'"

    def find_error(self, value):
        if self.string not in str(value):
            return Exception(f"Expected metadata[`{self.key}`] to contain `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataRegexMatch(ChatbotMetadataCheck):
    """
    @private
    """

    pattern: re.Pattern

    def __str__(self):
        return f'Metadata("{self.key}").re_match("{self.pattern.pattern}")'

    def humanize(self):
        return f"metadata `{self.key}` should match `{self.pattern.pattern}`"

    def find_error(self, value):
        if re.search(self.pattern, str(value)) is None:
            return Exception(f"Expected metadata[`{self.key}`] to match the regex `{self.pattern.pattern}`, found: `{value}`")


@dataclass
class ChatbotMetadataOneOf(ChatbotMetadataCheck):
    """
    @private
    """

    values: list
    str_values: list

    def __str__(self):
        return f'Metadata("{self.key}").one_of({self.values})'

    def humanize(self):
        return f"metadata `{self.key}` should be one of `{self.values}`"

    def find_error(self, value):
        if str(value) not in self.str_values:
            return Exception(f"Expected metadata[`{self.key}`] to contain one of {self.values}, found: `{value}`")
