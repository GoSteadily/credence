import abc
import enum
import uuid
from dataclasses import dataclass, field
from typing import List


@dataclass(kw_only=True)
class Interaction(abc.ABC):
    """"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """A unique id used to identify a conversation."""

    @abc.abstractmethod
    def is_user_interaction(self) -> bool:
        "@private"

    @abc.abstractmethod
    def is_chatbot_interaction(self) -> bool:
        "@private"

    @abc.abstractmethod
    def to_result(self, **kwargs) -> "InteractionResult":
        "@private"


class InteractionResultStatus(str, enum.Enum):
    """@private"""

    Passed = "passed"
    Failed = "failed"
    Skipped = "skipped"


@dataclass(kw_only=True)
class InteractionResult(abc.ABC):
    """"""

    status: InteractionResultStatus

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__annotations__.get("type", None) is None:
            raise Exception(f"type is required for all subclasses of InteractionResult {cls} {vars(cls)}")

        if cls.__annotations__.get("data", None) is None:
            raise Exception(f"data is required for all subclasses of InteractionResult {cls} {vars(cls)}")

    @abc.abstractmethod
    def generate_error_messages(self) -> List[str]:
        pass
