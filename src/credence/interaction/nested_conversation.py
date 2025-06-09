import copy
from dataclasses import dataclass

from credence.conversation import Conversation
from credence.interaction import Interaction, InteractionResult, InteractionResultStatus

from ..result import Result


@dataclass
class NestedConversation(Interaction):
    """
    `NestedConversation`s allow us to include an existing conversation's
    interactions inside a new conversation allowing code reuse.

    Created using `credence.conversation.Conversation.nested`.

    ```python
    # Create a conversation made up of often repeated interactions.
    #
    # In the example below, the user must always agree to terms of service
    # before using the chatbot. To avoid repeating this flow several times,
    # we create a conversation for this flow and reuse it in other conversations.
    agree_to_tos_conversation = Conversation(
        title="new user must agree to TOS",
        interactions=[
            User.message("Hi"),
            Chatbot.responds(
                [Response.equals("Hi. Do you agree to our terms of service?")]),
            Chatbot.responds([Response.equals("Yes")]),
            Chatbot.responds([Response.equals("Welcome aboard")]),
        ],
    )

    london_weather_conversation = Conversation(
        title="chatbot can answer weather related questions",
        interactions=[
            # Reuse the agree_to_tos_conversation
            Conversation.nested("Register User Flow", agree_to_tos_conversation),
            User.message("What is the weather in London?"),
            Chatbot.responds([Response.equals("It is drizzling.")]),
        ],
    )

    ambiguous_location_conversation = Conversation(
        title="chatbot asks for extra information when asked ambiguous weather related questions",
        interactions=[
            # Reuse the agree_to_tos_conversation
            Conversation.nested("Register User Flow", agree_to_tos_conversation),
            User.message("What is the weather?"),
            Chatbot.responds([Response.equals("Which city are you interested in?")]),
        ],
    )
    ```
    """

    name: str
    """@private The name given to the nested conversation"""

    conversation: Conversation
    """@private The nested conversation"""

    def __str__(self):
        nested_conversation_str = str(self.conversation)
        nested_conversation_str = "".join([f"  {line}" for line in nested_conversation_str.splitlines(keepends=True)]).strip()

        return f"""
Conversation.nested(
  {self.name.__repr__()},
  {nested_conversation_str},
)
""".strip()

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return False

    def to_result(self, conversation_results: Result, skipped: bool) -> "NestedConversationResult":
        "@private"

        status = InteractionResultStatus.Passed
        if conversation_results.failed:
            status = InteractionResultStatus.Failed
        if skipped:
            status = InteractionResultStatus.Skipped

        return NestedConversationResult(
            data=copy.deepcopy(self),
            status=status,
            results=conversation_results,
        )


@dataclass(kw_only=True)
class NestedConversationResult(InteractionResult):
    data: NestedConversation
    status: InteractionResultStatus
    results: Result

    def generate_error_messages(self):
        errors = []
        for result in self.results.interaction_results:
            errors.extend(result.generate_error_messages())

        return errors
