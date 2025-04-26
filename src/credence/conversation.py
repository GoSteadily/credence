from dataclasses import dataclass
from typing import List

from credence.step import Step


@dataclass
class Conversation(Step):
    title: str
    steps: List[Step]
