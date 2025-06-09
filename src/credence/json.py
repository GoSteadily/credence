import json

from credence.conversation import Conversation
from credence.interaction.chatbot import Chatbot, ChatbotIgnoresMessage
from credence.interaction.chatbot.check.metadata import Metadata
from credence.interaction.chatbot.check.response import Response
from credence.interaction.function_call import FunctionCall
from credence.interaction.user import User


def _decode_interaction(data, conversation_lookup):
    t = data["type"]

    if t == "user_message":
        return User.message(data["user_message"]["message"])

    elif t == "chatbot_response":
        checks = []
        for check in data["chatbot_response"].get("checks", []):
            ct = check["type"]
            if ct == "ai_check":
                checks.append(Response.ai_check(should=check["ai_check"]["prompt"]))
            elif ct == "message_check":
                op = check["message_check"]["op"]
                val = check["message_check"]["value"]
                if op == "contains":
                    checks.append(Response.contains(val))
                elif op == "equals":
                    checks.append(Response.equals(val))
            elif ct == "metadata_check":
                m = check["metadata_check"]
                op = m["op"]
                if op == "equals":
                    checks.append(Metadata(m["key"]).equals(m["value"]))
        return Chatbot.responds(checks)

    elif t == "chatbot_ignore":
        return ChatbotIgnoresMessage()

    elif t == "nested_conversation":
        nested_id = data["nested_conversation"]["conversation_id"]
        nested_conv = conversation_lookup.get(nested_id)
        if not nested_conv:
            raise ValueError(f"Nested conversation ID {nested_id} not yet decoded.")
        return Conversation.nested(nested_conv.title, nested_conv)

    elif t == "function_call":
        args = {arg["name"]: _to_arg_value(arg) for arg in data["function_call"]["args"]}

        return FunctionCall(
            name=data["function_call"]["name"],
            args=args,
            function_id=data["function_call"]["function_id"],
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
                # Check for unresolved nested dependencies
                nested_ids = []
                for i in entry["interactions"]:
                    if i["type"] == "nested_conversation":
                        nested_ids.append(i["nested_conversation"]["conversation_id"])

                if all(nid in decoded for nid in nested_ids):
                    conv = Conversation(title=entry["name"], interactions=[_decode_interaction(i, decoded) for i in entry["interactions"]])
                    decoded[cid] = conv
                    remaining.remove(cid)
                    progress = True
            except KeyError as e:
                raise ValueError(f"Missing expected key in interaction: {e}") from e
            except Exception:
                continue

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
        with open("downloaded_data.json", "w") as f:
            json.dump(data, f, indent=2)

        # print("Download complete. Saved to downloaded_data.json")
        return data
    else:
        pass
        # TODO: Raise
        # print(f"Failed to fetch data: {response.status_code}")
