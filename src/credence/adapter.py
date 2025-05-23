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
from credence.interaction.nested_conversation import NestedConversation
from credence.interaction.user import UserGenerated, UserMessage
from credence.role import Role
from credence.test_result import Message, TestResult

logger = logging.getLogger(__name__)
"""@private"""

default_user_simulator_system_prompt = (
    "You are now simulating a user who is interacting with a chatbot.\nDo not behave like an AI assistant, for example, don't offer to give assistance."
)


def _docstring_parameter(*sub):
    def dec(obj):
        obj.__doc__ = obj.__doc__.format(*sub)
        return obj

    return dec


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

        # 4. Define the required `model_name` method
        def model_name(self):
            return os.environ.get("MODEL_NAME", "gpt-4.1-mini")


        # 5. Define the required `handle_message`
        def handle_message(self, message: str) -> str | None:
            # Send the message to your chatbot and return the response message.
            # For chatbots that internally send messages, see the notes below.
            return my_app.chatbot.process_message(message)

        # 6. (Optional) Define any methods you would want to
        #    execute during tests
        #
        #    The method below would be executed by adding the following interaction to
        #    a conversation: `External('register_user', {"name": "some name", "phone_number": "some_number"})`
        def register_user(self, name: str, phone_number: str):
            # Run a system method eg my_app.register_user(name, phone_number)
            self.context["user"] = name
    ```
    """

    def __init__(self):
        super().__init__()
        self.context: Dict[str, Any] = {}
        """
        The adapter provides an empty `context` dictionary that can be used to
        persist some state across a conversation. You can set the initial context with `set_context`.

        ### Usage:

        Imagine you had a conversation that starts by registering a user:

        ```python
        conversation = Conversation(
            title="...",
            interactions=[
                External("register", {"user": "John", "phone_number": "+12345678901"}),
                User.message("..."),
                ...
            ],
        )
        ```

        If your chatbot requires some `User` instance when processing a
        message, you can store the registered user's phone number in the adapter's context
        during registration. Later, in `handle_message`, you could that phone number to load
        the user from the database:

        ```python
        from credence.adapter import Adapter

        class MyChatbotAdapter(Adapter):
            def create_client(self):
                ...

            def model_name(self):
                ...

            def register_user(self, name: str, phone_number: str):
                # 1. Store the registered user's phone number
                self.context["phone_number"] = phone_number
                my_app.register_user(name, phone_number)

            def handle_message(self, message: str) -> str | None:
                user: User = my_app.get_user(self.context["phone_number"])
                my_app.chatbot.process_message(
                    user=user,
                    message=message,
                )

        ```
        """

        self.queue: Queue[Tuple[int, str]] = Queue()
        """@private"""

        self.client: Instructor | None = None
        """@private"""

        self.messages: List[Message] = []
        """@private"""

        self.next_message_index: int = 0
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

    def set_context(self, **kwargs: Dict[str, Any]):
        """
        Replace the current context with another dictionary.
        """
        self.context = kwargs
        return self

    @abc.abstractmethod
    def handle_message(self, message: str):
        """
        Call your chatbot to handle a message

        ## Handling messages sent from within your chatbot

        The `handle_message` method should return a string if user responses are dispatched
        from outside the chatbot. If the chatbot handles message dispatching as well using
        some `Messenger`, we recommend using `Adapter.record_chatbot_message` with one of two options:

        a. **Add an `on_dispatch` callback to your messenger class**
         ```python
         # In your test file

         from credence.adapter import Adapter
         import pytest

         class MyChatbotAdapter(Adapter):
             def __init__(self):
                super().__init__()
                self.messenger = Messenger(on_dispatch=self.record_chatbot_message)

             def handle_message(self, message: str) -> str | None:
                 my_app.chatbot.process_message(
                     user=self.context["user"],
                     messenger=self.messenger,
                 )
                 return None

             ... # other required methods
         ```

        b. **Monkeypatch your messenger**

           More on pytest's monkeypatching - https://docs.pytest.org/en/stable/how-to/monkeypatch.html

           ```python
           # In your test file

           from credence.adapter import Adapter
           import pytest

           class MyChatbotAdapter(Adapter):
               def handle_message(self, message: str) -> str | None:
                   monkeypatch = self.context["monkeypatch"]

                   def mock_send_message(message: str):
                     # Manually inform the adapter that the message was sent
                     return self.record_chatbot_message(message)

                   monkeypatch.setattr(my_app.messenger.MessengerClass, "send_message", mock_send_message)
                    return None

               ... # other required methods

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
        """

    @abc.abstractmethod
    def create_client(self) -> Instructor:
        """
        Create an instructor client for your adapter

        **Example**

        ```python
        def create_client(self):
            # Look at instructor's documentation for more
            # integrations - https://python.useinstructor.com/integrations/


            client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            return instructor.from_openai(client, mode=instructor.Mode.TOOLS)
        ```

        Look at instructor's documentation for more integrations - https://python.useinstructor.com/integrations/
        """

    @abc.abstractmethod
    def model_name(self) -> str:
        """
        Define the name of the model to be used in generating user messages and running AI checks
        """

    def get_client(self) -> Instructor:
        "@private"
        if self.client is None:
            self.client = self.create_client()

        return self.client

    def record_chatbot_message(self, chatbot_message: str):
        """
        Manually inform the adapter of a chatbot response message.
        See `handle_message` for more details.
        """
        self._add_message(Role.Chatbot, chatbot_message)

        return self

    def _add_message(self, role: Role, message: str):
        from credence import metadata

        message_metadata = None
        if role == Role.Chatbot:
            self.queue.put_nowait((self.next_message_index, message))
            message_metadata = metadata.get_values()

        self.messages.append(
            Message(
                index=self.next_message_index,
                role=role,
                body=message,
                metadata=message_metadata,
            )
        )

        self.next_message_index += 1

    def test(self, conversation: Conversation) -> TestResult:
        """
        Evaluate the conversation against your chatbot
        """

        from credence.interaction.external import External

        start_time = time.time()
        testing_time = 0.0

        try:
            for interaction in conversation.interactions:
                if isinstance(interaction, NestedConversation):
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
                    self._add_message(Role.User, interaction.text)

                    chatbot_response = self.handle_message(interaction.text)

                    if chatbot_response:
                        self._add_message(Role.Chatbot, chatbot_response)

                elif isinstance(interaction, UserGenerated):
                    self._assert_no_chatbot_messages()

                    generation_start_time = time.time()

                    client = self.get_client()
                    text = self._generate_user_message(client=client, interaction=interaction, messages=self.messages)
                    testing_time += time.time() - generation_start_time

                    self._add_message(Role.User, text)

                    chatbot_response = self.handle_message(text)
                    if chatbot_response:
                        self._add_message(Role.Chatbot, chatbot_response)

                elif isinstance(interaction, ChatbotResponds):
                    generation_start_time = time.time()

                    chatbot_response = self._get_queued_chatbot_message()
                    exceptions = interaction.check(
                        adapter=self,
                        messages=self.messages,
                        chatbot_response=chatbot_response,
                    )

                    if exceptions:
                        return TestResult(
                            conversation=conversation,
                            messages=self.messages,
                            errors=exceptions,
                            testing_time_ms=round(testing_time * 1000),
                            chatbot_time_ms=round((time.time() - start_time - testing_time) * 1000),
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
        except Empty:
            raise Exception("Expected a chatbot message but none had been sent") from None

    @_docstring_parameter(default_user_simulator_system_prompt)
    def user_simulator_system_prompt(self) -> str | None:
        """
        By default, credence uses a simple systen prompt to generate user messages:

        ```
        {0}
        ```

        You can override the prompt by overriding the `user_simulator_system_prompt`
        method and returning an alternative prompt.
        """
        return dedent(default_user_simulator_system_prompt).strip()

    def _generate_user_message(
        self,
        client: Instructor,
        interaction: UserGenerated,
        messages: List[Message],
    ):
        llm_messages: List[ChatCompletionMessageParam] = []

        prompt = self.user_simulator_system_prompt() or default_user_simulator_system_prompt
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

        llm_messages.append(Role.Chatbot.to_llm_message(interaction.prompt))
        return client.chat.completions.create(
            model=self.model_name(),
            response_model=str,
            messages=llm_messages,
        )
