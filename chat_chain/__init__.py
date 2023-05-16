"""
`chat_chain`

Simple chain toolings to build conversational applications
"""

from ._chain import (Conversation, Message, Mode, ModeOption,
                     ModeOptionSideEffect, ModeOptionSideEffectKnowledge,
                     ModeOptionSideEffectTransaction, handle_message)
from ._config import Config
from ._gpt import get_embedding, get_response, get_response_chunks

VERSION = "0.1.0"

__all__ = [
    "VERSION",
    "Conversation",
    "Message",
    "Mode",
    "ModeOption",
    "ModeOptionSideEffect",
    "ModeOptionSideEffectKnowledge",
    "ModeOptionSideEffectTransaction",
    "handle_message",
    "Config",
    "get_embedding",
    "get_response",
    "get_response_chunks",
]
