import os

import instructor
import openai
import pytest

from credence.adapter import Adapter
from credence.conversation import Conversation
from credence.step.chatbot import Chatbot, Response
from credence.step.execute import Execute
from credence.step.user import User


class TestChatbotAdapter(Adapter):
    __test__ = False

    def handle_message(self, message: str):
        if "Hi" in message or "Hello" in message:
            greeting = "Hello there."

            if self.context.get("name"):
                greeting = f"Hi {self.context['name']}."

            return f"{greeting} My name is credence"
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
                        Response.ai_check(should="respond with user's name John and introduce itself as 'credence'"),
                        Response.contains(string="John"),
                        Response.re_match(regexp="Hi|Hello"),
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
                        Response.contains(string="there"),
                        Response.re_match(regexp="Hi|Hello"),
                    ]
                ),
            ],
        ),
    ]


@pytest.mark.parametrize("conversation", conversations())
def test_maa(conversation):
    result = TestChatbotAdapter().set_context().test(conversation)

    result.print()
    assert result.errors == []
