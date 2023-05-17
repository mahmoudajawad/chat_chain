# CLI Chatty
Example for a CLI conversational application using `chat_chain`

## Pre-requisite
- You need to have a [MongoDB](https://www.mongodb.com) instance running.
- You need to have a [QDrant](https://qdrant.tech) instance running.
- QDrant instance should have collection `knowledge`, which:
  - Defines following vecor:
```
{
    "content": rest.VectorParams(
        distance=rest.Distance.COSINE,
        size=1536,
    ),
}
```
  - Every document in the collection has following payload:
```
{
  "content": KNOWLEDGE_CONTENT,
  "metadata": {
      "title": KNOWLEDGE_TITLE,
      "tags": KNOWLEDGE_TAGS_ARRAY,
  }
}
```
- You can use `docker-compose` to launch required instances locally.

## How to Use
Follow steps:
1. Install additional requirements from `requirements.txt` as:
```bash
pip install -r requirements.txt
```
2. Create `.env` file with following contents:
```dotenv
DB_CONN_STRING=localhost # MongoDB connection string
QDRANT_HOST_STRING=localhost # QDrant connection string
OPENAI_API_KEY= # OpenAI API key
DEBUG= # 1 to enable debug logging
```
3. Start application:
```bash
python .
```
