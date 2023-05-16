# CLI Chatty
Example for a CLI conversational application using `chat_chain`

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
DEBUG=0 # 1 to enable debug logging
```
3. Start application:
```bash
python .
```
