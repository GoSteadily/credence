# from dataclasses import dataclass
# from html import escape
# from typing import List

# from markdowngenerator import MarkdownGenerator

# from credence.conversation import Conversation
# from credence.exceptions import ColoredException
# from credence.interaction.chatbot import ChatbotIgnoresMessage, ChatbotResponds
# from credence.interaction.nested_conversation import NestedConversation
# from credence.interaction.user import UserMessage
# from credence.message import Message
# from credence.result import Result
# from credence.role import Role


# @dataclass
# class JsonRender:
#     def to_json(result: Result, index=None):
#         # prefix = "✅" if result.errors == [] else "❌"

#         # index_str = f"{index}. " if index else ""

#         doc = {
#             "chatbot_time_ms": result.chatbot_time_ms,
#             "testing_time_ms": result.testing_time_ms,
#             "conv": JsonRender._to_conversation(
#                 result=result,
#                 doc=doc,
#                 conversation=result.conversation,
#                 messages=result.messages.copy(),
#             ),
#         }

#         if result.errors:
#             with DetailsAndSummary(doc, "Errors"):
#                 for index, error in enumerate(result.errors, 1):
#                     if isinstance(error, ColoredException):
#                         doc.writeTextLine(f"{index}. {error.markdown_message}\n", html_escape=False)
#                     else:
#                         doc.writeTextLine(f"{index}. {error}\n", html_escape=False)

#         return doc

#     @staticmethod
#     def _to_conversation(result: Result, doc: MarkdownGenerator, conversation: Conversation, messages: List[Message]):
#         from credence.interaction.function_call import FunctionCall

#         interactions = []

#         for interaction in conversation.interactions:
#             if isinstance(interaction, NestedConversation):
#                 interactions.append(
#                     {
#                         "id": interaction.id,
#                         "type": "nested_conversation",
#                         "nested_conversation": JsonRender._to_conversation(
#                             result=result,
#                             doc=doc,
#                             conversation=interaction.conversation,
#                             messages=messages,
#                         ),
#                     }
#                 )

#             elif isinstance(interaction, FunctionCall):
#                 interactions.append(
#                     {
#                         "id": interaction.id,
#                         "type": "function_call",
#                         "function_call": {
#                             "function_id": interaction.function_id,
#                             "name": interaction.function,
#                             "args": interaction.kwargs,
#                         },
#                     }
#                 )

#             elif isinstance(interaction, UserMessage):
#                 message = messages[0]
#                 messages.remove(message)

#                 if message.role == Role.User:
#                     interactions.append(
#                         {
#                             "id": interaction.id,
#                             "type": "user_message",
#                             "user_message": {
#                                 "generated": interaction.generated,
#                                 "message": interaction.text,
#                             },
#                             "message": message.body,
#                         }
#                     )

#             elif isinstance(interaction, ChatbotIgnoresMessage):
#                 interactions.append(
#                     {
#                         "id": interaction.id,
#                         "type": "chatbot_ignore",
#                         "chatbot_ignore": {},
#                     }
#                 )

#             elif isinstance(interaction, ChatbotResponds):
#                 message = messages[0]
#                 messages.remove(message)

#                 if message.role == Role.Chatbot:
#                     failed = False
#                     for expectation in interaction.expectations:
#                         failed = failed or not expectation.passed

#                     name = f"asst{' ❌' if failed else ''}:"
#                     with DetailsAndSummary(doc, f"<code>{name}</code>  {escape(message.body, quote=False)}", escape_html=False):
#                         doc.addHorizontalRule()

#                         if interaction.expectations != []:
#                             marks = []
#                             for expectation in interaction.expectations:
#                                 marks.append("✅" if expectation.passed else "❌")

#                             marks = " ".join(marks)

#                             with DetailsAndSummary(doc, f"Checks <code>{marks}</code>", escape_html=False):
#                                 for expectation in interaction.expectations:
#                                     prefix = "`✅`" if expectation.passed else "`❌`"
#                                     doc.writeText(f"  * {prefix} {escape(expectation.humanize(), quote=False)}")
#                                 doc.writeTextLine()

#                         with DetailsAndSummary(doc, "Metadata", escape_html=False):
#                             doc.addTable(
#                                 header_names=["Key", "Value"],
#                                 row_elements=[[k, v] for (k, v) in message.metadata.items()],
#                                 alignment="left",
#                             )
#         return {"id": result.conversation.id, "name": result.conversation.title, "interactions": interactions}


# class DetailsAndSummary:
#     "@private"

#     def __init__(self, doc: MarkdownGenerator, title: str, escape_html: bool = True):
#         self.doc = doc
#         self.title = title
#         self.escape_html = escape_html

#     def __enter__(self):
#         self.doc.insertDetailsAndSummary(self.title, escape_html=self.escape_html)

#     def __exit__(self, exc_type, exc_value, exc_traceback):
#         self.doc.endDetailsAndSummary()


# def _ms_to_s(ms):
#     return f"{ms / 1000}s"
