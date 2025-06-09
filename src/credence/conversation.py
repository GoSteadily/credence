import copy
import uuid
from dataclasses import dataclass, field
from typing import List

from credence.interaction import Interaction


@dataclass
class Conversation:
    """
    A `Conversation` is used to test a chatbot.

    It describes the expected interactions between a user
    and the chatbot.

    There are 3 interactions supported:
    1. User interactions are used to send messages to your chatbot as a user (`credence.interaction.user.User`).
    2. Chatbot interactions are used to run checks on the expected response from the chatbot (`credence.interaction.chatbot.Chatbot`).
    3. FunctionCall interactions act as an escape hatch allowing you to model
       interactions that take place outside the normal message sending flow (`credence.interaction.external.FunctionCall`).

       This is commonly used for events that happen somewhere else,
       such as user sign-up or payment from your website.

    Additionally, to allow code reuse, conversations can be nested within
    on another using `Conversation.nested(conversation)`. This is helpful if you have an involved enrolment flow
    that would otherwise need to be repeated in each conversation.
    """

    title: str
    """A unique title used to identify a conversation."""

    interactions: List[Interaction]
    """The sequence of interactions being tested."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """A unique id used to identify a conversation."""

    @staticmethod
    def nested(name: str, conversation: "Conversation") -> Interaction:
        """
        Reuse a conversation inside another conversation.

        See: `credence.interaction.nested_conversation.NestedConversation`
        """
        if not isinstance(conversation, Conversation):
            raise Exception("Invalid conversation")

        from credence.interaction.nested_conversation import NestedConversation

        return NestedConversation(name=name, conversation=copy.deepcopy(conversation))

    def __str__(self):
        """
        Generate the code used to create an interaction
        """
        interactions_str = ""
        for index, interaction in enumerate(self.interactions):
            if index != 0:
                interactions_str += ","

            interaction_str = str(interaction)
            interaction_str = "".join([f"      {line}" for line in interaction_str.splitlines(keepends=True)])
            interactions_str += f"\n{interaction_str}"

        closing_newline = ""
        if len(self.interactions) > 0:
            closing_newline = ",\n  "

        return f"""
Conversation(
  title="{self.title}",
  interactions=[{interactions_str}{closing_newline}],
)
""".strip()
