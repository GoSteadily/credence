import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, List

from markdowngenerator import MarkdownGenerator
from termcolor import cprint

from credence.conversation import Conversation
from credence.exceptions import ColoredException
from credence.interaction.chatbot import ChatbotIgnoresMessage, ChatbotResponds
from credence.interaction.nested_conversation import NestedConversation
from credence.interaction.user import UserGenerated, UserMessage
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
        cprint(f"  Total Time:  {(self.chatbot_time_ms + self.testing_time_ms) / 1000}s")
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
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = Path(tmpdir).joinpath("default.md")
            with MarkdownGenerator(filename=filename, enable_TOC=False, enable_write=False) as doc:
                prefix = "✅" if self.errors == [] else "❌"

                index_str = f"{index}. " if index else ""

                with DetailsAndSummary(doc, f"<h3><code>{prefix}</code> {index_str}{escape(self.conversation.title, quote=False)}</h3>", escape_html=False):
                    doc.addHeader(3, "Conversation")
                    self._add_conversation(doc, self.conversation, self.messages.copy())

                    doc.addHorizontalRule()

                    if self.errors:
                        with DetailsAndSummary(doc, "Errors"):
                            for index, error in enumerate(self.errors, 1):
                                if isinstance(error, ColoredException):
                                    doc.writeTextLine(f"{index}. {error.markdown_message}\n", html_escape=False)
                                else:
                                    doc.writeTextLine(f"{index}. {error}\n", html_escape=False)

                    with DetailsAndSummary(doc, f"Time taken - {(self.chatbot_time_ms) / 1000}s"):
                        total_time = self.chatbot_time_ms + self.testing_time_ms

                        doc.addTable(
                            header_names=["Name", "Time"],
                            row_elements=[
                                ["Total Time  ", _ms_to_s(total_time)],
                                ["Chatbot Time", _ms_to_s(self.chatbot_time_ms)],
                                ["Testing Time", _ms_to_s(self.testing_time_ms)],
                            ],
                            alignment="right",
                        )

                    with DetailsAndSummary(doc, "Code"):
                        doc.addCodeBlock(f"{self.conversation}", "python")

        return "".join(doc.document_data_array)

    def _add_conversation(self, doc: MarkdownGenerator, conversation: Conversation, messages: List[Message]):
        from credence.interaction.external import External

        for interaction in conversation.interactions:
            if isinstance(interaction, NestedConversation):
                with DetailsAndSummary(doc, "🧵 " + interaction.name):
                    self._add_conversation(doc, interaction.conversation, messages)

            elif isinstance(interaction, External):
                pass

            elif isinstance(interaction, UserGenerated) or isinstance(interaction, UserMessage):
                message = messages[0]
                messages.remove(message)

                if message.role == Role.User:
                    title = f"<code>user:</code> {escape(message.body, quote=False)}"
                    with DetailsAndSummary(doc, title, escape_html=False):
                        pass

            elif isinstance(interaction, ChatbotIgnoresMessage):
                with DetailsAndSummary(doc, "<code>asst: </code> ", escape_html=False):
                    pass

            elif isinstance(interaction, ChatbotResponds):
                message = messages[0]
                messages.remove(message)

                if message.role == Role.Chatbot:
                    failed = False
                    for expectation in interaction.expectations:
                        failed = failed or not expectation.passed

                    name = f"asst{' ❌' if failed else ''}:"
                    with DetailsAndSummary(doc, f"<code>{name}</code>  {escape(message.body, quote=False)}", escape_html=False):
                        doc.addHorizontalRule()

                        if interaction.expectations != []:
                            marks = []
                            for expectation in interaction.expectations:
                                marks.append("✅" if expectation.passed else "❌")

                            marks = " ".join(marks)

                            with DetailsAndSummary(doc, f"Checks <code>{marks}</code>", escape_html=False):
                                for expectation in interaction.expectations:
                                    prefix = "`✅`" if expectation.passed else "`❌`"
                                    doc.writeText(f"  * {prefix} {escape(expectation.humanize(), quote=False)}")
                                doc.writeTextLine()
                                
                        with DetailsAndSummary(doc, "Metadata", escape_html=False):
                            doc.addTable(
                                header_names=["Key", "Value"],
                                row_elements=[[k, v] for (k, v) in message.metadata.items()],
                                alignment="left",
                            )

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


class DetailsAndSummary:
    "@private"

    def __init__(self, doc: MarkdownGenerator, title: str, escape_html: bool = True):
        self.doc = doc
        self.title = title
        self.escape_html = escape_html

    def __enter__(self):
        self.doc.insertDetailsAndSummary(self.title, escape_html=self.escape_html)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.doc.endDetailsAndSummary()


def _ms_to_s(ms):
    return f"{ms / 1000}s"
