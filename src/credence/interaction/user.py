import copy
from dataclasses import dataclass
from typing import Any, List

from instructor import Instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam

from credence.interaction import Interaction, InteractionResult, InteractionResultStatus
from credence.message import Message
from credence.role import Role


@dataclass
class UserMessage(Interaction):
    """@private"""

    text: str
    generated: bool

    def is_user_interaction(self) -> bool:
        return True

    def is_chatbot_interaction(self) -> bool:
        return False

    def to_result(
        self,
        skipped: bool,
        client: Instructor,
        model_name: str,
        prompt: str,
        messages: List[Message],
        handle_message: Any,
        next_chatbot_message: str | None,
    ):
        if skipped:
            return self.skipped()

        if next_chatbot_message:
            return self.failed(unexpected_chatbot_message=f"{next_chatbot_message}")

        if self.generated:
            try:
                user_message = self._generate_user_message(
                    client=client,
                    model_name=model_name,
                    messages=messages,
                    system_prompt=prompt,
                    generation_prompt=self.text,
                )
            except Exception as e:
                return self.failed(generation_error=f"{e}")

        else:
            user_message = self.text

        try:
            chatbot_response = handle_message(user_message)
            return self.passed(
                user_message=user_message,
                chatbot_response=chatbot_response,
            )

        except Exception as e:
            self.failed(handle_message_error=f"{e}")

    def _generate_user_message(
        self,
        client: Instructor,
        model_name: str,
        messages: List[Message],
        system_prompt: str,
        generation_prompt: str,
    ):
        llm_messages: List[ChatCompletionMessageParam] = []

        prompt = system_prompt

        if messages:
            context = "\nContext:"
            for message in messages:
                context += f"{str(message.role)}: {message.body}\n"

            prompt += context

        llm_messages.append(
            ChatCompletionSystemMessageParam(
                role="system",
                content=prompt,
            )
        )

        llm_messages.append(Role.Chatbot.to_llm_message(generation_prompt))
        return client.chat.completions.create(
            model=model_name,
            response_model=str,
            messages=llm_messages,
        )

    def passed(
        self,
        user_message: str,
        chatbot_response: str,
    ) -> "UserMessageResult":
        return UserMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Passed,
            user_message=user_message,
            chatbot_response=chatbot_response,
        )

    def failed(
        self,
        user_message: str | None = None,
        generation_error: str | None = None,
        handle_message_error: str | None = None,
        unexpected_chatbot_message: str | None = None,
    ) -> "UserMessageResult":
        return UserMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Failed,
            user_message=user_message,
            generation_error=generation_error,
            handle_message_error=handle_message_error,
            unexpected_chatbot_message=unexpected_chatbot_message,
        )

    def skipped(
        self,
    ) -> "UserMessageResult":
        return UserMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Skipped,
        )


@dataclass
class UserMessageResult(InteractionResult):
    """@private"""

    data: UserMessage
    status: InteractionResultStatus
    user_message: str | None = None
    chatbot_response: str | None = None
    generation_error: str | None = None
    handle_message_error: str | None = None
    unexpected_chatbot_message: str | None = None

    def generate_error_messages(self):
        if self.generation_error:
            return [f"Error while generating user message:\n`{self.generation_error}`"]
        if self.handle_message_error:
            return [f"Error while calling `handle_message`:\n`{self.handle_message_error}`"]
        if self.unexpected_chatbot_message:
            return [f"Got an unexpected chatbot message:\n`{self.unexpected_chatbot_message}`"]

        return []


class User:
    """
    `User` interactions allow us to simulate a user sending messages
    to the chatbot.
    """

    @staticmethod
    def message(text: str):
        """
        Send a specific text message to the chatbot.
        """
        return UserMessage(text=text, generated=False)

    @staticmethod
    def generated(prompt: str):
        """
        Send an ai-generated text message to the chatbot based on a prompt.
        """
        return UserMessage(text=prompt, generated=True)
