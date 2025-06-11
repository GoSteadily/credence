import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import List

from markdowngenerator import MarkdownGenerator

from credence.interaction import InteractionResultStatus
from credence.interaction.chatbot import ChatbotIgnoresMessageResult, ChatbotRespondsResult
from credence.interaction.chatbot.check.base import BaseCheckResultStatus
from credence.interaction.nested_conversation import NestedConversationResult
from credence.interaction.user import UserMessageResult
from credence.message import Message
from credence.result import Result


@dataclass
class MarkdownRenderer:
    @staticmethod
    def to_markdown(result: Result, index=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = Path(tmpdir).joinpath("default.md")
            with MarkdownGenerator(filename=filename, enable_TOC=False, enable_write=False) as doc:
                prefix = "✅" if not result.failed else "❌"

                index_str = f"{index}. " if index else ""

                with DetailsAndSummary(doc, f"<h3><code>{prefix}</code> {index_str}{escape(result.title, quote=False)}</h3>", escape_html=False):
                    doc.addHeader(3, "Conversation")
                    MarkdownRenderer._add_conversation(
                        result=result,
                        doc=doc,
                        messages=result.messages.copy(),
                    )

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
    def _add_conversation(result: Result, doc: MarkdownGenerator, messages: List[Message]):
        from credence.interaction.function_call import FunctionCall

        for interaction in result.interaction_results:
            if isinstance(interaction, NestedConversationResult):
                with DetailsAndSummary(doc, "🧵 " + interaction.data.name):
                    MarkdownRenderer._add_conversation(
                        result=interaction.results,
                        doc=doc,
                        messages=messages,
                    )

            elif isinstance(interaction, FunctionCall):
                # TODO:
                pass

            elif isinstance(interaction, UserMessageResult):
                if interaction.status == InteractionResultStatus.Passed:
                    title = f"<code>user:</code> {escape(interaction.user_message, quote=False)}"
                    with DetailsAndSummary(doc, title, escape_html=False):
                        pass
                elif interaction.status == InteractionResultStatus.Failed:
                    title = "<code>user ❌:</code>"
                    with DetailsAndSummary(doc, title, escape_html=False):
                        # TODO: Show errors: use generate errors?
                        pass

            elif isinstance(interaction, ChatbotIgnoresMessageResult):
                if interaction.status == InteractionResultStatus.Passed:
                    with DetailsAndSummary(doc, "<code>asst: </code> ", escape_html=False):
                        pass
                elif interaction.status == InteractionResultStatus.Failed:
                    with DetailsAndSummary(doc, f"<code>asst ❌: {interaction.unhandled_message}</code> ", escape_html=False):
                        # TODO: Show errors: use generate errors?
                        pass
                    pass

            elif isinstance(interaction, ChatbotRespondsResult):
                if interaction.status == InteractionResultStatus.Passed:
                    icon = ""
                elif interaction.status == InteractionResultStatus.Failed:
                    icon = " ❌"
                elif interaction.status == InteractionResultStatus.Skipped:
                    icon = " ⛔︎"

                if interaction.missing_chatbot_message:
                    pass
                else:
                    name = f"asst{icon}:"

                    with DetailsAndSummary(doc, f"<code>{name}</code>  {escape(interaction.chatbot_response, quote=False)}", escape_html=False):
                        doc.addHorizontalRule()

                        if interaction.checks != []:
                            marks = []
                            for check in interaction.checks:
                                if check.status == BaseCheckResultStatus.Passed:
                                    mark = "✅"
                                elif check.status == BaseCheckResultStatus.Failed:
                                    mark = "❌"
                                elif check.status == BaseCheckResultStatus.Skipped:
                                    mark = "⛔︎"

                                marks.append(mark)

                            marks = " ".join(marks)

                            with DetailsAndSummary(doc, f"Checks <code>{marks}</code>", escape_html=False):
                                for check in interaction.checks:
                                    if check.status == BaseCheckResultStatus.Passed:
                                        mark = "✅"
                                    elif check.status == BaseCheckResultStatus.Failed:
                                        mark = "❌"
                                    elif check.status == BaseCheckResultStatus.Skipped:
                                        mark = "⛔︎"

                                    doc.writeText(f"  * `{mark}` {escape(check.data.humanize(), quote=False)}\n")
                                doc.writeTextLine()

                        with DetailsAndSummary(doc, "Metadata", escape_html=False):
                            doc.addTable(
                                header_names=["Key", "Value"],
                                row_elements=[[k, v] for (k, v) in interaction.metadata.items()],
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
