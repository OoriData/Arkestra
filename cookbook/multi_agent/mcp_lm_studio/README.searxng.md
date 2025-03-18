Simple example with a single tool that connects to a local SearXNG instance, allowing the LLM to perform web searches. The server handles the API calls to SearXNG, while the client manages communication between the LLM and the MCP server.

```sh
export SEARXNG_PORT=8888                     
docker run \
    -d -p ${SEARXNG_PORT}:8080 \
    -v "${PWD}/searxng:/etc/searxng" \
    -e "BASE_URL=http://localhost:$SEARXNG_PORT/" \
    -e "INSTANCE_NAME=mcp-searxng" \
    --name mcp-searxng \
    searxng/searxng
```

Or if running with the SearXNG rate limiter set up:

```sh
docker network create searxng-network
# Redis used by rate limiter
docker run -d --name redis --network searxng-network redis:alpine
export SEARXNG_PORT=8888                     
docker run \
    -d -p ${SEARXNG_PORT}:8080 \
    -v "${PWD}/searxng:/etc/searxng" \
    -e "BASE_URL=http://localhost:$SEARXNG_PORT/" \
    -e "INSTANCE_NAME=mcp-searxng" \
    -e "REDIS_URL=redis://redis:6379/0" \
    --network searxng-network \
    --name mcp-searxng \
    searxng/searxng
```


Make sure it's running OK:

curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/search\?q\=test\&format\=json

Or to make sure SearXNG itself doesn't classify you as a bot:

curl -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "http://localhost:8888/search?q=test&format=json"

```sh
SEARXNG_ENDPOINT=http://localhost:8888/
# LM_STUDIO_ENDPOINT=llama-3.2-3b-instruct
LM_STUDIO_ENDPOINT=qwen2.5-14b-instruct-1m
python searxng_mcp_client.py
```

# Sample queries

Who just won the Carabao League cup final? Was there any history to the result?
