from dataclasses import dataclass

from termcolor import cprint

from credence.exceptions import ColoredException
from credence.interaction import InteractionResultStatus
from credence.result import Result
from credence.role import Role


@dataclass
class TextRenderer:
    @staticmethod
    def to_stdout(result: Result, index=None):
        cprint("")
        cprint("------------ Result ------------", attrs=["bold"])
        cprint(result.title)
        cprint("------------------------------------")
        cprint(f"  Total Time:  {(result.chatbot_time_ms + result.testing_time_ms) / 1000}s")
        cprint(f"   Test Time:  {result.testing_time_ms / 1000}s")
        cprint(f"Chatbot Time:  {result.chatbot_time_ms / 1000}s")
        cprint("------------------------------------\n", attrs=["bold"])

        for message in result.messages:
            if message.role == Role.User:
                color = "blue"
                name = "user: "
            else:
                color = "green"
                name = "asst: "

            cprint(name, color, attrs=["bold"], end="")
            cprint(message.body)

        if result.failed:
            errors = []
            for interaction in result.interaction_results:
                if interaction.status == InteractionResultStatus.Failed:
                    errors.extend(interaction.generate_error_messages())

            if errors:
                cprint("-------------- Errors --------------", "red", attrs=["bold"])
                for index, error in enumerate(errors, 1):
                    if isinstance(error, ColoredException):
                        print(f"{index}. {error.colored_message}\n")

                    else:
                        cprint(f"{index}. {error}\n", "red", attrs=[])
