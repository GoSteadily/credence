from dataclasses import dataclass
from typing import List

from termcolor import cprint

from credence.conversation import Conversation
from credence.exceptions import ColoredException
from credence.interaction import InteractionResult, InteractionResultStatus
from credence.message import Message
from credence.role import Role


@dataclass
class Result:
    messages: List[Message]
    failed: bool
    title: str
    interaction_results: List[InteractionResult]
    chatbot_time_ms: int
    testing_time_ms: int

    def to_stdout(self):
        cprint("")
        cprint("------------ Result ------------", attrs=["bold"])
        cprint(self.title)
        cprint("------------------------------------")
        cprint(f"  Total Time:  {(self.chatbot_time_ms + self.testing_time_ms) / 1000}s")
        cprint(f"   Test Time:  {self.testing_time_ms / 1000}s")
        cprint(f"Chatbot Time:  {self.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for message in self.messages:
            if message.role == Role.User:
                color = "blue"
                name = "user: "
            if message.role == Role.Chatbot:
                color = "green"
                name = "asst: "

            cprint(name, color, attrs=["bold"], end="")
            cprint(message.body)

        # errors: List[Any]

        if self.failed:
            errors = []
            for result in self.interaction_results:
                if result.status == InteractionResultStatus.Failed:
                    errors.extend(result.generate_error_messages())


            if errors:
                cprint("-------------- Errors --------------", "red", attrs=["bold"])
                for index, error in enumerate(errors, 1):
                    if isinstance(error, ColoredException):
                        print(f"{index}. {error.colored_message}\n")

                    else:
                        cprint(f"{index}. {error}\n", "red", attrs=[])

    def to_markdown(self, index=None):
        from credence.result.markdown import MarkdownRenderer

        return MarkdownRenderer.to_markdown(self, index)

    def to_json(self, index=None):
        from credence.result.json import JsonRenderer

        return JsonRenderer.to_json(self, index)

    def _get_internal_interactions(self):
        return self._do_get_internal_interactions(interactions=[], conversation=self.conversation)

    def _do_get_internal_interactions(self, interactions, conversation: Conversation):
        for interaction in conversation.interactions:
            from credence.interaction.nested_conversation import NestedConversation

            if isinstance(interaction, NestedConversation):
                self._do_get_internal_interactions(
                    conversation=interaction.conversation,
                    interactions=interactions,
                )
            if interaction.is_user_interaction():
                interactions.append(interaction)

            if interaction.is_chatbot_interaction():
                interactions.append(interaction)

        return interactions
