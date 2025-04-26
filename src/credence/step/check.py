import logging
from typing import Any, List, Tuple

import instructor
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContentTestResult(BaseModel):
    """
    The result of analyzing a single requirement to check whether the chatbot
    response given to the user message meets the requirements.
    """

    requirement: str = Field(description="The requirement being checked.")
    reason: str = Field(description="The reason why the response either meets or does not meet the requirement.")
    was_met: bool = Field(description="Whether or not the response meets the requirements.")

    @staticmethod
    def check_requirement(
        client: instructor.Instructor,
        model_name: str,
        messages: List[Tuple[Any, str]],
        requirement: str,
    ):
        from credence.adapter import Role

        chat_log = ""
        for _role, message in messages:
            role: Role = _role
            chat_log = chat_log + f"{role.value}: {message}\n"
        request_messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="""
                    You are quality assurance system that confirms whether the answers given to a specific question meet some requirements.
                    """.strip(),
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"""
                    This is the chatbot log:

                    {chat_log}
                    """.strip(),
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"""
                    Do the chatbot responses match the following criteria:

                    {requirement}
                    """.strip(),
            ),
        ]

        result: ContentTestResult = client.chat.completions.create(
            model=model_name,
            response_model=ContentTestResult,
            messages=request_messages,
        )

        logger.debug(result)

        return result
