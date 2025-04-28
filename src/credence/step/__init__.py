import copy
from dataclasses import dataclass


@dataclass(kw_only=True)
class Step:
    def nested_conversation(conversation):
        from credence.conversation import Conversation

        from .nested import Nested

        if not isinstance(conversation, Conversation):
            raise Exception("Invalid conversation")

        return Nested(conversation=copy.deepcopy(conversation))
