"""
Functions to craft messages and to get response from AI model
"""

import itertools
import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator, Optional

import openai
import tiktoken

from ._config import Config

if TYPE_CHECKING:
    from qdrant_client.conversions.common_types import ScoredPoint

    from ._chain import Message


async def query_qdrant(query: str, /) -> list["ScoredPoint"]:
    """
    Search QDrant database for articles matching `query`

    :param str query:
        String to vectorise and match against database data
    :return:
        List of :class:`ScoredPoint` objects, each representing one match, sorted by match score,
        limited to 5
    """

    query_embeddings = await get_embedding(query)

    query_results = Config.qdrant.search(
        collection_name="parts",
        query_vector=("content", query_embeddings),
        limit=Config.consts.max_knowledge,
    )

    return query_results


@dataclass(kw_only=True)
class Knowledge:
    """
    Dataclass to represent results of matching question against knowledge-base

    :param tuple[tuple[str,float]] matched_parts:
        Tuple of tuples of three values, first is part ID, second is match score, third is part
        content
    :param :class:`Counter` parts_tags:
        Collection of all tags of matched parts represented as :class:`Counter` object
    """

    matched_parts: tuple[tuple[str, float, str], ...]
    parts_tags: "Counter"


async def match_knowledge(*, question: str) -> "Knowledge":
    """
    Match question against knowledge-base and find best matches, along with tags

    :param str question:
        Question to match against knowledge-base
    :return:
        :class:`Knowledge` object
    """

    question = question.strip()

    query_results = await query_qdrant(question)

    knowledge_tags = itertools.chain.from_iterable(
        (result.payload or {}).get("metadata", {}).get("tags", [])
        for result in query_results
    )

    return Knowledge(
        matched_parts=tuple(
            (
                (result.payload or {}).get("id", None),
                result.score,
                (result.payload or {}).get("content", None),
            )
            for result in query_results
        ),
        parts_tags=Counter(knowledge_tags),
    )


async def compose_prompt(*, knowledge: "Knowledge") -> str:
    """
    Compose AI model system prompt that dictates model task

    Uses :class:`Knowledge` object to form a prompt which either dictates model knowledge, or its
    ignorance on the topic asked by user. It also uses object `parts_tags` to determine adding a
    response ending instructions

    :param :class:`Knowledge` knowledge:
        :class:`Knowledge` object to analyse
    :return:
        AI model system prompt
    """

    prompt = Config.consts.system_prompt_intro

    acceptable_knowledge = tuple(
        part
        for part in knowledge.matched_parts
        if part[1] >= Config.consts.knowledge_bar
    )

    if not acceptable_knowledge:
        prompt += f" {Config.consts.system_prompt_no_knowledge}"
        return prompt

    tags = [tag[0] for tag in knowledge.parts_tags.most_common()]
    tags_prompts = {
        doc["tag"]: doc["prompt"]
        async for doc in Config.mongodb.tags_prompts.find({"tag": {"$in": tags}})
    }

    for tag in tags:
        if tag in tags_prompts:
            prompt += f" {Config.consts.system_prompt_ending}{tags_prompts[tag]}"
            break

    prompt += (
        f" {Config.consts.system_prompt_knowledge}"
        f"{' '.join(part[2] for part in acceptable_knowledge)}"
    )

    return prompt


def build_messages_list(
    *, prompt: str, question: Optional[str] = None
) -> tuple[list["Message"], int]:
    """
    Build messages list to be used with AI model to generate response

    Beside formatting arguments into the correct format for AI model SDK, this function also
    truncates `prompt` down to point where it takes two thirds of tokens limit impose by AI model,
    in order to keep 100 max tokens for question, and rest for the answer

    :param str prompt:
        AI model system prompt
    :param str question:
        User question
    :return:
        Tuple of two values, first is truncated prompt and question as AI model SDK messages list,
        second is tokens limit to be set for response
    """

    messages: list["Message"] = [
        {"role": "system", "content": prompt},
    ]

    if question:
        messages.append({"role": "user", "content": question})

    tokens_count = num_tokens_from_messages(messages)
    while True:
        if tokens_count <= 2500:
            break
        prompt = truncate_prompt(prompt=prompt, tokens_count=tokens_count)
        tokens_count = num_tokens_from_messages(messages)

    return (messages, min(4096 - tokens_count, 500))


def truncate_prompt(*, prompt: str, tokens_count: int) -> str:
    """
    Truncate prompt in relative to `tokens_count` to words count of `prompt`

    :param str prompt:
        AI model system prompt
    :param int tokens_count:
        Tokens count for messages list which `prompt` was part of
    :return:
        Truncated AI model system prompt
    """

    knowledge_words = prompt.split(" ")
    knowledge_words_count = len(knowledge_words)
    prompt = " ".join(
        knowledge_words[: math.floor((knowledge_words_count * 2500) / tokens_count)]
    )

    return prompt


async def get_response(*, messages: list["Message"], response_tokens_limit: int) -> str:
    """
    Get response to user question from AI model

    :param list[Message] messages:
        List of messages which includes AI model system prompt and user question
    :return:
        AI model response
    """

    response = await openai.ChatCompletion.acreate(
        model=Config.consts.model,
        messages=messages,
        max_tokens=response_tokens_limit,
    )

    return response["choices"][0]["message"]["content"]


async def get_response_chunks(
    *, messages: list["Message"], response_tokens_limit: int
) -> AsyncIterator[tuple[int, str]]:
    """
    Get response to user question from AI model in chunks

    :param list[Message] messages:
        List of messages which includes AI model system prompt and user question
    :param int response_tokens_limit:
        Value of max tokens expected to be the response of AI model
    :return:
        Tuple of two values, first is chunk index, second is chunk value, asynchronously iterable
    """

    content_index = 0

    async for chunk in await openai.ChatCompletion.acreate(
        model=Config.consts.model,
        messages=messages,
        max_tokens=response_tokens_limit,
        stream=True,
    ):
        content = chunk["choices"][0].get("delta", {}).get("content")
        if content is not None:
            yield (content_index, content)
            content_index += 1


async def get_embedding(text: str, /) -> list[float]:
    """
    Calculate embeddings of `text`

    :param str text:
        Text to calculate its embeddings
    :return:
        Embeddings vector as list of float points
    """

    result = await openai.Embedding.acreate(model="text-embedding-ada-002", input=text)
    return result["data"][0]["embedding"]


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += (
                4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            )
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    raise NotImplementedError(
        f"""num_tokens_from_messages() is not presently implemented for model {model}.
  https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are
  converted to tokens."""
    )
