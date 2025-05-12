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
    ChatbotIgnoresMessage,
    ChatbotResponds,
)
from credence.interaction.nested import Nested
from credence.interaction.user import UserGenerated, UserMessage
from credence.role import Role
from credence.test_result import TestResult

logger = logging.getLogger(__name__)
"""@private"""


class Adapter(abc.ABC):
    """
    `Adapter` allows credence to interact with your chatbot
    implementation.

    It:
    1. executes the interactions described in a conversation
    2. evaluates the correctness of chatbot responses and collects any errors
    3. measures the time taken by the chatbot and the test

    ---

    In order to create an adapter, you must:

    ```python
    # 1. Import the adapter
    from credence.adapter import Adapter

    # 2. Create a subclass of Adapter
    class MyChatbotAdapter(Adapter):

    # 3. Define the required `create_client` method
    def create_client(self):
        # Look at instructor's documentation for more
        # integrations - https://python.useinstructor.com/integrations/

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

    # 4. Define the model you want to use to generate
    #    user input and run AI content checks
    def model_name(self):
        return os.environ.get("MODEL_NAME", "gpt-4.1-mini")


    # 5. Define the required `handle_message` method to
    #    route messages to your chatbot
    def handle_message(self, message: str) -> str | None:
        # Send the message to your chatbot and return the response message.
        # For chatbots that internally send messages, see the notes below.

    # 6. (Optional) Define any methods you would want to
    #    execute during tests
    def register_user(self, name: str, phone_number: str):
        # my_app.register_user(name, phone_number)
        self.add_to_context("user", name)
    ```

    #### Context:

    

    #### Notes:
    1. The `handle_message` method should return a string if user responses are dispatched
       from outside the chatbot. If the chatbot handles message dispatching as well using
       some `Messenger`, we recommend using `Adapter.add_chatbot_message` with one of two options:

       a. **Add an `on_dispatch` callback to your messenger class**
        ```python
        # In your test file

        from credence.adapter import Adapter
        import pytest

        class MyChatbotAdapter(Adapter):
            def __init__(self):
            super().__init__()
            self.messenger = Messenger(on_dispatch=self.add_chatbot_message)

            def create_client(self):
                ...
            def model_name(self):
                ...

            def handle_message(self, message: str) -> str | None:
                my_app.chatbot.process_message(
                    user=self.context["user"],
                    messenger=self.messenger,
                )
        ```



       b. **Monkeypatch your messenger**

          More on pytest's monkeypatching - https://docs.pytest.org/en/stable/how-to/monkeypatch.html

          ```python
          # In your test file

          from credence.adapter import Adapter
          import pytest

          class MyChatbotAdapter(Adapter):
              def create_client(self):
                  ...
              def model_name(self):
                  ...

              def handle_message(self, message: str) -> str | None:
                  monkeypatch = self.context["monkeypatch"]

                  def mock_send_message(message: str):
                    # Manually inform the adapter that the message was sent
                    return self.add_chatbot_message(message)

                  monkeypatch.setattr(my_app.messenger.MessengerClass, "send_message", mock_send_message)



          # In your test
          @pytest.mark.parametrize("conversation", conversations())
          def test_maa(app, monkeypatch, conversation):
                  adapter = (
                      MyChatbotAdapter()
                      # Add monkeypatch to the context so you can use it within the adapter
                      .set_context(monkeypatch=monkeypatch)
                      .test(conversation)
                  )

                  ...

          ```

    2. The `register_user` method would be executed during a `credence.conversation.Conversation`
       using `External('register_user', {"name": "some name", "phone_number": "some_number"})`
    """

    def __init__(self):
        super().__init__()
        self.context = {}
        self.queue = Queue()
        """@private"""
        self.client = None
        """@private"""
        self.messages = None
        """@private"""

        from credence import metadata

        metadata.set_adapter(self)

    def __del__(self):
        """Clear the metadata when destroying the adapter"""
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
