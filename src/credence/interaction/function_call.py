import copy
from dataclasses import dataclass, field
from typing import Dict

from credence.adapter import Adapter
from credence.interaction import Interaction, InteractionResult, InteractionResultStatus


@dataclass(kw_only=True, init=False)
class FunctionCall(Interaction):
    """
    `FunctionCall` interactions allow you to run any function defined in an
    `Adapter` class.

    This acts as an escape hatch allowing you to model interactions that
    take place outside the normal message sending flow such as user sign-up
    or payment from your website.

    ### Usage
    >>> FunctionCall("function_with_no_args")

    >>> FunctionCall("function_with_args", {"arg_a": "1", "arg_b": "2"})
    """

    name: str
    """The name of the function on the adapter instance."""
    args: Dict[str, str] = field(default_factory=dict)
    """The keyword arguments that will be applied to the function."""
    type: str = "function_call"
    """@private"""

    def __init__(self, id, name, args={}):
        super().__init__()

        self.id = id
        self.name = name
        self.args = args

    def call(self, adapter: "Adapter"):
        return self.to_result(adapter=adapter)

    def to_result(self, adapter: "Adapter"):
        if hasattr(adapter, self.name) and callable(getattr(adapter, self.name)):
            func = getattr(adapter, self.name)
            func(**self.args)
        else:
            raise Exception(f"Function not defined: {self.name}")

    def __str__(self):
        """ """
        name = self.name.__repr__()

        if len(self.args) > 0:
            return f"FunctionCall({name}, {self.args})"

        else:
            return f"FunctionCall({name})"

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return False

    def passed(
        self,
    ) -> "FunctionCallResult":
        return FunctionCallResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Passed,
            execution_error=None,
        )

    def failed(self, execution_error: str) -> "FunctionCallResult":
        return FunctionCallResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Failed,
            execution_error=execution_error,
        )

    def skipped(self, execution_error: str | None = None) -> "FunctionCallResult":
        return FunctionCallResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Skipped,
            execution_error=None,
        )


@dataclass(kw_only=True)
class FunctionCallResult(InteractionResult):
    data: FunctionCall

    execution_error: str | None = None
    type: str = "function_call"

    def generate_error_messages(self):
        if self.execution_error:
            return [f"Error while calling function:\n{self.execution_error}"]

        return []
