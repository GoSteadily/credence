import abc
import enum
from dataclasses import dataclass


@dataclass(kw_only=True)
class BaseCheck(abc.ABC):
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

    # @abc.abstractmethod
    # def find_error(self, value, **kwargs):
    #     """ """

    @abc.abstractmethod
    def humanize(self) -> str:
        "Generate a sentence that describes the check"

    @abc.abstractmethod
    def to_check_result(self, **kwargs) -> "BaseCheckResult":
        ""


class BaseCheckResultStatus(str, enum.Enum):
    """@private"""

    Passed = "passed"
    Failed = "failed"
    Skipped = "skipped"


@dataclass(kw_only=True)
class BaseCheckResult:
    """"""

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__annotations__.get("data", None) is None:
            raise Exception(f"data is required for all subclasses of InteractionResult {cls} {vars(cls)}")

        if cls.__annotations__.get("status", None) is None:
            raise Exception("status is required for all subclasses of InteractionResult")

    @abc.abstractmethod
    def generate_error_messages(self):
        pass
