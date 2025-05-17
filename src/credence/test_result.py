from dataclasses import dataclass
from typing import Any, List, Tuple

from termcolor import cprint

from credence.conversation import Conversation
from credence.exceptions import ColoredException
from credence.interaction.chatbot import ChatbotResponds
from credence.interaction.nested_conversation import NestedConversation
from credence.role import Role


@dataclass
class TestResult:
    messages: List[Tuple[int, Role, str]]
    errors: List[Any]
    conversation: Conversation
    chatbot_time_ms: int
    testing_time_ms: int

    def to_stdout(self):
        cprint("")
        cprint("------------ TestResult ------------", attrs=["bold"])
        cprint(self.conversation.title)
        cprint("------------------------------------")
        cprint(f"  Total Time:  {(self.chatbot_time_ms + self.testing_time_ms) / 1000}s")
        cprint(f"   Test Time:  {self.testing_time_ms / 1000}s")
        cprint(f"Chatbot Time:  {self.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for _index, role, message in self.messages:
            if role == Role.User:
                color = "blue"
                name = "user: "
            if role == Role.Chatbot:
                color = "green"
                name = "asst: "

            cprint(name, color, attrs=["bold"], end="")
            cprint(message)

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
        md += "|Role| Message |Checks|\n"
        md += "|----|---------|------|\n"

        interactions = self._get_internal_interactions()

        # TODO: Replace this zipping with another approach
        # Right now, we assume that
        for message_, interaction in zip(self.messages, interactions, strict=False):
            index, role, message = message_


            if role == Role.User:
                name = "user"
                md += f"| `{name}` | **{message.replace('\n', '<br>')}** | |\n"
            if role == Role.Chatbot:
                name = "asst"


                requirements = []
                if isinstance(interaction, ChatbotResponds):
                    for expectation in interaction.expectations:
                        prefix = "`✅`" if expectation.passed else "`❌`"
                        requirements.append(f"{prefix} {expectation.humanize()}")

                if requirements:
                    for index, requirement in enumerate(requirements):
                        if index == 0:
                            md += f"| `{name}` | {message.replace('\n', '<br>')} | {requirement} |\n"
                        else:
                            md += f"|          |                                 | {requirement} |\n"

                else:
                    md += f"| `{name}` | {message.replace('\n', '<br>')} | {requirements} |\n"

            # md += f"`{name}`\n\n"
            # md += f"> {message.replace('\n', '<br>')}\n\n"

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
