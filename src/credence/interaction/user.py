from dataclasses import dataclass

from credence.interaction import Interaction


@dataclass
class UserMessage(Interaction):
    """@private"""

    text: str


@dataclass
class UserGenerated(Interaction):
    """@private"""

    prompt: str


class User(Interaction):
    @staticmethod
    def message(text: str):
        return UserMessage(text=text)

    @staticmethod
    def generated(prompt: str):
        return UserGenerated(prompt=prompt)
