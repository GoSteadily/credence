import copy
import logging
import traceback
from dataclasses import dataclass
from textwrap import dedent
from typing import List

import instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel, Field
from termcolor import colored

from credence.exceptions import ColoredException
from credence.interaction.chatbot.check.base import BaseCheckResult, BaseCheckResultStatus
from credence.interaction.chatbot.check.response import ChatbotResponseCheck
from credence.message import Message

logger = logging.getLogger(__name__)
"""@private"""


@dataclass(kw_only=True)
class ChatbotResponseAICheck(ChatbotResponseCheck):
    """
    @private
    """

    prompt: str
    # Increase the number of retries for brittle tests
    retries: int = 0
    type: str = "ai_check"

    def __str__(self):
        if self.retries > 0:
            return f"""Response.ai_check(
    should={str_repr(self.prompt)},
    retries={self.retries},
)""".strip()
        else:
            return f"Response.ai_check(should={str_repr(self.prompt)})"

    def humanize(self):
        return f"should {self.prompt}"

    def to_check_result(self, messages: List[Message], adapter, skipped: bool = False):
        if skipped:
            return self.skipped()

        from credence.adapter import Adapter

        if not isinstance(adapter, Adapter):
            return self.failed(invalid_adapter_error=f"{adapter} is not a valid Adapter")

        try:
            result = AIContentCheck.check_requirement(
                client=adapter.get_client(),
                model_name=adapter.model_name(),
                messages=messages,
                requirement=self.prompt,
            )
        except Exception:
            trace = str(traceback.format_exc())
            return self.failed(generation_error=f"{trace[-3000:]}")

        if result.requirement_met:
            return self.passed()
        else:
            return self.failed(unmet_requirement=result.reason)

    def passed(self):
        return ChatbotResponseAICheckResult(
            status=BaseCheckResultStatus.Passed,
            data=copy.deepcopy(self),
        )

    def failed(self, invalid_adapter_error: str | None = None, generation_error: str | None = None, unmet_requirement: str | None = None):
        return ChatbotResponseAICheckResult(
            status=BaseCheckResultStatus.Failed,
            data=copy.deepcopy(self),
            invalid_adapter_error=invalid_adapter_error,
            generation_error=generation_error,
            unmet_requirement=unmet_requirement,
        )

    def skipped(self):
        return ChatbotResponseAICheckResult(
            status=BaseCheckResultStatus.Skipped,
            data=copy.deepcopy(self),
        )


@dataclass(kw_only=True)
class ChatbotResponseAICheckResult(BaseCheckResult):
    data: ChatbotResponseAICheck
    status: BaseCheckResultStatus
    invalid_adapter_error: str | None = None
    generation_error: str | None = None
    unmet_requirement: str | None = None
    type: str = "ai_check"

    def generate_error_messages(self):
        if self.invalid_adapter_error:
            return [f"Invalid Adapter Error:\n{self.invalid_adapter_error}"]

        if self.generation_error:
            return [f"Error while generating response:\n{self.generation_error}"]

        if self.unmet_requirement:
            return [f"Requirement not met:\n{self.unmet_requirement}"]

        return []


class AIContentCheck(BaseModel):
    """
    @private

    The result of analyzing a single requirement to check whether the chatbot
    response given to the user message meets the requirements.
    """

    requirement: str = Field(description="The requirement being checked.")
    reason: str = Field(
        description="Explanation for why the response either meets or does not meet the requirement. Should explicitly state whether the requirement was met."
    )
    requirement_met: bool = Field(description="Whether or not the response meets the requirements.")

    @staticmethod
    def check_requirement(
        client: instructor.Instructor,
        model_name: str,
        messages: List[Message],
        requirement: str,
        # For brittle tests, increase retries to give the LLM
        # multiple chances to mark a requirement as met
        retries: int = 0,
    ) -> "AIContentCheck":
        request_messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="""
                    You are quality assurance system that confirms whether the responses given by an assistant meet a requirement.
                    Don't be too strict with your analysis. If the response is close to meeting the requirement, then give it a pass.
                    """.strip(),
            )
        ]

        if messages:
            chat_log = ""
            for message in messages:
                chat_log = chat_log + f"{message.role.value}: {message.body}\n"

            request_messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"""
                    This is the chatbot log:

                    {chat_log}
                    """.strip(),
                )
            )

        request_messages.append(
            ChatCompletionUserMessageParam(
                role="user",
                content=dedent(
                    f"""
                    Does the assistant's response meet the following requirement:

                    The assistant should {requirement}
                    """
                ).strip(),
            ),
        )

        result: AIContentCheck = client.chat.completions.create(
            model=model_name,
            response_model=AIContentCheck,
            messages=request_messages,
            # If the response is invalid, retry once
            max_retries=1,
        )

        result.requirement = requirement

        # print("request_messages",request_messages)
        # print(result)
        if not result.requirement_met and retries > 0:
            return AIContentCheck.check_requirement(
                client=client,
                model_name=model_name,
                messages=messages,
                requirement=requirement,
                retries=retries - 1,
            )

        return result

    def generate_error(self, chatbot_response: tuple[int, str]):
        if not self.requirement_met:
            return ColoredException(
                chatbot_response[0],
                self._exception_message(
                    chatbot_response=chatbot_response[1],
                    colorize=False,
                ),
                self._exception_message(
                    chatbot_response=chatbot_response[1],
                    colorize=True,
                ),
                self._exception_message(
                    chatbot_response=chatbot_response[1],
                    colorize=False,
                    markdown=True,
                ),
            )

    def _exception_message(self, chatbot_response: str, colorize: bool, markdown: bool = False):
        if markdown:
            return (
                f"chatbot response did not pass AI check:\n"
                f"| **requirement** | The chatbot should {self.requirement} |\n"
                f"| --------------- | ------------------------------------- |\n"
                f"|    **response** | {chatbot_response}                    |\n"
                f"|      **passed** | `False`                               |\n"
                f"|      **reason** | {self.reason}                         |\n"
            )
        else:
            return (
                f"chatbot response did not pass AI check:\n"
                f"{maybe_colored(colorize, 'requirement', attrs=['bold'])}: {self.requirement}\n"
                f"{maybe_colored(colorize, '   response', attrs=['bold'])}: {chatbot_response}\n"
                f"{maybe_colored(colorize, '     passed', attrs=['bold'])}: False\n"
                f"{maybe_colored(colorize, '     reason', attrs=['bold'])}: {self.reason}\n"
            )


def maybe_colored(colorize: bool, str, **kwargs):
    """
    @private
    """
    if colorize:
        return colored(str, **kwargs)
    else:
        return str


def str_repr(string: str):
    """
    @private
    """
    return f"{string.__repr__()}"
