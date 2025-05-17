import abc
from dataclasses import dataclass


@dataclass(kw_only=True)
class BaseCheck(abc.ABC):
    """@private"""

    passed: bool = True
    """@private"""

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

    @abc.abstractmethod
    def humanize(self) -> str:
        "Generate a sentence that describes the check"

    def check(self, value, **kwargs):
        self.passed = True
        exception = self.find_error(value, **kwargs)
        if exception:
            self.passed = False
            return [exception]
        else:
            return []
