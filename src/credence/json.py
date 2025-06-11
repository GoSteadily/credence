import json
import re

from credence.conversation import Conversation
from credence.interaction.chatbot import Chatbot, ChatbotIgnoresMessage
from credence.interaction.chatbot.check import metadata, response
from credence.interaction.chatbot.check.metadata import ChatbotResponseMetadataCheck
from credence.interaction.chatbot.check.response import ChatbotResponseMessageCheck, Response
from credence.interaction.function_call import FunctionCall
from credence.interaction.user import User


def _decode_interaction(data, conversation_lookup):
    t = data["type"]

    if t == "user_message":
        if data["user_message"]["generated"]:
            message = User.generated(data["user_message"]["message"])
        else:
            message = User.message(data["user_message"]["message"])
        message.id = data["user_message"]["id"]
        return message

    elif t == "chatbot_response":
        checks = []
        for check in data["chatbot_response"].get("checks", []):
            ct = check["type"]
            check_ = None
            if ct == "ai_check":
                check_ = Response.ai_check(should=check["ai_check"]["prompt"])
                check_.id = check["ai_check"]["id"]
            elif ct == "message_check":
                op = response.Operation(check["message_check"]["op"])
                check_ = ChatbotResponseMessageCheck(
                    id=check["message_check"]["id"],
                    value=re.compile(check["message_check"]["value"]) if op == response.Operation.RegexMatch else check["message_check"]["value"],
                    operation=response.Operation(check["message_check"]["op"]),
                )
            elif ct == "metadata_check":
                op = metadata.Operation(check["metadata_check"]["op"])
                check_ = ChatbotResponseMetadataCheck(
                    id=check["metadata_check"]["id"],
                    key=check["metadata_check"]["key"],
                    value=re.compile(check["metadata_check"]["value"]) if op == metadata.Operation.RegexMatch else check["metadata_check"]["value"],
                    operation=metadata.Operation(check["metadata_check"]["op"]),
                )
            if check_:
                checks.append(check_)
        r = Chatbot.responds(checks)
        r.id = data["chatbot_response"]["id"]

        return r

    elif t == "chatbot_ignore":
        return ChatbotIgnoresMessage(id=data["chatbot_ignore"]["id"])

    elif t == "nested_conversation":
        nested_id = data["nested_conversation"]["conversation_id"]
        nested_conv = conversation_lookup.get(nested_id)
        if not nested_conv:
            raise ValueError(f"Nested conversation ID {nested_id} not yet decoded.")
        nested = Conversation.nested(nested_conv.title, nested_conv)
        nested.id = data["nested_conversation"]["id"]
        return nested

    elif t == "function_call":
        args = {arg["name"]: _to_arg_value(arg) for arg in data["function_call"]["args"]}

        return FunctionCall(
            id=data["function_call"]["id"],
            name=data["function_call"]["name"],
            args=args,
        )

    raise Exception(f"Unsupported interaction type: {t}")


def decode_conversations(data):
    "@private"
    raw_lookup = {entry["id"]: entry for entry in data}
    decoded = {}
    remaining = set(raw_lookup.keys())

    while remaining:
        progress = False
        for cid in list(remaining):
            entry = raw_lookup[cid]

            try:
                nested_ids = []
                for i in entry["latest_version"]["interactions"]:
                    if i["type"] == "nested_conversation":
                        nested_ids.append(i["nested_conversation"]["conversation_id"])

                if all(nid in decoded for nid in nested_ids):
                    conv = Conversation(
                        id=entry["id"],
                        version_id=entry["latest_version"]["id"],
                        title=entry["latest_version"]["name"],
                        interactions=[_decode_interaction(i, decoded) for i in entry["latest_version"]["interactions"]],
                    )
                    decoded[cid] = conv
                    remaining.remove(cid)
                    progress = True
            except KeyError as e:
                raise ValueError(f"Missing expected key in interaction: {e}") from e
            # except Exception as e:
            #     # print(e)
            #     continue

        if not progress:
            unresolved = ", ".join(remaining)

            raise RuntimeError(f"Could not resolve dependencies for: {unresolved}")

    return list(decoded.values())


def _to_arg_value(arg):
    if arg["type"] == "number":
        return _to_number(arg["value"])
    else:
        return arg["value"]


def _to_number(string):
    try:
        return int(string)
    except Exception:
        return float(string)


# TODO: Expose this as an entry point
# `credence sync conversations`
# https://setuptools.pypa.io/en/latest/userguide/entry_point.html
#
# Things to think about:
# - credence.toml
#   - projectID
#   - suitePath?: Users may prefer tests inside their tests folder
# - credence/secrets.toml
#   - api_key
def download(api_key):
    import requests

    # 1. The web endpoint that returns JSON
    url = "http://localhost:4000/api/conversations"

    # 2. Send the GET request
    response = requests.get(url)

    # 3. Check for a successful response
    if response.status_code == 200:
        data = response.json()  # Parse JSON response

        # 4. (Optional) Save it to a local file
        # with open("downloaded_data.json", "w") as f:
        #     json.dump(data, f, indent=2)

        # print("Download complete. Saved to downloaded_data.json")
        return data
    else:
        pass
        # TODO: Raise
        # print(f"Failed to fetch data: {response.status_code}")
