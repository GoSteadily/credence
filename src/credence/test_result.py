from dataclasses import dataclass
import itertools
from typing import Any, List

from termcolor import cprint

from credence.conversation import Conversation
from credence.exceptions import ColoredException
from credence.interaction.chatbot import ChatbotResponds
from credence.interaction.nested_conversation import NestedConversation
from credence.message import Message
from credence.role import Role


@dataclass
class TestResult:
    messages: List[Message]
    errors: List[Any]
    conversation: Conversation
    chatbot_time_ms: int
    testing_time_ms: int

    def to_stdout(self):
        cprint("")
        cprint("------------ TestResult ------------", attrs=["bold"])
        cprint(self.conversation.title)
        cprint("------------------------------------")
        cprint(
            f"  Total Time:  {(self.chatbot_time_ms + self.testing_time_ms) / 1000}s")
        cprint(f"   Test Time:  {self.testing_time_ms / 1000}s")
        cprint(f"Chatbot Time:  {self.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for message in self.messages:
            if message.role == Role.User:
                color = "blue"
                name = "user: "
            if message.role == Role.Chatbot:
                color = "green"
                name = "asst: "

            cprint(name, color, attrs=["bold"], end="")
            cprint(message.body)

        if self.errors:
            cprint("-------------- Errors --------------", "red", attrs=["bold"])

            for index, error in enumerate(self.errors, 1):
                if isinstance(error, ColoredException):
                    print(f"{index}. {error.colored_message}")
                else:
                    cprint(f"{index}. {error}", "red", attrs=[])

        cprint("")

    def to_markdown(self, index=None):
        passed = "`✅` "
        if self.errors != []:
            passed = "`❌` "

        index_str = ""
        if index:
            index_str = f"{index}. "

        md = f"""
<details>
<summary>

### {index_str}{passed} {self.conversation.title}

</summary>

### Conversation

"""
        md += "| Role | Message | Checks | Metadata |\n"
        md += "|------|---------|--------|----------|\n"

        interactions = self._get_internal_interactions()

        # TODO: Replace this zipping with another approach
        # Right now, we assume that
        for message, interaction in zip(self.messages, interactions, strict=False):
            if message.role == Role.User:
                name = "user"
                md += f"| `{name}` | **{message.body.replace('\n', '<br>')}** | | |\n"
            if message.role == Role.Chatbot:
                name = "asst"

                requirements = []
                if isinstance(interaction, ChatbotResponds):
                    for expectation in interaction.expectations:
                        prefix = "`✅`" if expectation.passed else "`❌`"
                        requirements.append(
                            f"{prefix} {expectation.humanize()}".replace("\n", "<br>"))

                name_ = name.replace('\n', '<br>')
                body = message.body.replace('\n', '<br>')

                if requirements or message.metadata:
                    for requirement_pair, metadata_pair in itertools.zip_longest(enumerate(requirements), message.metadata.items()):
                        metadata = ""
                        if metadata_pair:
                            metadata = f"`{metadata_pair[0]}`: {metadata_pair[1].replace('\n', '<br>')}"

                        requirement = ""
                        if requirement_pair:
                            (_, requirement) = requirement_pair
                            requirement = f"{requirement.replace('\n', '<br>')}"

                        if index == 0:
                            md += f"| `{name_}` | {body} | {requirement} | {metadata} |\n"
                        else:
                            md += f"|           |        | {requirement} | {metadata} |\n"

                else:
                    md += f"| `{name_}` | {body} | — | — |\n"

        if self.errors:
            md += """
---

### Errors

"""

            for index, error in enumerate(self.errors, 1):
                if isinstance(error, ColoredException):
                    md += f"{index}. {error.markdown_message}<br>\n"
                else:
                    md += f"{index}. {error}<br>\n"
        md += f"""
<br>

---

<br>
<details>
<summary>

### Time taken - {(self.chatbot_time_ms) / 1000}s

</summary>

| Total Time   | {(self.chatbot_time_ms + self.testing_time_ms) / 1000}s |
| ------------ | ------ |
| Chatbot Time | {self.chatbot_time_ms / 1000}s   |
| Testing Time  | {self.testing_time_ms / 1000}s   |

</details>




<details>
<summary>

### Code

</summary>

```python
{self.conversation}
```

</details>
"""
        md += "\n</details>\n\n---\n\n"
        return md

    def _get_internal_interactions(self):
        return self._do_get_internal_interactions(interactions=[], conversation=self.conversation)

    def _do_get_internal_interactions(self, interactions, conversation: Conversation):
        for interaction in conversation.interactions:
            if isinstance(interaction, NestedConversation):
                self._do_get_internal_interactions(
                    conversation=interaction.conversation,
                    interactions=interactions,
                )
            if interaction.is_user_interaction():
                interactions.append(interaction)

            if interaction.is_chatbot_interaction():
                interactions.append(interaction)

        return interactions
