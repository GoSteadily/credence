import copy
from dataclasses import dataclass
from typing import List

from credence.step import Step


@dataclass
class Nested(Step):
    conversation: "Conversation"

    def __str__(self):
        nested_conversation_str = str(self.conversation)
        nested_conversation_str = "".join([f"  {line}" for line in nested_conversation_str.splitlines(keepends=True)])

        return f"Conversation.nested(\n{nested_conversation_str},\n)"


@dataclass
class Conversation(Step):
    title: str
    steps: List[Step]

    @staticmethod
    def nested(conversation: "Conversation") -> Step:
        if not isinstance(conversation, Conversation):
            raise Exception("Invalid conversation")

        return Nested(conversation=copy.deepcopy(conversation))

    def __str__(self):
        steps_str = ""
        for index, step in enumerate(self.steps):
            if index != 0:
                steps_str += ","

            step_str = str(step)
            step_str = "".join([f"      {line}" for line in step_str.splitlines(keepends=True)])
            steps_str += f"\n{step_str}"

        closing_newline = ""
        if len(self.steps) > 0:
            closing_newline = ",\n  "

        return f"""
Conversation(
  title="{self.title}",
  steps=[{steps_str}{closing_newline}],
)
""".strip()
