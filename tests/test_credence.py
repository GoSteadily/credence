import os

import instructor
import openai

from credence.adapter import Adapter
from credence.conversation import Conversation
from credence.step.chatbot import Chatbot
from credence.step.execute import Execute
from credence.step.user import User


class TestChatbotAdapter(Adapter):
    __test__ = False

    def handle_message(self, message: str):
        if "Hi" in message or "Hello" in message:
            greeting = "Hello there."

            if self.context.get("name"):
                greeting = f"Hi {self.context['name']}."

            return f"{greeting} I am credence"
        else:
            return None

    def create_client(self):
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

        return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

    def model_name(self):
        return os.environ["MODEL_NAME"]

    def enrol_user(self, name: str):
        self.add_to_context("name", name)


def test_maa():
    for conversation in conversations():
        (
            TestChatbotAdapter()
            #
            .set_context()
            .test(conversation)
            .print()
        )


def conversations():
    return [
        Conversation(
            title="registered user sends messages",
            steps=[
                Execute("enrol_user", {"name": "John"}),
                # User.message("Hello"),
                User.generated("Say hello and introduce yourself as John"),
                Chatbot.expect(
                    [
                        Chatbot.ai_check(should="respond with user's name John and introduce itself as credence"),
                        Chatbot.contains(string="John"),
                        Chatbot.re_match(regexp="Hi|Hello"),
                    ]
                ),
            ],
        ),
        Conversation(
            title="unknown user sends messages",
            steps=[
                User.message("Hello, I'm Nduati"),
                Chatbot.expect(
                    [
                        Chatbot.contains(string="there"),
                        Chatbot.re_match(regexp="Hi|Hello"),
                    ]
                ),
            ],
        ),
    ]
