"""
Lobby mode definition
"""

from typing import TYPE_CHECKING

from chat_chain import (Mode, ModeOption, ModeOptionSideEffectKnowledge,
                        ModeOptionSideEffectTransaction)

if TYPE_CHECKING:
    from chat_chain import Conversation, Message


async def _lobby_handle_request(
    conversation: "Conversation", message: str, response: str
) -> list["Message"]:
    # pylint: disable=unused-argument
    # pylint: disable=import-outside-toplevel

    from ._comment_details import comment_details

    conversation.partial_log_range = (len(conversation.log) - 1, None)
    conversation.mode = comment_details

    return [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant named Chatty helping user send a comment on something"
                " you said earlier. Explain to user the following:"
                "\n- User comments which improves your knowledge are highly appreciated and welcome."
                "\n- User needs to provide his name, email address, and comment to proceed."
                "\n- User can cancel the process of registering a comment by requesting to."
            ),
        }
    ]


lobby = Mode(
    name="lobby",
    prompt=(
        "You are a segmentation machine who reply with numbers to segment sentences."
        " The segments numbers are:"
        " 1. If sentence is to request registering a comment."
        " 0. If sentence for anything else."
        " The sentence is: {message}"
    ),
    options=[
        ModeOption(
            condition=lambda response: response == "0",
            side_effect=ModeOptionSideEffectKnowledge(collection="knowledge"),
        ),
        ModeOption(
            condition=lambda response: response == "1",
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_lobby_handle_request
            ),
        ),
    ],
)
