import os
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import List, Tuple

import instructor
import openai
import pytest
from credence.checker import LLMChecker
from support.math_chatbot import MathChatbot

from credence.adapter import Adapter, Role
from credence.conversation import Conversation
from credence.interaction.chatbot import Chatbot
from credence.interaction.chatbot.check.metadata import Metadata
from credence.interaction.chatbot.check.response import Response
from credence.interaction.external import External
from credence.interaction.user import User
from credence.message import Message


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
        return os.environ.get("MODEL_NAME", "gpt-4.1-mini")

    def user_simulator_system_prompt(self):
        return dedent("""
            You are now simulating a user who is interacting with a system.
            You can only speak in seven word sentences.
            """).strip()

    def register_user(self, name: str):
        self.context["user"] = name


class MyLLMChecker(LLMChecker):
    def create_client(self):
        client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )

        return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

    def model_name(self):
        return os.environ.get("MODEL_NAME", "gpt-4.1-mini")


def conversations():
    user_registration_flow = Conversation(
        title="we greet registered users by name",
        interactions=[
            External("register_user", {"name": "John"}),
            User.generated("Say hello and introduce yourself as John"),
            Chatbot.responds(
                [
                    Response.ai_check(
                        should="greet the user using his name - John", retries=2),
                    Response.ai_check(should="introduce itself as Credence", retries=1),
                    Response.contains(string="John"),
                    Response.re_match(regexp="Hi|Hello"),
                    Metadata("chatbot.handler").equals("greeting"),
                    Metadata("chatbot.handler").contains("greet"),
                    Metadata("chatbot.handler").re_match("gre{2}"),
                ]
            ),
        ],
    )

    failing_test = Conversation(
        title="Failing test",
        interactions=[
            External("register_user", {"name": "John"}),
            User.generated("Say hello and introduce yourself as John"),
            Chatbot.responds(
                [
                    Response.ai_check(should="offer the user a discount"),
                    Response.contains(string="Steve"),
                    Response.re_match(regexp="Random"),
                    Metadata("chatbot.handler").equals("greeting"),
                    Metadata("chatbot.handler").equals("gree"),
                    Metadata("chatbot.handler").contains("fail"),
                    Metadata("chatbot.handler").re_match("fail{2}"),
                ]
            ),
        ],
    )

    failing_test2 = Conversation(
        title="Failing test 2",
        interactions=[
            External("register_user", {"name": "John"}),
            User.generated("Say hello and introduce yourself as John"),
            Chatbot.responds(
                [
                    Metadata("unknown metadata").re_match("fail{2}"),
                ]
            ),
        ],
    )

    return [
        (False, failing_test),
        (False, failing_test2),
        (True, user_registration_flow),
        (
            True,
            Conversation(
                title="we answer registered user's math questions",
                interactions=[
                    Conversation.nested("User Registration Flow",
                                        user_registration_flow),
                    User.message("math:1 + 1"),
                    Chatbot.responds(
                        [
                            Response.equals("2"),
                            Metadata("chatbot.handler").equals("math"),
                            Metadata("chatbot.math.result").equals(2),
                        ]
                    ),
                ],
            ),
        ),
        (
            True,
            Conversation(
                title="we greet unknown users generically",
                interactions=[
                    User.message("Hello, I'm John"),
                    Chatbot.responds(
                        [
                            Response.contains(string="there"),
                            Response.re_match(regexp="Hi|Hello"),
                        ]
                    ),
                ],
            ),
        ),
        (
            True,
            Conversation(
                title="we ignore unknown users' math questions",
                interactions=[
                    User.message("math:1 + 1"),
                    Chatbot.ignores_mesage(),
                ],
            ),
        ),
    ]


def require_unique(conversations: List[Tuple[int, Conversation]]):
    seen = set()
    dupes = set()

    for _, conversation in conversations:
        if conversation.title in seen:
            dupes.add(conversation.title)
        else:
            seen.add(conversation.title)

    assert len(dupes) == 0, f"Duplicate test names found: {dupes}"
    return conversations


tmpdirname = tempfile.TemporaryDirectory(delete=False)


conversation_count = len(conversations())


def index_str(index):
    chars = len(str(conversation_count))
    return str(index).rjust(chars, "0")


@pytest.mark.parametrize("conversation", enumerate(require_unique(conversations()), 1))
def test_maa(conversation):
    index, (should_pass, conversation) = conversation
    adapter = MathChatbotAdapter()

    result = adapter.test(conversation)
    result.to_stdout()
    Path("tmp/test_cases").mkdir(parents=True, exist_ok=True)
    passed = "p" if result.errors == [] else "f"

    with Path(f"tmp/test_cases/{index_str(index)}. {conversation.title}.{passed}.case.md").open("w") as f:
        f.write(result.to_markdown(index=index))

    if should_pass:
        assert result.errors == [
        ], f"Found {len(result.errors)} error(s) when evaluating the test"
    else:
        assert result.errors != [
        ], "Found 0 error(s) when evaluating a test that should fail"


def test_assert_that():
    c = MyLLMChecker()

    c.assert_that("Hi there", "is a greeting")
    c.assert_that("Hi there", "is written in English")
    c.assert_that("Hi there", "is not written in French")
    
    with pytest.raises(AssertionError):
        c.assert_that("Hi there", "is written in French")
    
    with pytest.raises(AssertionError):
        c.assert_that("Salut", "is written in English")

    with pytest.raises(AssertionError):
        c.assert_that("1 + 1 = 4", "is mathematically correct")




def test_checks():
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

    # RESPONSE

    assert Response.contains(string="bc").find_error((0, "abcd")) is None
    assert Response.contains(string="bc").find_error((0, "def")) is not None

    assert Response.equals(string="abc").find_error((0, "abc")) is None
    assert Response.equals(string="abc").find_error((0, "def")) is not None

    assert Response.not_equals(string="abc").find_error((0, "abc")) is not None
    assert Response.not_equals(string="abc").find_error((0, "def")) is None

    assert Response.re_match("^abc$").find_error((0, "abc")) is None
    assert Response.re_match("^abc").find_error((0, "abcd")) is None
    assert Response.re_match("^abc$").find_error((0, "abcd")) is not None

    adapter = MathChatbotAdapter()
    try:
        assert (
            Response.ai_check(should="give a greeting").find_error(
                messages=[Message(role=Role.Chatbot, body="Hi there")],
                adapter=adapter,
            )
            is None
        )
        assert (
            Response.ai_check(should="give a greeting").find_error(
                messages=[Message(role=Role.Chatbot, body="I like fish")],
                adapter=adapter,
            )
            is not None
        )

    except instructor.exceptions.InstructorRetryException:
        pass


def test_string_encoding():
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
    assert str(Metadata("key").not_equals("there")
               ) == 'Metadata("key").not_equals("there")'
    assert str(Metadata("key").contains("there")) == 'Metadata("key").contains("there")'
    assert str(Metadata("key").re_match("there")) == 'Metadata("key").re_match("there")'
    assert str(Metadata("key").one_of([1, 2, 3])) == 'Metadata("key").one_of([1, 2, 3])'

    assert str(External("register_user", {"name": "John"})
               ) == "External('register_user', {'name': 'John'})"
    assert str(External("register_user", {})) == "External('register_user')"

    assert str(
        Conversation(
            title="ABC",
            interactions=[],
        )
    ) == (
        """
Conversation(
  title="ABC",
  interactions=[],
)
""".strip()
    )

    assert str(
        Conversation.nested(
            "Name",
            Conversation(
                title="ABC",
                interactions=[],
            ),
        )
    ) == (
        """
Conversation.nested(
  'Name',
  Conversation(
    title="ABC",
    interactions=[],
  ),
)
""".strip()
    )

    assert str(
        Conversation.nested(
            "ABC Flow",
            Conversation(
                title="ABC",
                interactions=[
                    Chatbot.responds(
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
  'ABC Flow',
  Conversation(
    title="ABC",
    interactions=[
        Chatbot.responds([
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
