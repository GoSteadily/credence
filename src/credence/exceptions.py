class ColoredException(Exception):
    def __init__(self, message: str, colored_message: str, markdown_message: str):
        super().__init__(message)
        self.colored_message = colored_message
        self.markdown_message = markdown_message
