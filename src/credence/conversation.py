from dataclasses import dataclass
from typing import List

from credence.step import Step


@dataclass
class Conversation:
    title: str
    steps: List[Step]
