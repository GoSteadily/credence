import logging
from enum import Enum

from openai.types.chat import ChatCompletionAssistantMessageParam, ChatCompletionUserMessageParam

"""@private"""

logger = logging.getLogger(__name__)
"""@private"""


class Role(str, Enum):
    """@private"""

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
