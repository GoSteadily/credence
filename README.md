A chatbot testing library that enables developers to write regression tests for their chatbots.

# Features

<details>
<summary>

  #### 💬 Built around conversations

</summary>

  Users rarely disclose information in one long, perfectly-worded message. Important facts are often shared gradually over the course of a conversation. 
  
  We built credence around conversations to ensure that we could test a chatbot's ability to:
  1. utilize conversational context
  2. handle topic switching
  3. choose the correct agent to handle a message

</details>


<details>
<summary>

  #### 🧪 Designed to allow confident code changes

</summary>

  Conversations are also extremely useful in writing regression tests.
  One of the hardest parts of chatbot development is fixing strange edge cases without introducing new ones.
  With credence, we can represent challenging conversations and the desired chatbot behaviour in code. 
  This allows us to make modifications without worrying that we have reintroduced bugs or completely broken working code.
</details>

<details>
<summary>

  #### 💼 Executed with your tests, embedded in your code

</summary>


  credence runs as part of your test suite using your existing LLM provider.
  No new integrations, no external services, just one more set of tests that run locally or in CI.

  Because credence is just some more code in your test suite, it has access to all your business logic.
  Need to test how you chatbot behaves after a user makes a payment, directly call your functions to create the user and simulate the payment.
</details>

<details>
<summary>

  #### ✅ AI Checks

</summary>
  
  Enforce high-level behaviour with AI checks.
  When using LLMs, you never know exactly what your chatbot will spit out.
  AI checks allow you to enforce high-level expectations on responses. 
  
  Want to test your customer support chatbot's response to angry users? 
  You can check that the chatbot "apologizes for the inconvenience with a diplomatic tone".
</details>

<details>
<summary>

  #### 🤸‍♀️ Extremely flexible

</summary>
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

# Quick Start

## Requirements
- [pytest](https://docs.pytest.org/en/stable/): The credence documentation assumes that you are using pytest for testing. We don't use pytest within the library, so other testing frameworks *should* work.
- LLM Integration: credence is a "bring your own LLM" library. If you want to make use of any AI features, you will need a [supported provider](https://python.useinstructor.com/integrations/). This should just work for most use cases.

## Installation

```bash
uv add git+https://github.com/GoSteadily/credence --tag 0.1.8
```

## Setup some tests

1. Setup an

## Parallelizing test execution
pytest -n auto -s -o log_cli=true

## Parallelizing test execution

If your chatbot uses an LLM or you are using `User.generated` or `Response.ai_check`, each test may take a few seconds. To speed up your tests, consider using [pytest-xdist](https://pytest-xdist.readthedocs.io/en/stable/) to parallelize test execution.

To run parallel test use `pytest -n auto -s -o log_cli=true` from your terminal.



# Usage Examples

## External interactions

## Nesting conversations

## Customizing the user prompt

## Test the right level

# API Documentation

Complete documentation can be found at: https://gosteadily.github.io/credence/credence.html

---

# Licensing

# Contributing

# Contact

# Steadily Consulting
