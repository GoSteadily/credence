class ColoredException(Exception):
    """@private"""

    def __init__(self, index: int, message: str, colored_message: str, markdown_message: str):
        super().__init__(message)
        self.index = index
        self.colored_message = colored_message
        self.markdown_message = markdown_message


class ChatbotIndexedException(Exception):
    """@private"""

    def __init__(self, index: int, message: str):
        super().__init__(message)
        self.index = index
