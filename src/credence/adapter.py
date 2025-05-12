import abc
import logging
import time
from queue import Empty, Queue
from textwrap import dedent
from typing import Any, Dict, List, Tuple

from instructor import Instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam

from credence.conversation import Conversation
from credence.interaction.chatbot import (
    ChatbotResponds,
    ChatbotIgnoresMessage,
)
from credence.interaction.nested import Nested
from credence.interaction.user import UserGenerated, UserMessage
from credence.role import Role
from credence.test_result import TestResult

logger = logging.getLogger(__name__)


class Adapter(abc.ABC):
    def __init__(self):
        super().__init__()
        self.context = {}
        self.queue = Queue()
        self.client = None
        self.messages = None

        from credence import metadata

        metadata.set_adapter(self)

    def __del__(self):
        try:
            from credence import metadata

            metadata.clear_adapter(None)
        except Exception:
            pass

    @abc.abstractmethod
    def handle_message(self, message: str):
        """
        Call your chatbot to handle a message
        """

    @abc.abstractmethod
    def create_client(self) -> Instructor:
        """
        Create an instructor client
        """

    @abc.abstractmethod
    def model_name(self) -> str:
        """
        Define the name of the model to be used
        """

    def _client(self) -> Instructor:
        """
        Create an instructor client
        """
        if self.client is None:
            self.client = self.create_client()

        return self.client

    def set_context(self, **kwargs: Dict[str, Any]):
        self.context = kwargs
        return self

    def add_to_context(self, key: str, value: Any):
        self.context[key] = value
        return self

    def add_chatbot_message(self, chatbot_message: str):
        self.queue.put_nowait(chatbot_message)
        self.messages.append((Role.Chatbot, chatbot_message))

        return self

    def test(self, conversation: Conversation) -> TestResult:
        """
        TODO: Add docs
        """

        from credence.interaction.external import External

        start_time = time.time()
        testing_time = 0.0

        if self.messages is None:
            self.messages = []

        try:
            for interaction in conversation.interactions:
                if isinstance(interaction, Nested):
                    result = self.test(interaction.conversation)
                    testing_time += result.testing_time_ms / 1000
                    if result.errors:
                        result.conversation = conversation
                        result.chatbot_time_ms = round((time.time() - start_time - testing_time) * 1000)
                        result.testing_time_ms = round(testing_time * 1000)
                        return result

                elif isinstance(interaction, External):
                    interaction.call(self)

                elif isinstance(interaction, UserMessage):
                    self._assert_no_chatbot_messages()
                    self.messages.append((Role.User, interaction.text))

                    from credence import metadata

                    metadata.clear()
                    chatbot_response = self.handle_message(interaction.text)

                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        self.messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(interaction, UserGenerated):
                    self._assert_no_chatbot_messages()

                    generation_start_time = time.time()

                    client = self._client()
                    text = self._generate_user_message(client=client, interaction=interaction, messages=self.messages)
                    testing_time += time.time() - generation_start_time

                    self.messages.append((Role.User, text))

                    chatbot_response = self.handle_message(text)
                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        self.messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(interaction, ChatbotResponds):
                    generation_start_time = time.time()

                    chatbot_response = self._get_queued_chatbot_message()
                    interaction._check(
                        adapter=self,
                        messages=self.messages,
                        chatbot_response=chatbot_response,
                    )
                    testing_time += time.time() - generation_start_time
                elif isinstance(interaction, ChatbotIgnoresMessage):
                    self._assert_no_chatbot_messages()

        except Exception as e:
            logger.exception("Test failed")
            return TestResult(
                conversation=conversation,
                messages=self.messages,
                errors=[e],
                testing_time_ms=round(testing_time * 1000),
                chatbot_time_ms=round((time.time() - start_time - testing_time) * 1000),
            )

        return TestResult(
            conversation=conversation,
            messages=self.messages,
            errors=[],
            testing_time_ms=round(testing_time * 1000),
            chatbot_time_ms=round((time.time() - start_time - testing_time) * 1000),
        )

    def _assert_no_chatbot_messages(self):
        try:
            message = self.queue.get_nowait()
            raise Exception(f"Unexpected chatbot message: {message}")
        except Empty:
            return None

    def _get_queued_chatbot_message(self):
        try:
            return self.queue.get_nowait()
        except Empty as e:
            raise Exception("Expected a chatbot message but none had been sent") from e

    def user_message_prompt(self):
        return dedent("""
            You are now simulating a user who is interacting with a system.
            You are not an assistant.
            """).strip()

    def _generate_user_message(
        self,
        client: Instructor,
        interaction: UserGenerated,
        messages: List[Tuple[Role, str]],
    ):
        llm_messages: List[ChatCompletionMessageParam] = []

        prompt = self.user_message_prompt()
        if messages:
            context = "\nContext:"
            for role, message in messages:
                context += f"{str(role)}: {message}\n"

            prompt += context

        llm_messages.append(
            ChatCompletionSystemMessageParam(
                role="system",
                content=prompt,
            )
        )

        llm_messages.append(Role.Chatbot.to_llm_message(interaction.prompt))

        return client.chat.completions.create(
            model=self.model_name(),
            response_model=str,
            messages=llm_messages,
        )
