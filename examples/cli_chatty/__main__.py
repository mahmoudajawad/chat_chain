"""
Chatty executable functions
"""

import asyncio
import logging
import os
from typing import AsyncIterable

import dotenv
import openai
from chat_chain import (Config, Conversation, get_response_chunks,
                        handle_message)

from _modes import lobby

async def _process_conversation_message(
    *, conversation: "Conversation", message: str
) -> AsyncIterable[tuple[int, str]]:
    messages, response_tokens_limit = await handle_message(
        conversation=conversation, message=message
    )

    response = ""

    async for chunk in get_response_chunks(
        messages=messages, response_tokens_limit=response_tokens_limit
    ):
        yield chunk
        response += chunk[1]

    conversation.log.append({"role": "assistant", "content": response})


async def answer_message(conversation, message, /):
    """
    Print out answer to user message
    """

    print("AI: ", end="", flush=True)
    async for chunk in _process_conversation_message(
        conversation=conversation, message=message
    ):
        print(chunk[1], end="", flush=True)

    print("\n")


def main():
    """
    Chatty main
    """

    dotenv.load_dotenv()

    openai.api_key = os.getenv("OPENAI_API_KEY")

    if os.getenv("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)

    Config.consts.system_prompt_intro = (
        "You are a helpful assistant named Chatty who is helps users learn about contributions"
        " of Muslims and Arabs to science and knowledge, past and modern. You also can take"
        " comments from users on the information you provide and register them for review by"
        " team."
    )

    conversation = Conversation(
        mode=lobby, session="session", log=[], partial_log_range=(0, None)
    )

    # Conversation starter
    print("> Who are you?")
    asyncio.run(answer_message(conversation, "Who are you?"))

    # Conversation loop
    while True:
        message = input("> ")
        asyncio.run(answer_message(conversation, message))


if __name__ == "__main__":
    main()
