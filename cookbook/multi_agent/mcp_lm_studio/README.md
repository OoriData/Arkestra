Integrating MCP with Local LLMs: A Guide for LM Studio and MLX

Demo exploring how to use the Model Context Protocol (MCP) with local LLMs using platforms like LM Studio and MLX on Mac.

## Introduction to MCP and Local LLMs

The MCP has emerged as a standardized way for AI applications to interact with external systems. [It provides a universal framework](https://www.descope.com/learn/post/mcp) that allows LLMs to access tools, resources, and contextual information beyond their training data. When combined with locally-run LLMs, this creates powerful, privacy-preserving AI systems that can interact with your computer and external services without sending sensitive data to third-party servers.

### What is MCP?

MCP uses a client-server architecture partially inspired by the Language Server Protocol (LSP). Core components include:

1. Host applications: LLMs that interact with users and initiate connections
2. MCP clients: Components integrated within host applications that translate between the host's requirements and the MCP
3. MCP servers: Services that add context and capabilities, exposing specific functions to AI applications
4. Transport layer: Communication mechanisms between clients and servers (STDIO for local use, HTTP+SSE for remote connections)

All communication in MCP uses JSON-RPC 2.0 as the underlying message standard, providing a structured format for requests, responses and notifications.

## Local LLM options

### LM Studio

LM Studio is a comprehensive application that allows you to discover, download, and run a variety of LLMs locally. It provides both a chat interface and a local inference server that mimics OpenAI's API.

To get started with LM Studio:

1. Download and install LM Studio from their website
2. Browse and download models like Llama 3, Mistral Small, Qwen or one of the Deepseek distills
3. Use the chat interface directly or run LM Studio as a local server

Basic Python example using the LM Studio SDK:

```python
import lmstudio as lms

# Initialize a model
model = lms.llm("llama-3.2-1b-instruct")

# Generate text
result = model.respond("What is the meaning of life?")
print(result)
```

The [Python SDK](https://lmstudio.ai/docs/python) provides a convenient way to interact with LM Studio's capabilities programmatically.

Video resource: [LM Studio: How to Run a Local Inference Server-with Python code-Part 1](https://www.youtube.com/watch?v=1LdrF0xKnjc)

### MLX

MLX allows running models locally through the MLXPipeline class, with access to over 150 open-source models available on Hugging Face.

To use MLX:

1. Install required packages:
```
pip install --upgrade mlx-lm transformers huggingface_hub
```

2. Load and use a model:
```python
from mlx_lm import load, generate

# Load a model
model, tokenizer = load("mlx-community/quantized-gemma-2b-it")

# Generate text
prompt = "What is the meaning of life?"
messages = [{"role": "user", "content": prompt}]
prompt = tokenizer.apply_chat_template(
    messages, 
    add_generation_prompt=True
)
text = generate(model, tokenizer, prompt=prompt, verbose=True)
print(text)
```

[The MLX-LM package](https://github.com/ml-explore/mlx-lm) of MLX provides both command-line tools and a Python API for generating text and chatting with local models.

## Creating MCP Servers

[MCP servers provide three main capability types](https://modelcontextprotocol.io/quickstart/server): Resources (file-like data), Tools (functions callable by LLMs), and Prompts (templates for specific tasks).

### Python MCP Server Example

Creating an MCP server with Python is straightforward using libraries like FastMCP:

```python
from fastmcp import MCP, Tool

mcp = MCP(name="WeatherServer", version="1.0.0")

@mcp.tool("get-forecast")
async def get_forecast(location: str, days: int = 1):
    # In a real implementation, you would call a weather API here
    forecast = f"Weather forecast for {location} for the next {days} day(s): Sunny, 75°F"
    return forecast

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

This example creates a simple weather server that exposes a tool for getting forecasts.

Vid resource: ["Learn MCP Servers with Python (EASY)"](https://www.youtube.com/watch?v=Ek8JHgZtmcI)

## Connecting MCP to Local LLMs using LM Studio's Tool Support

[LM Studio supports external tool use through its REST API](https://lmstudio.ai/docs/app/api/tools), similar to OpenAI's function calling:

```python
from openai import OpenAI

# Start LM Studio server and load a model first

# Connect to LM Studio server
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Define a tool
get_forecast_tool = {
    "type": "function",
    "function": {
        "name": "get_forecast",
        "description": "Get weather forecast for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather for"
                },
                "days": {
                    "type": "number",
                    "description": "Number of days to forecast"
                }
            },
            "required": ["location"]
        }
    }
}

# Chat completion with tool
response = client.chat.completions.create(
    model="lmstudio-community/llama-3.2-1b-instruct",
    messages=[{"role": "user", "content": "What's the weather like in San Francisco?"}],
    tools=[get_forecast_tool]
)

print(response)
```

This approach allows LM Studio to recognize when tools should be called and handle their responses.

# On to our demos

The weather example is all over the 101 for this stuff. Let's push beyond that.

## Demo 1: Local file read access

A practical MCP server that allows LLMs to interact with your local filesystem. Tools for file operations enabling LLM queries like "any files from the past week over 1GB size?"

See README.local-file-read.md

## Demo 2: Web search with SearXNG

See README.searxng.md

# Overall MCP Advanced Features and Future Directions

1. **Multi-tool routing**: Allowing the LLM to choose from multiple MCP servers based on query type?
2. **Resource handling**: MCP resources & how they can provide [file-like access to external data](https://modelcontextprotocol.io/quickstart/server)
3. **Structured output**: Toolio FTW!!!
4. **Integration with development environments**: Tools like Cursor [which already support MCP for enhanced coding assistance](https://www.perplexity.ai/search/i-want-to-do-a-quick-talk-demo-Te_ARjZvQhqf67gi8gTL5w)

# Appendix: Benefits of Local LLMs

Running LLMs locally offers significant advantages:

1. Privacy: All data remains on your device, crucial for handling sensitive information
2. Customizability: You can fine-tune models for specific domains or tasks
3. No internet dependency: Once set up, systems can operate entirely offline
4. Reduced costs: No need for API credits or subscription fees
