from dataclasses import dataclass
from typing import Any, List, Tuple

from termcolor import cprint

from credence.conversation import Conversation
from credence.exceptions import ColoredException
from credence.role import Role


@dataclass
class TestResult:
    messages: List[Tuple[Role, str]]
    errors: List[Any]
    conversation: Conversation
    time_taken_ms: int
    chatbot_time_ms: int

    def print(self):
        cprint("")
        cprint("------------ TestResult ------------", attrs=["bold"])
        cprint(self.conversation.title)
        cprint("------------------------------------")
        cprint(f"   Test Time:  {self.time_taken_ms / 1000}s")
        cprint(f"Handler Time:  {self.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for role, message in self.messages:
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
        md += "|||\n"
        md += "|---|---|\n"

        for role, message in self.messages:
            if role == Role.User:
                name = "user"
                md += f"| `{name}` | **{message.replace('\n', '<br>')}** |\n"
            if role == Role.Chatbot:
                name = "asst"
                md += f"| `{name}` | {message.replace('\n', '<br>')} |\n"

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

### Runtime - {(self.time_taken_ms - self.chatbot_time_ms) / 1000}s

</summary>

Runtime

| Total Time   | {self.time_taken_ms / 1000}s |
| ------------ | ------ |
| Chatbot Time | {(self.time_taken_ms - self.chatbot_time_ms) / 1000}s   |
| Tester Time | {self.chatbot_time_ms / 1000}s   |

</details>




<details>
<summary>

### Code

</summary>

```python
{self.conversation}
```

</details>

---

"""
        md += "\n</details>"
        return md
