import logging
import os
from typing import List, Tuple

import instructor
import openai
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
        messages,
        requirement: str,
    ):
        from credence.adapter import Role

        messages: List[Tuple[Role, str]] = messages

        chat_log = ""
        for role, message in messages:
            chat_log = chat_log + f"{role.value}: {message}\n"
        request_messages = [
            {
                "role": "system",
                "content": """
                    You are quality assurance system that confirms whether the answers given to a specific question meet some requirements.
                    """.strip(),
            },
            {
                "role": "user",
                "content": f"""
                    This is the chatbot log:

                    {chat_log}
                    """.strip(),
            },
            {
                "role": "user",
                "content": f"""
                    Do the chatbot responses match the following criteria:

                    {requirement}
                    """.strip(),
            },
        ]

        if os.environ.get("TOGETHER_API_KEY"):
            client = openai.OpenAI(
                base_url="https://api.together.xyz/v1",
                api_key=os.environ["TOGETHER_API_KEY"],
            )
        else:
            client = openai.OpenAI(
                # base_url="https://api.together.xyz/v1",
                api_key=os.environ["OPENAI_API_KEY"],
            )

        # By default, the patch function will patch the ChatCompletion.create and ChatCompletion.create methods to support the response_model parameter
        client = instructor.from_openai(client, mode=instructor.Mode.TOOLS)

        result: ContentTestResult = client.chat.completions.create(
            model=os.environ["MODEL_NAME"],
            response_model=ContentTestResult,
            messages=request_messages,
        )

        logger.debug(result)

        return result
