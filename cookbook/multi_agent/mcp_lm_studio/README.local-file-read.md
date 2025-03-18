This filesystem MCP server includes several tools designed to help LLMs interact with local files:

* `get-current-time`: Provides the current date/time for temporal queries
* `list-files`: Lists files in a directory with metadata
* `search-files`: Powerful search function with filtering options
* `get-file-info`: Detailed information about a specific file
* `recent-large-files`: Specialized tool for finding recent large files
* `file-preview`: Resource to preview file contents


## Security Features

* Path validation to prevent filesystem traversal attacks
* Root directory restrictions
* Size limits for file reading
* Error handling for permissions and file access issues

## Client Application

* Connects to both the MCP server and LM Studio
* Translates LLM tool calls to MCP server requests
* Manages the conversation flow with the LLM

## Using the System

Configure `ROOT_DIR` in the MCP server to point to the desired directory

Start LM Studio and load your preferred model

```sh
ROOT_DIR=~/Documents
python filesystem_mcp_server.py
```

Run the MCP server and client application

```sh
LM_STUDIO_ENDPOINT=llama-3.2-3b-instruct
ROOT_DIR=~/Documents
python local_llm_mcp_client.py
```

### Example Queries

* List the SOWs in my Documents folder
* Find any files from the past week over 1GB in size
* List all PDF files in my Documents folder
* What's the largest file in my Downloads folder?
* Show me the most recently modified files
* Give me a preview of the README.md file


## Implementation Notes

The MCP server uses STDIO for communication, which is ideal for local applications. For more complex scenarios, you could extend this to use HTTP+SSE. The file preview tool is limited to text files and has size restrictions.

# Extending the System

Ideas:

* Adding write capabilities (careful with security considerations!)
* Implementing file content analysis (e.g., summarization, keyword extraction)
