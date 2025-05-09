import abc
import re
from dataclasses import dataclass
from typing import Any


class ChatbotCheck(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        """
        Each check should define a `_str_` method that
        returns the code used to generate the check.

        Example:

        If `Response.equals("ABC")` produces the internal
        type `ChatbotResponseEquals("ABC")`, the __str__
        method should return 'Response.equals("ABC")'.
        """

    @abc.abstractmethod
    def find_error(self, value, **kwargs):
        """ """

    def check(self, value, **kwargs):
        exception = self.find_error(value, **kwargs)
        if exception:
            raise exception


@dataclass
class ChatbotResponseCheck(ChatbotCheck):
    pass


@dataclass
class ChatbotMetadataCheck(ChatbotCheck):
    key: str


@dataclass
class Metadata:
    field: str

    def contains(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").contains` could not convert value into str') from e
                except Exception as e2:
                    return e2

        return ChatbotMetadataContains(key=self.field, string=string)

    def equals(self, string: Any):
        if not isinstance(string, str):
            try:
                string = str(string)
            except Exception as e:
                try:
                    raise Exception('`Metadata("...").equals` could not convert value into str') from e
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
    string: str

    def __str__(self):
        return f'Metadata("{self.key}").equals("{self.string}")'

    def find_error(self, value):
        if str(value) != self.string:
            return Exception(f"Expected metadata[`{self.key}`] to equal `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataNotEquals(ChatbotMetadataCheck):
    string: str

    def __str__(self):
        return f'Metadata("{self.key}").not_equals("{self.string}")'

    def find_error(self, value):
        if str(value) == self.string:
            return Exception(f"Expected metadata[`{self.key}`] to not equal `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataContains(ChatbotMetadataCheck):
    string: str

    def __str__(self):
        return f'Metadata("{self.key}").contains("{self.string}")'

    def find_error(self, value):
        if self.string not in str(value):
            return Exception(f"Expected metadata[`{self.key}`] to contain `{self.string}`, but found: `{value}`")


@dataclass
class ChatbotMetadataRegexMatch(ChatbotMetadataCheck):
    pattern: re.Pattern

    def __str__(self):
        return f'Metadata("{self.key}").re_match("{self.pattern.pattern}")'

    def find_error(self, value):
        if re.search(self.pattern, str(value)) is None:
            return Exception(f"Expected metadata[`{self.key}`] to match the regex `{self.pattern.pattern}`, found: `{value}`")


@dataclass
class ChatbotMetadataOneOf(ChatbotMetadataCheck):
    values: list
    str_values: list

    def __str__(self):
        return f'Metadata("{self.key}").one_of({self.values})'

    def find_error(self, value):
        if str(value) not in self.str_values:
            return Exception(f"Expected metadata[`{self.key}`] to contain one of {self.values}, found: `{value}`")
