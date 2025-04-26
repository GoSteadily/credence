import abc
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from queue import Empty, Queue
from typing import Any, Dict, List, Tuple

from instructor import Instructor

from credence.conversation import Conversation
from credence.step.chatbot import ChatbotExpectations, ChatbotResponseAICheck, ChatbotResponseContains, ChatbotResponseRegexMatch
from credence.step.check import ContentTestResult
from credence.step.execute import Execute
from credence.step.user import UserGenerated, UserMessage

logger = logging.getLogger(__name__)


class Role(Enum):
    Chatbot = "assistant"
    User = "user"

    def invert(self):
        match self:
            case Role.Chatbot:
                return Role.User
            case Role.User:
                return Role.Chatbot


@dataclass
class TestResult:
    messages: List[Tuple[Role, str]]
    errors: List[Any]
    time_taken_ms: int

    def print(self):
        print(self)


class Adapter(abc.ABC):
    def __init__(self):
        super().__init__()
        self.context = {}
        self.queue = Queue()
        self.client = None

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

    def test(self, conversation: Conversation) -> TestResult:
        """ """
        # for loop in try
        start_time = time.time()

        messages = []

        try:
            for step in conversation.steps:
                if isinstance(step, Execute):
                    self._call_function(step)

                elif isinstance(step, UserMessage):
                    self._assert_no_chatbot_messages()
                    messages.append((Role.User, step.text))

                    chatbot_response = self.handle_message(step.text)
                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(step, UserGenerated):
                    self._assert_no_chatbot_messages()
                    client = self._client()
                    text = self._generate_user_message(client=client, step=step, messages=messages)
                    messages.append((Role.User, text))

                    chatbot_response = self.handle_message(text)
                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(step, ChatbotExpectations):
                    chatbot_response = self._get_queued_chatbot_message()
                    self._check_expectations_were_met(
                        step=step,
                        messages=messages,
                        chatbot_response=chatbot_response,
                    )

        except Exception as e:
            logger.exception("Test failed")
            return TestResult(
                messages=messages,
                errors=[e],
                time_taken_ms=round((time.time() - start_time) * 1000),
            )

        return TestResult(
            messages=messages,
            errors=[],
            time_taken_ms=round((time.time() - start_time) * 1000),
        )

    def _call_function(self, step: Execute):
        if hasattr(self, step.function_name) and callable(getattr(self, step.function_name)):
            func = getattr(self, step.function_name)
            func(**step.args)
        else:
            raise Exception(f"Function not defined: {step.function_name}")

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
        return """
You are a system that simulates user conversations.

Pretend you are a user and complete this conversation.
"""

    def _generate_user_message(
        self,
        client: Instructor,
        step: UserGenerated,
        messages: List[Tuple[Role, str]],
    ):
        llm_messages = []

        for role, message in messages:
            llm_messages.append(
                {
                    "role": role.invert().value,
                    "content": message,
                }
            )
        llm_messages.append({"role": "system", "content": self.user_message_prompt() + "\n" + step.prompt})

        return client.chat.completions.create(
            model=self.model_name(),
            response_model=str,
            messages=llm_messages,
        )

    def _check_expectations_were_met(
        self,
        step: ChatbotExpectations,
        messages: List[Tuple[Role, str]],
        chatbot_response: str,
    ):
        for expectation in step.expectations:
            if isinstance(expectation, ChatbotResponseAICheck):
                client = self._client()
                ContentTestResult.check_requirement(
                    client=client,
                    messages=messages,
                    requirement=expectation.prompt,
                )

            elif isinstance(expectation, ChatbotResponseContains):
                if expectation.string not in chatbot_response:
                    raise Exception(f"{expectation.string} not in chatbot response: {chatbot_response}")

            elif isinstance(expectation, ChatbotResponseRegexMatch):
                if re.search(expectation.pattern, chatbot_response) is None:
                    raise Exception(f"{expectation.pattern} not found in chatbot response: {chatbot_response}")
