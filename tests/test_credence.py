import os
import tempfile
from pathlib import Path
from typing import List

import instructor
import openai
import pytest
from support.math_chatbot import MathChatbot

from credence.adapter import Adapter, Role
from credence.conversation import Conversation
from credence.step.chatbot import Chatbot
from credence.step.checks.metadata_check import Metadata
from credence.step.checks.response_check import Response
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
        return os.environ.get("MODEL_NAME", "gpt-4.1-nano")

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
                    Response.ai_check(should="greet the user by name", retries=2),
                    Response.ai_check(should="introduce itself as 'credence'", retries=1),
                    Response.contains(string="John"),
                    Response.re_match(regexp="Hi|Hello"),
                    Metadata("chatbot.handler").equals("greeting"),
                    Metadata("chatbot.handler").contains("greet"),
                    Metadata("chatbot.handler").re_match("gre{2}"),
                ]
            ),
        ],
    )

    return [
        user_registration_flow,
        Conversation(
            title="we answer registered user's math questions",
            steps=[
                Conversation.nested(user_registration_flow),
                User.message("math:1 + 1"),
                Chatbot.expect(
                    [
                        Response.equals("2"),
                        Metadata("chatbot.handler").equals("math"),
                        Metadata("chatbot.math.result").equals(2),
                    ]
                ),
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


def require_unique(conversations: List[Conversation]):
    seen = set()
    dupes = set()

    for conversation in conversations:
        if conversation.title in seen:
            dupes.add(conversation.title)
        else:
            seen.add(conversation.title)

    assert len(dupes) == 0, f"Duplicate test names found: {dupes}"
    return conversations


tmpdirname = tempfile.TemporaryDirectory(delete=False)


@pytest.mark.parametrize("conversation", enumerate(require_unique(conversations()), 1))
def test_maa(conversation):
    index, conversation = conversation
    adapter = MathChatbotAdapter()
    # .set_context(a=1, b=2)

    result = adapter.test(conversation)
    Path("/tmp/test_cases").mkdir(parents=True, exist_ok=True)
    with Path(f"tmp/test_cases/{index}. {conversation.title}.case.md").open("w") as f:
        f.write(result.to_markdown(index=index))

    assert result.errors == [], f"Found {len(result.errors)} error(s) when evaluating the test"


def test_checks():
    # RESPONSE
    adapter = MathChatbotAdapter()
    try:
        assert (
            Response.ai_check(should="give a greeting").find_error(
                messages=[
                    (Role.Chatbot, "Hi there"),
                ],
                adapter=adapter,
            )
            is None
        )
        assert (
            Response.ai_check(should="give a greeting").find_error(
                messages=[
                    (Role.Chatbot, "I like fish"),
                ],
                adapter=adapter,
            )
            is not None
        )

    except instructor.exceptions.InstructorRetryException:
        pass

    assert Response.contains(string="bc").find_error("abcd") is None
    assert Response.contains(string="bc").find_error("def") is not None

    assert Response.equals(string="abc").find_error("abc") is None
    assert Response.equals(string="abc").find_error("def") is not None

    assert Response.not_equals(string="abc").find_error("abc") is not None
    assert Response.not_equals(string="abc").find_error("def") is None

    assert Response.re_match("^abc$").find_error("abc") is None
    assert Response.re_match("^abc").find_error("abcd") is None
    assert Response.re_match("^abc$").find_error("abcd") is not None

    # METADATA
    assert Metadata("key").contains(string="bc").find_error("abcd") is None
    assert Metadata("key").contains(string="bc").find_error("def") is not None

    assert Metadata("key").equals(string="abc").find_error("abc") is None
    assert Metadata("key").equals(string="abc").find_error("def") is not None

    assert Metadata("key").not_equals(string="abc").find_error("abc") is not None
    assert Metadata("key").not_equals(string="abc").find_error("def") is None

    assert Metadata("key").re_match("^abc$").find_error("abc") is None
    assert Metadata("key").re_match("^abc").find_error("abcd") is None
    assert Metadata("key").re_match("^abc$").find_error("abcd") is not None

    assert Metadata("key").re_match("^abc$").find_error("abc") is None
    assert Metadata("key").re_match("^abc").find_error("abcd") is None
    assert Metadata("key").re_match("^abc$").find_error("abcd") is not None

    assert Metadata("key").one_of([1, 2, 3]).find_error(1) is None
    assert Metadata("key").one_of([1, 2, 3]).find_error("1") is None


def test_string():
    assert str(Response.ai_check(should="there")) == "Response.ai_check(should='there')"
    assert (
        str(Response.ai_check(should="there", retries=3))
        == """
Response.ai_check(
    should='there',
    retries=3,
)
""".strip()
    )
    assert str(Response.contains(string="there")) == "Response.contains('there')"
    assert str(Response.equals(string="there")) == "Response.equals('there')"
    assert str(Response.re_match("there")) == 'Response.re_match("there")'

    assert str(Metadata("key").equals("there")) == 'Metadata("key").equals("there")'
    assert str(Metadata("key").not_equals("there")) == 'Metadata("key").not_equals("there")'
    assert str(Metadata("key").contains("there")) == 'Metadata("key").contains("there")'
    assert str(Metadata("key").re_match("there")) == 'Metadata("key").re_match("there")'
    assert str(Metadata("key").one_of([1, 2, 3])) == 'Metadata("key").one_of([1, 2, 3])'

    assert str(
        Conversation(
            title="ABC",
            steps=[],
        )
    ) == (
        """
Conversation(
  title="ABC",
  steps=[],
)
""".strip()
    )

    assert str(
        Conversation.nested(
            Conversation(
                title="ABC",
                steps=[],
            ),
        )
    ) == (
        """
Conversation.nested(
  Conversation(
    title="ABC",
    steps=[],
  ),
)
""".strip()
    )

    assert str(
        Conversation.nested(
            Conversation(
                title="ABC",
                steps=[
                    Chatbot.expect(
                        [
                            Response.contains("b\nc"),
                            Response.equals("ab\nc"),
                            Response.ai_check(should="mention \na"),
                            Response.ai_check(should="there", retries=3),
                        ]
                    ),
                ],
            ),
        )
    ) == (
        """
Conversation.nested(
  Conversation(
    title="ABC",
    steps=[
        Chatbot.expect([
            Response.contains('b\\nc'),
            Response.equals('ab\\nc'),
            Response.ai_check(should='mention \\na'),
            Response.ai_check(
                should='there',
                retries=3,
            ),
        ]),
    ],
  ),
)
""".strip()
    )
