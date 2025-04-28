from dataclasses import dataclass

from credence.step import Step


@dataclass
class Nested(Step):
    from credence.conversation import Conversation

    conversation: Conversation
