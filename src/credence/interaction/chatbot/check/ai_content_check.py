import logging
from textwrap import dedent
from typing import List

import instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel, Field
from termcolor import colored

from credence.exceptions import ColoredException
from credence.message import Message

"""@private"""


logger = logging.getLogger(__name__)
"""@private"""


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
                f"chatbot response did not pass AI check:<br>\n\n"
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
