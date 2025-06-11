import abc
import logging
import time
import traceback
from queue import Empty, Queue
from textwrap import dedent
from typing import Any, Dict, List

from instructor import Instructor

from credence.conversation import Conversation
from credence.interaction import InteractionResultStatus
from credence.interaction.chatbot import (
    ChatbotIgnoresMessage,
    ChatbotResponds,
)
from credence.interaction.nested_conversation import NestedConversation
from credence.interaction.user import UserMessage
from credence.result import Message, Result
from credence.role import Role

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
        #    a conversation: `FunctionCall('register_user', {"name": "some name", "phone_number": "some_number"})`
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
                FunctionCall("register", {"user": "John", "phone_number": "+12345678901"}),
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

        self.queue: Queue[str] = Queue()
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

            metadata.clear_adapter()
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
            self.queue.put_nowait(message)
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

    def test(self, conversation: Conversation) -> Result:
        """
        Evaluate the conversation against your chatbot
        """
        return self._test(conversation, False)

    def _test(self, conversation: Conversation, has_failed: bool) -> Result:
        """
        @private
        """

        start_time = time.time()
        testing_time = 0.0

        interaction_results = []

        for interaction in conversation.interactions:
            from credence.interaction.function_call import FunctionCall

            if isinstance(interaction, NestedConversation):
                child_conversation_results = self._test(
                    interaction.conversation,
                    has_failed=has_failed,
                )

                interaction_results.append(interaction.to_result(conversation_results=child_conversation_results, skipped=has_failed))

            elif isinstance(interaction, FunctionCall):
                try:
                    if has_failed:
                        interaction_results.append(interaction.skipped())
                        continue

                    interaction.call(self)
                    interaction_results.append(interaction.passed())

                except Exception:
                    trace = str(traceback.format_exc())
                    interaction_results.append(interaction.failed(execution_error=f"{trace[-3000:]}"))

            elif isinstance(interaction, UserMessage):
                generation_start_time = time.time()

                prompt = self.user_simulator_system_prompt() or default_user_simulator_system_prompt

                result = interaction.to_result(
                    skipped=has_failed,
                    client=self.get_client(),
                    model_name=self.model_name(),
                    prompt=prompt,
                    handle_message=self.handle_message,
                    messages=self.messages,
                    next_chatbot_message=self._maybe_get_next_chatbot_message(),
                )
                interaction_results.append(result)

                if result.status == InteractionResultStatus.Passed and result.user_message:
                    self._add_message(Role.User, result.user_message)
                    if result.chatbot_response:
                        self._add_message(Role.Chatbot, result.chatbot_response)
                elif result.user_message:
                    self._add_message(Role.User, result.user_message)

                generation_time = time.time() - generation_start_time
                testing_time += generation_time

            elif isinstance(interaction, ChatbotResponds):
                generation_start_time = time.time()

                result = interaction.to_result(
                    adapter=self,
                    messages=self.messages,
                    chatbot_response=self._maybe_get_next_chatbot_message(),
                    skipped=has_failed,
                )
                testing_time += time.time() - generation_start_time

                interaction_results.append(result)

            elif isinstance(interaction, ChatbotIgnoresMessage):
                next_message = self._maybe_get_next_chatbot_message()
                result = interaction.to_result(next_message=next_message)
                interaction_results.append(result)

            has_failed = has_failed or interaction_results[-1].status != InteractionResultStatus.Passed

        return Result(
            conversation_id=conversation.id,
            version_id=conversation.version_id,
            title=conversation.title,
            messages=self.messages,
            failed=has_failed,
            interaction_results=interaction_results,
            testing_time_ms=round(testing_time * 1000),
            chatbot_time_ms=round((time.time() - start_time - testing_time) * 1000),
        )

    def _maybe_get_next_chatbot_message(self):
        try:
            return self.queue.get_nowait()
        except Empty:
            return None

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
