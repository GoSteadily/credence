import abc
import logging
from queue import Queue
from textwrap import dedent
from typing import Any, Dict, List, Tuple

import instructor
from instructor import Instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel, Field

from credence.result import Message

logger = logging.getLogger(__name__)
"""@private"""

default_checker_system_prompt = "You are quality assurance system that confirms whether the responses given by an assistant meet a requirement.\nDon't be too strict with your analysis. If the response is close to meeting the requirement, then give it a pass."


def _docstring_parameter(*sub):
    def dec(obj):
        obj.__doc__ = obj.__doc__.format(*sub)
        return obj

    return dec


class LLMChecker(abc.ABC):
    """
    `LLMChecker` allows credence to check if a string meets a natural language 
    assertion.

    ---

    In order to create an LLMChecker, you must:

    ```python
    # 1. Import the adapter
    from credence.adapter import LLMChecker

    # 2. Create a subclass of LLMChecker
    class MyLLMChecker(LLMChecker):

        # 3. Define the required `create_client` method
        def create_client(self):
            # Look at instructor's documentation for more
            # integrations - https://python.useinstructor.com/integrations/

            client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

        # 4. Define the required `model_name` method
        def model_name(self):
            return os.environ.get("MODEL_NAME", "gpt-4.1-mini")


    c = MyLLMChecker()

    c.assert_that("Hi there", "is a greeting")
    c.assert_that("Hi there", "is written in English")
    c.assert_that("Hi there", "is not written in French")
    ```
    """

    def __init__(self):
        super().__init__()
        
        self.client: Instructor | None = None
        """@private"""

    @abc.abstractmethod
    def create_client(self) -> Instructor:
        """
        Create an instructor client for your `LLMChecker`

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
        Define the name of the model to be used when running AI checks
        """

    def get_client(self) -> Instructor:
        "@private"
        if self.client is None:
            self.client = self.create_client()

        return self.client

    @_docstring_parameter(default_checker_system_prompt)
    def checker_system_prompt(self) -> str | None:
        """
        By default, credence uses a simple systen prompt to generate user messages:

        ```
        {0}
        ```

        You can override the prompt by overriding the `checker_system_prompt`
        method and returning an alternative prompt.
        """
        return dedent(default_checker_system_prompt).strip()

    def assert_that(self, text: str, assertion: str):
        r = AssertionCheck.check(
            client=self.get_client(),
            model_name=self.model_name(),
            prompt=self.checker_system_prompt() or default_checker_system_prompt,
            text=text,
            assertion=assertion,
        )

        assert r.assertion_is_true, r.reason


class AssertionCheck(BaseModel):
    """
    @private

    The result of analyzing an assertion to check whether the message
    meets the requirements.
    """

    assertion: str = Field(description="The assertion being checked.")
    reason: str = Field(
        description="Explanation for why the response either meets or does not meet the assertion. Should explicitly state whether the assertion was met."
    )
    assertion_is_true: bool = Field(
        description="Whether or not the response meets the assertion.")

    @staticmethod
    def check(
        client: instructor.Instructor,
        model_name: str,
        prompt: str,
        text: str,
        assertion: str,
        # For brittle tests, increase retries to give the LLM
        # multiple chances to mark a requirement as met
        retries: int = 0,
    ) -> "AssertionCheck":
        request_messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=prompt.strip(),
            )
        ]

        request_messages.append(
            ChatCompletionUserMessageParam(
                role="user",
                content=dedent(
                    f"""
                    Message: {text}

                    Is it true that the message {assertion}
                    """
                ).strip(),
            ),
        )

        result: AssertionCheck = client.chat.completions.create(
            model=model_name,
            response_model=AssertionCheck,
            messages=request_messages,
            # If the response is invalid, retry once
            max_retries=1,
        )

        result.assertion = assertion

        if not result.assertion_is_true and retries > 0:
            return AssertionCheck.check_requirement(
                client=client,
                model_name=model_name,
                prompt=prompt,
                text=text,
                assertion=assertion,
                retries=retries - 1,
            )

        return result
