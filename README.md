A chatbot testing library that enables developers to write regression tests for their chatbots.

---

# Features

<details>
<summary><h5 style="display: inline;">💬 Built around conversations</h5></summary>

Users rarely disclose information in one long, perfectly-worded message. Important facts are often shared gradually over the course of a conversation.

We built credence around conversations to ensure that we could test a chatbot's ability to:

1. utilize conversational context
2. handle topic switching
3. choose the correct agent to handle a message

</details>

<details>
<summary><h5 style="display: inline;">🔄 Designed to allow confident code changes</h5></summary>

One of the hardest parts of chatbot development is fixing strange edge cases without introducing new ones.

With credence, we can represent challenging conversations and the desired chatbot behaviour in code.
This allows us to make modifications without worrying that we have reintroduced bugs or completely broken working code.

</details>

<details>
<summary><h5 style="display: inline;">🪹 Executed with your tests, embedded in your code</h5></summary>

credence runs as part of your test suite using your existing LLM provider.
No new integrations, no external services, just one more set of tests that run locally or in CI.

Because credence is just some more code in your test suite, it has access to all your business logic.
Need to test how you chatbot behaves after a user makes a payment, directly call your functions to create the user and simulate the payment.

</details>

<details>
<summary><h5 style="display: inline;">👀 AI Checks</h5></summary>

Enforce high-level behaviour with AI checks.
When using LLMs, you never know exactly what your chatbot will spit out.
AI checks allow you to enforce high-level expectations on responses.

Want to test your customer support chatbot's response to angry users?
You can check that the chatbot "apologizes for the inconvenience with a diplomatic tone".

</details>

<details>

<summary><h5 style="display: inline;">🤸‍♀️ Extremely flexible</h5></summary>

Our metadata system allows you to collect information from anywhere in your chatbot and make assertions in your tests.

This is extremely useful when testing branching code.
Want to test that the correct agent is handling a specific message:

```python
# Inside your chatbot's agent routing code
agent = choose_agent(...)
credence.collect_metadata({"router.agent": agent})

# Inside your conversation, you can assert that
Metadata("router.agent").equals(Agent.XYZ)
```

</details>

<br>

---

# Quick Start

## Requirements

- [pytest](https://docs.pytest.org/en/stable/): The credence documentation assumes that you are using pytest for testing. We don't use pytest within the library, so other testing frameworks _should_ work.
- LLM Integration: credence is a "bring your own LLM" library. If you want to make use of any AI features, you will need a [supported provider](https://python.useinstructor.com/integrations/). This should just work for most use cases.

## Installation

```bash
uv add git+https://github.com/GoSteadily/credence --tag 0.1.8
```

## Create an adapter

```python
# Inside your tests folder eg in chatbot_test.py
import instructor
import openai
import pytest

# Let's assume you have a chatbot module that 
# exposes a process_message function
from my_app import chatbot

from credence.adapter import Adapter
from credence.conversation import Conversation
from credence.interaction.chatbot import Chatbot
from credence.interaction.chatbot.check.response import Response
from credence.interaction.external import External
from credence.interaction.user import User


class MyChatbotAdapter(Adapter):
    def create_client(self):
        # Look at instructor's documentation for more
        # integrations - https://python.useinstructor.com/integrations/

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        return instructor.from_openai(client, mode=instructor.Mode.TOOLS)

    def model_name(self):
        return os.environ.get("MODEL_NAME", "gpt-4.1-mini")

    def handle_message(self, message: str) -> str | None:
        # If your chatbot dispatches responses instead of returning 
        # a string, look at `Adapter.handle_message`'s documentation
        return chatbot.process_message(message)
```

> [!NOTE]
> credence works best when used for integration tests.
> 
> If you have an endpoint function that receives messages from a provider, then your `handle_message` function should mirror that function.
> For example, if this is how you handle messages from a provider like twilio:
> ```python
> @app.post("/webhook/twilio/sms")
> def handle_twilio_sms():
>     incoming_message: ParsedMessage = parse_webhook_message(request=request)
>     return chatbot.handle_webhook_message(incoming_message)
> ```
>
> then your handle_message function should be fairly similar:
> ```python
> class MyChatbotAdapter(Adapter):
>   ...
>   
>   def handle_message(self, message: str) -> str | None:
>       incoming_message = ParsedMessage(
>         body=message, 
>         phone_number=self.context["phone_number"], 
>       )
>       return chatbot.handle_webhook_message(incoming_message)
> ```


## Create a conversation

```python
# Inside your test file
class MyChatbotAdapter(Adapter):
    ...

def conversations():
    return [
        Conversation(
            title: "adapter works",
            interactions: [
                User.message("Hi"),
                # Let's only assert that the chatbot responds for now
                Chatbot.responds([]),
            ]
        )
    ]
```

## Test the conversation

```python
# Inside your test file

class MyChatbotAdapter(Adapter):
    ...

def conversations():
    ...

# Run each conversation as a separate test
@pytest.mark.parametrize("conversation", conversations())
def test_chatbot(conversation):
    result = MyChatbotAdapter().test(conversation)

    # To see logs, run `pytest -s`
    result.to_stdout()
    assert result.errors == [], f"Found {len(result.errors)} error(s) when evaluating the test"
```

## Parallelizing test execution

If your chatbot uses an LLM or you are using `User.generated` or `Response.ai_check`, each test may take a few seconds. To speed up your tests, consider using [pytest-xdist](https://pytest-xdist.readthedocs.io/en/stable/) to parallelize test execution.

To run parallel test use `pytest -n auto -s` from your terminal.

---

# Usage Examples

## External interactions / Escape hatches

A conversation might depend on some external interactions.
For example, a user may need to be registered before they can interact with the chatbot. You can use `External` interactions to run arbitrary code at any point in a conversation:


```python
from credence.adapter import Adapter

class MyChatbotAdapter(Adapter):

    
    def handle_message(self, message: str) -> str | None:
        user: User = my_app.fetch_user(self.context["phone_number"])
        return my_app.chatbot.process_message(user, message)

    # Define a custom function in your adapter
    def register_and_upgrade(self, name: str, phone_number: str):
        self.context["user"] = name
        user: User = my_app.register_user(name, phone_number)
        my_app.upgrade_user(user)

# Use the register_and_upgrade function in a conversation
conversation = Conversation(
        title: "Paid users have access to premium flow",
        interactions: [
            External("register_and_upgrade", {
                "user": "John",
                "phone_number": "+12345678901",
            }),
            User.message("Hi"),
            ...
        ],
    )
```


## Nesting conversations

In some cases, your chatbot has an often repeated interaction. For example, the user must always agree to terms of service
before using the chatbot. To avoid repeating this flow several times,
we create a conversation for this flow and reuse it in other conversations.

```python
agree_to_tos_conversation = Conversation(
    title="new user must agree to TOS",
    interactions=[
        User.message("Hi"),
        Chatbot.responds([Response.equals("Hi. Do you agree to our terms of service?")]),
        Chatbot.responds([Response.equals("Yes")]),
        Chatbot.responds([Response.equals("Welcome aboard")]),
    ],
)

london_weather_conversation = Conversation(
    title="chatbot can answer weather related questions",
    interactions=[
        # Reuse the agree_to_tos_conversation
        Conversation.nested(agree_to_tos_conversation),
        User.message("What is the weather in London?"),
        Chatbot.responds([Response.equals("It is drizzling.")]),
    ],
)

ambiguous_location_conversation = Conversation(
    title="chatbot asks for extra information when asked ambiguous weather related questions",
    interactions=[
        # Reuse the agree_to_tos_conversation
        Conversation.nested(agree_to_tos_conversation),
        User.message("What is the weather?"),
        Chatbot.responds([Response.equals("Which city are you interested in?")]),
    ],
)
```

## User Profiles: Customizing the user prompt
We provide a fairly simple prompt for user message generation. For more elaborate use cases, such as when supporting different user profiles, you can override the prompt using `credence.adapter.Adapter.user_simulator_system_prompt`.

For example, if you were testing your chatbot's ability to escalate angry users 
to a human customer service agent, you might want to support an "angry user" profile.

```python
class MyChatbotAdapter(Adapter):
    ...

    def user_simulator_system_prompt(self):
        match self.context.get("profile"):
            case "angry":
                return (
                    "You are angry customer who is frustrated about a recent product purchase. "
                    "Make sure to repeatedly express your irritation with the customer service."
                )
            case _:
                # Use the default prompt
                return None

```

# API Documentation

Complete documentation can be found at: https://gosteadily.github.io/credence/credence.html

---

# Licensing

# Contributing

# Contact

# Steadily Consulting
