import credence


class MathChatbot:
    def handle_message(self, user: str | None, message: str):
        if self.is_greeting(message):
            credence.collect_metadata({"chatbot.handler": "greeting"})
            response = "Hello there."

            if user:
                response = f"Hi {user}."

            return f"{response} My name is credence"

        elif self.is_math_question(message):
            credence.collect_metadata({"chatbot.handler": "math"})
            # Only registered users can ask math questions
            if user:
                message = message.removeprefix("math:")
                result = eval(message)
                credence.collect_metadata({"chatbot.math.result": result})
                return str(result)
            else:
                return

        else:
            return None

    def is_greeting(self, message):
        return "Hi" in message or "Hello" in message

    def is_math_question(self, message):
        return message.startswith("math:")
