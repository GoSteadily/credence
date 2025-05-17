import abc


class Interaction(abc.ABC):
    """"""

    @abc.abstractmethod
    def is_user_interaction(self) -> bool:
        "@private"

    @abc.abstractmethod
    def is_chatbot_interaction(self) -> bool:
        "@private"
