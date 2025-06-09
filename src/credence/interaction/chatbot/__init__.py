import copy
from dataclasses import dataclass
from typing import Dict, List

from credence.interaction import Interaction, InteractionResult, InteractionResultStatus
from credence.interaction.chatbot.check import BaseCheck
from credence.interaction.chatbot.check.ai import ChatbotResponseAICheck
from credence.interaction.chatbot.check.base import BaseCheckResult
from credence.interaction.chatbot.check.metadata import ChatbotResponseMetadataCheck
from credence.interaction.chatbot.check.response import ChatbotResponseMessageCheck
from credence.message import Message


class Chatbot:
    @staticmethod
    def responds(expectations: List[BaseCheck]) -> Interaction:
        return ChatbotResponds(expectations=expectations)

    @staticmethod
    def ignores_mesage() -> Interaction:
        return ChatbotIgnoresMessage()


@dataclass
class ChatbotResponds(Interaction):
    """@private"""

    expectations: List[BaseCheck]

    def __str__(self):
        """@private"""
        expectations_str = ""
        for expectation in self.expectations:
            expectations_str += "\n"
            for line in str(expectation).splitlines(keepends=True):
                expectations_str += f"    {line}"
            expectations_str += ","

        closing_str = "]"
        if len(self.expectations) > 0:
            closing_str = "\n]"

        return f"""
Chatbot.responds([{expectations_str}{closing_str})
""".strip()

    def to_result(
        self,
        adapter,
        skipped: bool,
        messages: List[Message],
        chatbot_response: str | None,
    ) -> "ChatbotRespondsResult":
        status = None
        from credence import metadata

        if chatbot_response is None:
            skipped = True
            status = InteractionResultStatus.Failed

        check_results = []
        metadata_fields = copy.deepcopy(metadata.metadata)
        for expectation in self.expectations:
            if isinstance(expectation, ChatbotResponseAICheck):
                check_results.append(
                    expectation.to_check_result(
                        messages=messages,
                        adapter=adapter,
                        skipped=skipped,
                    ),
                )

            elif isinstance(expectation, ChatbotResponseMessageCheck):
                check_results.append(
                    expectation.to_check_result(
                        value=chatbot_response,
                        skipped=skipped,
                    ),
                )

            elif isinstance(expectation, ChatbotResponseMetadataCheck):
                if skipped:
                    check_results.append(expectation.skipped())
                    continue
                
                try:
                    value = metadata_fields[expectation.key]
                    check_results.append(
                        expectation.to_check_result(value, skipped=skipped))
                except Exception:
                    check_results.append(expectation.failed_missing_key())

        metadata.clear()

        if status:
            pass
        elif skipped:
            status = InteractionResultStatus.Skipped
        elif chatbot_response is None:
            return ChatbotRespondsResult(
                data=copy.deepcopy(self),
                metadata=metadata_fields,
                status=status,
                checks=check_results,
                missing_chatbot_message=True,
                chatbot_response=chatbot_response,
            )

        elif any(map(lambda c: c.status == InteractionResultStatus.Failed, check_results)):
            status = InteractionResultStatus.Failed
        else:
            status = InteractionResultStatus.Passed

        return ChatbotRespondsResult(
            data=copy.deepcopy(self),
            metadata=metadata_fields,
            status=status,
            checks=check_results,
            chatbot_response=chatbot_response,
        )

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return True


@dataclass(kw_only=True)
class ChatbotRespondsResult(InteractionResult):
    data: ChatbotResponds
    metadata: Dict[str, str]
    status: InteractionResultStatus
    chatbot_response: str
    checks: List[BaseCheckResult]
    missing_chatbot_message: bool = False

    def generate_error_messages(self):
        if self.missing_chatbot_message:
            return ["Chatbot message is missing"]

        errors = []
        for check in self.checks:
            errors.extend(check.generate_error_messages())

        return errors


@dataclass
class ChatbotIgnoresMessage(Interaction):
    """@private"""

    def __str__(self):
        return "Chatbot.ignores_mesage()"

    def is_user_interaction(self) -> bool:
        return False

    def is_chatbot_interaction(self) -> bool:
        return False

    def to_result(self, next_message: str | None):
        if next_message:
            return (self.failed(unhandled_message=next_message),)
        else:
            return self.passed()

    def passed(self) -> "ChatbotIgnoresMessageResult":
        return ChatbotIgnoresMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Passed,
            unhandled_message=None,
        )

    def failed(self, unhandled_message: str) -> "ChatbotIgnoresMessageResult":
        return ChatbotIgnoresMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Failed,
            unhandled_message=unhandled_message,
        )

    def skipped(self) -> "ChatbotIgnoresMessageResult":
        return ChatbotIgnoresMessageResult(
            data=copy.deepcopy(self),
            status=InteractionResultStatus.Skipped,
            unhandled_message=None,
        )


@dataclass(kw_only=True)
class ChatbotIgnoresMessageResult(InteractionResult):
    data: ChatbotIgnoresMessage
    status: InteractionResultStatus
    unhandled_message: str | None = None

    def generate_error_messages(self):
        if self.unhandled_message:
            return [f"Got an unexpected chatbot message:\n`{self.unexpected_chatbot_message}`"]

        return []
