import os

import instructor
import openai
import pytest
from support.chatbot import MathChatbot

from credence.adapter import Adapter
from credence.conversation import Conversation
from credence.step import Step
from credence.step.chatbot import Chatbot, Response
from credence.step.execute import Execute
from credence.step.user import User


class MathChatbotAdapter(Adapter):
    def __init__(self):
        super().__init__()
        self.chatbot = MathChatbot()

    def handle_message(self, message: str):
        user = self.context.get("user")
        return self.chatbot.handle_message(user=user, message=message)

    def create_client(self):
        client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )

        return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

    def model_name(self):
        return os.environ["MODEL_NAME"]

    def register_user(self, name: str):
        self.add_to_context("user", name)


def conversations():
    user_registration_flow = Conversation(
        title="we greet registered users by name",
        steps=[
            Execute("register_user", {"name": "John"}),
            User.generated("Say hello and introduce yourself as John"),
            Chatbot.expect(
                [
                    Response.ai_check(should="respond with user's name John and introduce itself as 'credence'"),
                    Response.contains(string="John"),
                    Response.re_match(regexp="Hi|Hello"),
                ]
            ),
        ],
    )

    return [
        user_registration_flow,
        Conversation(
            title="we answer registered user's math questions",
            steps=[
                Step.nested_conversation(user_registration_flow),
                User.message("math:1 + 1"),
                Chatbot.expect([Response.equals("2")]),
            ],
        ),
        Conversation(
            title="we greet unknown users generically",
            steps=[
                User.message("Hello, I'm John"),
                Chatbot.expect(
                    [
                        Response.contains(string="there"),
                        Response.re_match(regexp="Hi|Hello"),
                    ]
                ),
            ],
        ),
        Conversation(
            title="we ignore unknown users' math questions",
            steps=[
                User.message("math:1 + 1"),
                Chatbot.ignores_mesage(),
            ],
        ),
    ]


@pytest.mark.parametrize("conversation", conversations())
def test_maa(conversation):
    result = MathChatbotAdapter().set_context().test(conversation)

    result.print()
    assert result.errors == []
