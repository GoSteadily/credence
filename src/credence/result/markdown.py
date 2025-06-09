import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import List

from markdowngenerator import MarkdownGenerator

from credence.conversation import Conversation
from credence.interaction.chatbot import ChatbotIgnoresMessage, ChatbotResponds
from credence.interaction.nested_conversation import NestedConversation
from credence.interaction.user import UserMessage
from credence.message import Message
from credence.result import Result
from credence.role import Role


@dataclass
class MarkdownRenderer:
    def to_markdown(result: Result, index=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = Path(tmpdir).joinpath("default.md")
            with MarkdownGenerator(filename=filename, enable_TOC=False, enable_write=False) as doc:
                prefix = "✅" if result.errors == [] else "❌"

            #     index_str = f"{index}. " if index else ""

            #     with DetailsAndSummary(doc, f"<h3><code>{prefix}</code> {index_str}{escape(result.conversation.title, quote=False)}</h3>", escape_html=False):
            #         doc.addHeader(3, "Conversation")
            #         MarkdownRenderer._add_conversation(
            #             result=result,
            #             doc=doc,
            #             conversation=result.conversation,
            #             messages=result.messages.copy(),
            #         )

            #         doc.addHorizontalRule()

            #         if result.errors:
            #             with DetailsAndSummary(doc, "Errors"):
            #                 for index, error in enumerate(result.errors, 1):
            #                     if isinstance(error, ColoredException):
            #                         doc.writeTextLine(f"{index}. {error.markdown_message}\n", html_escape=False)
            #                     else:
            #                         doc.writeTextLine(f"{index}. {error}\n", html_escape=False)

            #         with DetailsAndSummary(doc, f"Time taken - {(result.chatbot_time_ms) / 1000}s"):
            #             total_time = result.chatbot_time_ms + result.testing_time_ms

            #             doc.addTable(
            #                 header_names=["Name", "Time"],
            #                 row_elements=[
            #                     ["Total Time  ", _ms_to_s(total_time)],
            #                     ["Chatbot Time", _ms_to_s(result.chatbot_time_ms)],
            #                     ["Testing Time", _ms_to_s(result.testing_time_ms)],
            #                 ],
            #                 alignment="right",
            #             )

            #         # with DetailsAndSummary(doc, "Code"):
            #         #     doc.addCodeBlock(f"{result.conversation}", "python")

        return "".join(doc.document_data_array)

    @staticmethod
    def _add_conversation(result: Result, doc: MarkdownGenerator, conversation: Conversation, messages: List[Message]):
        from credence.interaction.function_call import FunctionCall

        for interaction in conversation.interactions:
            if isinstance(interaction, NestedConversation):
                with DetailsAndSummary(doc, "🧵 " + interaction.name):
                    MarkdownRenderer._add_conversation(
                        result=result,
                        doc=doc,
                        conversation=interaction.conversation,
                        messages=messages,
                    )

            elif isinstance(interaction, FunctionCall):
                pass

            elif isinstance(interaction, UserMessage):
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
