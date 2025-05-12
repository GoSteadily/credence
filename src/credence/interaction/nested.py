from dataclasses import dataclass

from credence.conversation import Conversation
from credence.interaction import Interaction


@dataclass
class Nested(Interaction):
    conversation: "Conversation"

    def __str__(self):
        nested_conversation_str = str(self.conversation)
        nested_conversation_str = "".join([f"  {line}" for line in nested_conversation_str.splitlines(keepends=True)])

        return f"Conversation.nested(\n{nested_conversation_str},\n)"
