"""
Request details mode
"""

import json
import logging
from typing import TYPE_CHECKING

from chat_chain import Mode, ModeOption, ModeOptionSideEffectTransaction

if TYPE_CHECKING:
    from chat_chain import Conversation, Message


def _load_details_json(response: str) -> dict:
    try:
        j = json.loads(response)
    except Exception:  # pylint: disable=broad-except
        j = {"name": None, "email": None, "comment": None}

    return j


async def _comment_details_handle_cancel(
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


async def _comment_details_handle_missing(
    conversation: "Conversation", message: str, response: str
) -> list["Message"]:
    # pylint: disable=unused-argument

    j = _load_details_json(response)

    return [
        {
            "role": "system",
            "content": (
                "You are a chat bot assisting a user registering a comment. Extract values from"
                f" following JSON '{j}', iterate it to user and request missing values."
                " Reply in the same language as following sentence:"
                f" '{conversation.log[conversation.partial_log_range[0]]['content']}'"
            ),
        }
    ]


async def _comment_details_handle_completed(
    conversation: "Conversation", message: str, response: str
) -> list["Message"]:
    # pylint: disable=unused-argument
    # pylint: disable=import-outside-toplevel

    from ._comment_confirm import comment_confirm

    j = _load_details_json(response)

    logging.debug("Changing mode to 'comment_confirm' as user provided all details")
    # Change conversation mode to comment_confirm
    conversation.mode = comment_confirm

    return [
        {
            "role": "system",
            "content": (
                f"You are a chat bot assisting {j['name']} registering a comment. User has provided"
                " all required details which are 'name', 'email', 'comment'. Display the details to"
                " user and request his confirmation on the details before finally registering the"
                " comment in the system."
                f" Reply in the same language as following sentence: {message}"
            ),
        }
    ]


comment_details = Mode(
    name="comment_details",
    prompt=(
        "You are a bot whose job is to extract following values from conversation:"
        ' "name", "email", "comment", "cancel". Values can not be empty or zero-length. Reply with'
        " JSON format only. Example of a correct reply JSON format:"
        ' {"name": <user\'s name>, "email": <user\'s email lowercase>, "comment": <user\'s comment>'
        ' }. If user requested cancelling process return following JSON {"cancel": true}.'
        " If any values are missing set the value in json format to null."
        " The conversion is:\n{conversation}"
    ),
    options=[
        ModeOption(
            condition=lambda response: "cancel" in _load_details_json(response),
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_comment_details_handle_cancel
            ),
        ),
        ModeOption(
            condition=lambda response: any(
                v is None for v in _load_details_json(response).values()
            ),
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_comment_details_handle_missing
            ),
        ),
        ModeOption(
            condition=lambda response: all(_load_details_json(response).values()),
            side_effect=ModeOptionSideEffectTransaction(
                transaction=_comment_details_handle_completed
            ),
        ),
    ],
)
