from dataclasses import dataclass

from credence.step import Step


@dataclass
class UserMessage(Step):
    text: str


@dataclass
class UserGenerated(Step):
    prompt: str


class User(Step):
    @staticmethod
    def message(text: str):
        return UserMessage(text=text)

    @staticmethod
    def generated(prompt: str):
        return UserGenerated(prompt=prompt)
