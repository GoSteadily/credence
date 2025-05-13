from dataclasses import dataclass, field
from typing import Dict

from credence.adapter import Adapter
from credence.interaction import Interaction


@dataclass
class External(Interaction):
    """
    `External` interactions allow you to run any function defined in an
    `Adapter` class.

    This acts as an escape hatch allowing you to model interactions that
    take place outside the normal message sending flow such as user sign-up
    or payment from your website.

    ### Usage
    >>> External("function_with_no_args")

    >>> External("function_with_args", {"arg_a": "1", "arg_b": "2"})
    """

    function: str
    """The name of the function on the adapter instance."""
    kwargs: Dict[str, str] = field(default_factory=dict)
    """The keyword arguments that will be applied to the function."""

    def call(self, adapter: "Adapter"):
        if hasattr(adapter, self.function) and callable(getattr(adapter, self.function)):
            func = getattr(adapter, self.function)
            func(**self.kwargs)
        else:
            raise Exception(f"Function not defined: {self.function}")

    def __str__(self):
        """ """
        name = self.function.__repr__()

        if len(self.kwargs) > 0:
            return f"External({name}, {self.kwargs})"

        else:
            return f"External({name})"
