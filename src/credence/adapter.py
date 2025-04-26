import abc
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from queue import Empty, Queue
from typing import Any, Dict, List, Tuple

from instructor import Instructor
from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from termcolor import colored, cprint

from credence.conversation import Conversation
from credence.step.chatbot import ChatbotExpectations, ChatbotResponseAICheck, ChatbotResponseContains, ChatbotResponseEquals, ChatbotResponseRegexMatch
from credence.step.check import ContentTestResult
from credence.step.execute import Execute
from credence.step.user import UserGenerated, UserMessage

logger = logging.getLogger(__name__)


class Role(str, Enum):
    Chatbot = "assistant"
    User = "user"

    def invert(self):
        match self:
            case Role.Chatbot:
                return Role.User
            case Role.User:
                return Role.Chatbot

    def to_llm_message(self, message: str):
        match self:
            case Role.Chatbot:
                return ChatCompletionUserMessageParam(role="user", content=message)
            case Role.User:
                return ChatCompletionAssistantMessageParam(role="assistant", content=message)


@dataclass
class TestResult:
    title: str
    messages: List[Tuple[Role, str]]
    errors: List[Any]
    time_taken_ms: int
    chatbot_time_ms: int

    def print(self):
        cprint("")
        cprint("------------ TestResult ------------", attrs=["bold"])
        cprint(self.title)
        cprint("------------------------------------")
        cprint(f"   Test Time:  {self.time_taken_ms / 1000}s")
        cprint(f"Handler Time:  {self.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for role, message in self.messages:
            if role == Role.User:
                color = "blue"
                name = "user: "
            if role == Role.Chatbot:
                color = "green"
                name = "asst: "

            cprint(name, color, attrs=["bold"], end="")
            cprint(message)

        for error in self.errors:
            cprint(error, "red", attrs=[])

        cprint("")


class Adapter(abc.ABC):
    def __init__(self):
        super().__init__()
        self.context = {}
        self.queue = Queue()
        self.client = None
        self.messages = None

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
        """ """
        start_time = time.time()
        time_spent_in_generation = 0.0

        if self.messages is None:
            self.messages = []

        try:
            for step in conversation.steps:
                if isinstance(step, Conversation):
                    result = self.test(step)
                    if result.errors:
                        return result

                if isinstance(step, Execute):
                    self._call_function(step)

                elif isinstance(step, UserMessage):
                    self._assert_no_chatbot_messages()
                    self.messages.append((Role.User, step.text))

                    chatbot_response = self.handle_message(step.text)
                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        self.messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(step, UserGenerated):
                    self._assert_no_chatbot_messages()

                    generation_start_time = time.time()

                    client = self._client()
                    text = self._generate_user_message(client=client, step=step, messages=self.messages)
                    time_spent_in_generation += time.time() - generation_start_time

                    self.messages.append((Role.User, text))

                    chatbot_response = self.handle_message(text)
                    if chatbot_response:
                        self.queue.put_nowait(chatbot_response)
                        self.messages.append((Role.Chatbot, chatbot_response))

                elif isinstance(step, ChatbotExpectations):
                    generation_start_time = time.time()

                    chatbot_response = self._get_queued_chatbot_message()
                    self._check_expectations_were_met(
                        step=step,
                        messages=self.messages,
                        chatbot_response=chatbot_response,
                    )
                    time_spent_in_generation += time.time() - generation_start_time

        except Exception as e:
            logger.exception("Test failed")
            return TestResult(
                title=conversation.title,
                messages=self.messages,
                errors=[e],
                time_taken_ms=round((time.time() - start_time) * 1000),
                chatbot_time_ms=round((time.time() - start_time - time_spent_in_generation) * 1000),
            )

        return TestResult(
            title=conversation.title,
            messages=self.messages,
            errors=[],
            time_taken_ms=round((time.time() - start_time) * 1000),
            chatbot_time_ms=round((time.time() - start_time - time_spent_in_generation) * 1000),
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
        llm_messages: List[ChatCompletionMessageParam] = []

        for role, message in messages:
            llm_messages.append(role.invert().to_llm_message(message))

        llm_messages.append(ChatCompletionSystemMessageParam(role="system", content=self.user_message_prompt() + "\n" + step.prompt))

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
                result = ContentTestResult.check_requirement(
                    client=client,
                    model_name=self.model_name(),
                    messages=messages,
                    requirement=expectation.prompt,
                )
                if not result.was_met:
                    raise Exception(
                        f"""
chatbot response did not pass AI check:
{colored("requirement", attrs=["bold"])}: {expectation.prompt}
{colored("     reason", attrs=["bold"])}: {result.reason}
{colored("   response", attrs=["bold"])}: {chatbot_response}"""
                    )

            elif isinstance(expectation, ChatbotResponseEquals):
                if expectation.string != chatbot_response:
                    raise Exception(f"chatbot response is not equal to `{expectation.string}`: `{chatbot_response}`")
            elif isinstance(expectation, ChatbotResponseContains):
                if expectation.string not in chatbot_response:
                    raise Exception(f"`{expectation.string}` not in chatbot response: `{chatbot_response}`")

            elif isinstance(expectation, ChatbotResponseRegexMatch):
                if re.search(expectation.pattern, chatbot_response) is None:
                    raise Exception(f"{expectation.pattern} not found in chatbot response: `{chatbot_response}`")
