"""
Classes and definitions for Conversation Modes feature
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Literal, Optional, TypedDict

import openai
from mypy_extensions import Arg

from ._config import Config
from ._gpt import compose_prompt, match_knowledge


async def _get_model_answer(*, prompt: str) -> str:
    response = await openai.ChatCompletion.acreate(
        model=Config.consts.model,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2,
    )

    return response["choices"][0]["message"]["content"]


async def handle_message(
    *, conversation: "Conversation", message: str
) -> tuple[list["Message"], int]:
    """
    Utility function to handle a message and execute chain on

    :param :class:`Conversation` conversation:
        Current :class:`Conversation` session
    :param str message:
        Received message
    :return:
        (tuple[list[:class:`Message`], int]) Tuple of two items, list of messages to be passed to AI
        mode, AI model response limit
    """

    logging.debug("Handling message '%s' with mode: %s", message, conversation.mode)

    conversation.log.append({"role": "user", "content": message})

    mode = conversation.mode

    messages_conversation = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in conversation.log[
            conversation.partial_log_range[0] : conversation.partial_log_range[1]
        ]
    )

    mode_prompt = mode.prompt.replace("{message}", message).replace(
        "{conversation}", messages_conversation
    )

    logging.debug("Compiled mode prompt: %s", mode_prompt)

    response = await _get_model_answer(prompt=mode_prompt)

    logging.debug("Model response: %s", response)

    messages_list: list["Message"] = [
        {
            "role": "system",
            "content": (
                "You are a chatbot. You didn't understand what user had told you. Request user to"
                " rephrase the message."
            ),
        }
    ]

    for (i, option) in enumerate(mode.options):
        if option.condition(response):
            logging.debug(
                "Option '%s' condition for response from model is truthy. Executing side effect",
                i,
            )
            messages_list = await option.side_effect.exec(
                conversation=conversation, message=message, response=response
            )
            break
    else:
        logging.debug(
            "No options matched for model response. Falling back to default no-understand response",
        )

    response_tokens_limit = 300

    logging.debug(
        "Final messages_list, response_tokens_limit: %s, %s",
        messages_list,
        response_tokens_limit,
    )

    return (messages_list, response_tokens_limit)


class Message(TypedDict):
    """
    Type hint class for GPT message entry

    :param Literal["system","user","assistant"] role:
        Role of character of message entry
    :param str content:
        Message content
    """

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(kw_only=True)
class Conversation:
    """
    In-memory representation of user conversation values and config

    :param :class:`Mode` mode:
        Current mode of conversation
    :param str session:
        Reference to session ID
    :param list[:class:`Message`] log:
        List of all messages in conversation
    :param tuple[int,Optional[int]] partial_log_range:
        Range representation of messages log that are of interest for current mode
    """

    mode: "Mode"
    session: str
    log: list["Message"]
    partial_log_range: tuple[int, Optional[int]]


@dataclass(kw_only=True)
class Mode:
    """
    Define and configure conversation modes

    :param str name:
        Unique name for logging and debugging
    :param str prompt:
        Prompt used to analyse user message. `{message}` in prompt will be replaced with user
        message

    """

    name: str
    prompt: str
    options: list["ModeOption"]


@dataclass(kw_only=True)
class ModeOption:
    """
    Define an option for :class:`Mode` to test against `prompt` response

    :param Callable[[str],bool] condition:
        Callable to execute to test whether :class:`Mode` prompt response satisfies this action
    :param :class:`ModelActionSideEffect` side_effect:
        Side effect to be executed if `condition` is truthful
    """

    condition: Callable[[str], bool]
    side_effect: "ModeOptionSideEffect"


class ModeOptionSideEffect(ABC):
    """
    Abstract class for possible :class:`ModeOption` side effects
    """

    # pylint: disable=too-few-public-methods

    @abstractmethod
    async def exec(
        self, *, conversation: "Conversation", message: str, response: str
    ) -> list["Message"]:
        """
        Abstract method to provide side effect definition for a mode option
        """


@dataclass(kw_only=True)
class ModeOptionSideEffectKnowledge(ModeOptionSideEffect):
    """
    Implementation of :class:`ModeOptionSideEffect` to provide knowledge side effect

    :param str collection:
        Name of collection to query for knowledge
    """

    collection: str

    async def exec(
        self, *, conversation: "Conversation", message: str, response: str
    ) -> list["Message"]:
        knowledge = await match_knowledge(question=message)

        prompt = await compose_prompt(knowledge=knowledge)

        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ]


@dataclass(kw_only=True)
class ModeOptionSideEffectTransaction(ModeOptionSideEffect):
    """
    Implementation of :class:`ModeOptionSideEffect` to provide transaction side effect

    :param Callable transaction:
        Transaction to execute as side effect
    """

    transaction: Callable[
        [
            Arg("Conversation", "conversation"),
            Arg(str, "message"),
            Arg(str, "response"),
        ],
        Coroutine[Any, Any, list["Message"]],
    ]

    async def exec(
        self, *, conversation: "Conversation", message: str, response: str
    ) -> list["Message"]:
        return await self.transaction(
            conversation=conversation, message=message, response=response
        )
