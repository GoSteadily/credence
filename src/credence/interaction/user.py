from dataclasses import dataclass

from credence.interaction import Interaction


@dataclass
class UserMessage(Interaction):
    """@private"""

    text: str


@dataclass
class UserGenerated(Interaction):
    """@private"""

    prompt: str


class User(Interaction):
    """
    `User` interactions allow us to simulate a user sending messages
    to the chatbot.
    """

    @staticmethod
    def message(text: str):
        """
        Send a specific text message to the chatbot.
        """
        return UserMessage(text=text)

    @staticmethod
    def generated(prompt: str):
        """
        Send an ai-generated text message to the chatbot based on a prompt.
        """
        return UserGenerated(prompt=prompt)
