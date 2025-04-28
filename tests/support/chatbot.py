class MathChatbot:
    def handle_message(self, user: str | None, message: str):
        if self.is_greeting(message):
            response = "Hello there."

            if user:
                response = f"Hi {user}."

            return f"{response} My name is credence"

        elif self.is_math_question(message):
            # Only registered users can ask math questions
            if user:
                message = message.removeprefix("math:")
                return str(eval(message))
            else:
                return

        else:
            return None

    def is_greeting(self, message):
        return "Hi" in message or "Hello" in message

    def is_math_question(self, message):
        return message.startswith("math:")
