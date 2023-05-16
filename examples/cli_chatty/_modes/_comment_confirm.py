"""
Request confirm mode
"""

import json
import logging
from typing import TYPE_CHECKING

from chat_chain import (Config, Mode, ModeOption,
                        ModeOptionSideEffectTransaction)

if TYPE_CHECKING:
    from chat_chain import Conversation, Message


def _load_details_json(response: str) -> dict:
    try:
        j = json.loads(response)
    except Exception:  # pylint: disable=broad-except
        j = {"name": None, "email": None, "comment": None, "confirm": False}

    return j


async def _comment_confirm_handle_confirm(
    conversation: "Conversation", message: str, response: str
) -> list["Message"]:
    # pylint: disable=unused-argument
    # pylint: disable=import-outside-toplevel

    from ._lobby import lobby

    j = _load_details_json(response)

    ref = "123"
    # Uncomment for live transaction
    # result = await Config.mongoddb.comments.insert_one(j)
    # ref = result.inserted_id

    logging.debug("Changing mode to 'lobby' as user confirmed details")
    # Return user to lobby mode and reset partial_log_range
    conversation.partial_log_range = (len(conversation.log) - 1, None)
    conversation.mode = lobby

    return [
        {
            "role": "system",
            "content": (
                f"You are a chat bot assisting {j['name']} register a comment for Chatty team."
                " Thank user and inform him request has been received and that Masaar team would"
                f" contact him shortly. Also infor user the reference for request is {ref}."
                " Also inform user you are ready to receive his questions about what you know."
                f" Reply in the same language as following sentence: {message}"
            ),
        }
    ]


async def _comment_confirm_handle_cancel(
    conversation: "Conversation", message: str, response: str
) -> list["Message"]:
    # pylint: disable=unused-argument
    # pylint: disable=import-outside-toplevel

    from ._lobby import lobby

    logging.debug(
        "Changing mode to 'lobby' as user cancelled process to register a comment"
    )
    # Return user to lobby mode and reset partial_log_range
    conversation.partial_log_range = (len(conversation.log) - 1, None)
    conversation.mode = lobby

    return [
        {
            "role": "system",
            "content": (
                "You are a chat bot assisting a user registering a comment. User has decided"
                " to end the process to registering a comment. Inform user process has been"
                " cancelled and user can start asking again about information on Muslims and"
                " Arabs contributions to science and knowledge, past and modern."
                " Reply in the same language as following sentence:"
                f" '{conversation.log[conversation.partial_log_range[0]]['content']}'"
            ),
        }
    ]


comment_confirm = Mode(
    name="comment_confirm",
    prompt=(
        "You are a bot whose job is to extract following values from conversation:"
        ' "name", "email", "comment", "confirm". Values can not be empty or zero-length. Reply with'
        " JSON format only. Example of a correct reply JSON format:"
        ' {"name": <user\'s name>, "email": <user\'s email lowercase>, "comment": <user\'s comment>'
        ' "confirm": <boolean value to indicate user confirmed the details>}. '
        " If any values are missing set the value in json format to null."
        " The conversion is:\n{conversation}"
    ),
    options=[
        ModeOption(
            condition=lambda response: not _load_details_json(response)["confirm"],
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_comment_confirm_handle_cancel
            ),
        ),
        ModeOption(
            condition=lambda response: _load_details_json(response)["confirm"],
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_comment_confirm_handle_confirm
            ),
        ),
    ],
)
