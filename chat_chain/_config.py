"""
Class and instance of runtime config
"""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import openai
import qdrant_client
from motor.motor_asyncio import AsyncIOMotorClient

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

openai.api_key = os.getenv("OPENAI_API_KEY")


@dataclass(kw_only=True)
class _ConfigConsts:
    system_prompt_intro: str
    system_prompt_knowledge: str
    system_prompt_no_knowledge: str
    system_prompt_ending: str
    model: str
    knowledge_bar: float
    max_knowledge: int


@dataclass(kw_only=True)
class _Config:
    mongodb: "AsyncIOMotorDatabase"
    qdrant: "qdrant_client.QdrantClient"
    consts: "_ConfigConsts"


Config = _Config(
    mongodb=AsyncIOMotorClient(os.getenv("DB_CONN_STRING")).chain_data,
    qdrant=qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST_STRING"),
        prefer_grpc=True,
    ),
    consts=_ConfigConsts(
        system_prompt_intro=os.getenv("SYSTEM_PROMPT_INTRO")
        or "You are a helpful chat assistant",
        system_prompt_knowledge=os.getenv("SYSTEM_PROMPT_KNOWLEDGE")
        or (
            "Your only source of knowledge is following text and you should ploitely decline to"
            " answer any question not from the following text: "
        ),
        system_prompt_no_knowledge=os.getenv("SYSTEM_PROMPT_NO_KNOWLEDGE")
        or (
            "User has asked a question you didn't understand or don't have the knowledge to answer."
            " Apologise to user and reply explaining you didn't understand or know answer."
        ),
        system_prompt_ending=os.getenv("SYSTEM_PROMPT_ENDING")
        or "End the your messages with: ",
        model="gpt-3.5-turbo",
        knowledge_bar=0.80,
        max_knowledge=5,
    ),
)
