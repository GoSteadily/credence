from dataclasses import dataclass, field
from typing import Dict

from credence.step import Step


@dataclass
class Execute(Step):
    function_name: str
    args: Dict[str, str] = field(default_factory=dict)
