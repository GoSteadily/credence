from dataclasses import dataclass
from typing import Dict

from credence.step import Step


@dataclass
class Execute(Step):
    function_name: str
    args: Dict[str, str]
