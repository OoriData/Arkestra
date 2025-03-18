'''
Local LLM MCP Client
'''

import subprocess
import json
import asyncio
from openai import OpenAI
import time
import sys
import structlog

from config import ROOT_DIR, LM_STUDIO_ENDPOINT, LM_STUDIO_MODEL

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
)
log = structlog.get_logger()


def start_mcp_server():
    '''Start the MCP server as a subprocess.'''
    log = structlog.get_logger()
    log.info('Starting MCP server')

    try:
        # Expects MCP server file in same dir as filesystem_mcp_server.py
        process = subprocess.Popen(
            [sys.executable, 'filesystem_mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Wait a moment to ensure the process starts correctly
        time.sleep(0.5)

        # Check if the process started successfully
        if process.poll() is not None:
            stderr = process.stderr.read()
            log.error('MCP server failed to start', 
                     returncode=process.returncode,
                     stderr=stderr)
            raise RuntimeError(f'MCP server failed to start: {stderr}')

        log.info('MCP server process started', pid=process.pid)
        return process
    except Exception as e:
        log.exception('Error starting MCP server', error=str(e))
        raise

async def send_to_mcp(mcp_process, method, params=None):
    '''Send a request to the MCP server and get the response.'''
    log = structlog.get_logger()

    # Check if process is still running
    if mcp_process.poll() is not None:
        log.error('MCP server process has terminated', 
                 returncode=mcp_process.returncode)
        stderr = mcp_process.stderr.read()
        log.error('MCP server stderr output', stderr=stderr)
        raise RuntimeError(f'MCP server process terminated with code {mcp_process.returncode}')

    request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': method,
        'params': params or {}
    }

    request_str = json.dumps(request) + '\n'
    log.debug('Sending request to MCP server', method=method, params=params)

    try:
        mcp_process.stdin.write(request_str)
        mcp_process.stdin.flush()

        # Add timeout to prevent hanging
        response_str = await asyncio.wait_for(
            asyncio.to_thread(mcp_process.stdout.readline),
            timeout=10.0
        )

        if not response_str:
            log.error('Empty response from MCP server', method=method)
            raise RuntimeError('MCP server returned empty response')

        response = json.loads(response_str)
        log.debug('Received response from MCP server', response=response)
        return response
    except BrokenPipeError:
        log.error('Broken pipe when communicating with MCP server', method=method)
        # Check if the server is still running
        if mcp_process.poll() is not None:
            stderr = mcp_process.stderr.read()
            log.error('MCP server has terminated', 
                     returncode=mcp_process.returncode, 
                     stderr=stderr)
        raise
    except asyncio.TimeoutError:
        log.error('Timeout waiting for MCP server response', method=method)
        raise
    except Exception as e:
        log.exception('Error communicating with MCP server', 
                     error=str(e), method=method)
        raise

def create_llm_client():
    '''Create a client for LM Studio.'''
    log.info('Creating LLM client')
    return OpenAI(base_url=LM_STUDIO_ENDPOINT, api_key='lm-studio')

def define_tools():
    '''Define the tools available for the LLM.'''
    log.debug('Defining tools')
    return [
        {
            'type': 'function',
            'function': {
                'name': 'get_current_time',
                'description': 'Get the current system time',
                'parameters': {
                    'type': 'object',
                    'properties': {}
                }
            }
        },
        {
            'type': 'function',
            'function': {
                'name': 'list_files',
                'description': 'List files in a directory',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'directory': {
                            'type': 'string',
                            'description': f'Path relative to {ROOT_DIR} or absolute path'
                        },
                        'recursive': {
                            'type': 'boolean',
                            'description': 'Whether to list files recursively'
                        },
                        'include_hidden': {
                            'type': 'boolean',
                            'description': 'Whether to include hidden files'
                        },
                        'max_depth': {
                            'type': 'integer',
                            'description': 'Maximum depth for recursive search'
                        }
                    }
                }
            }
        },
        {
            'type': 'function',
            'function': {
                'name': 'search_files',
                'description': 'Search for files matching criteria',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'pattern': {
                            'type': 'string',
                            'description': 'File pattern (e.g., "*.txt")'
                        },
                        'directory': {
                            'type': 'string',
                            'description': f'Directory to search in (relative to {ROOT_DIR} or absolute)'
                        },
                        'recursive': {
                            'type': 'boolean',
                            'description': 'Whether to search recursively'
                        },
                        'min_size': {
                            'type': 'integer',
                            'description': 'Minimum file size in bytes'
                        },
                        'max_size': {
                            'type': 'integer',
                            'description': 'Maximum file size in bytes'
                        },
                        'modified_after': {
                            'type': 'string',
                            'description': 'Files modified after this date (ISO format)'
                        },
                        'modified_before': {
                            'type': 'string',
                            'description': 'Files modified before this date (ISO format)'
                        },
                        'file_type': {
                            'type': 'string',
                            'description': 'Filter by file extension (e.g., "pdf")'
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return'
                        }
                    }
                }
            }
        },
        {
            'type': 'function',
            'function': {
                'name': 'get_file_info',
                'description': 'Get detailed information about a specific file',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'path': {
                            'type': 'string',
                            'description': f'Path to the file (relative to {ROOT_DIR} or absolute)'
                        }
                    },
                    'required': ['path']
                }
            }
        },
        {
            'type': 'function',
            'function': {
                'name': 'recent_large_files',
                'description': 'Find recent large files',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'directory': {
                            'type': 'string',
                            'description': f'Directory to search in (relative to {ROOT_DIR} or absolute)'
                        },
                        'days': {
                            'type': 'integer',
                            'description': 'How many days back to look'
                        },
                        'min_size_gb': {
                            'type': 'number',
                            'description': 'Minimum size in GB'
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of results'
                        }
                    }
                }
            }
        },
        {
            'type': 'function',
            'function': {
                'name': 'file_preview',
                'description': 'Get a preview of a file\'s contents',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'path': {
                            'type': 'string',
                            'description': f'Path to the file (relative to {ROOT_DIR} or absolute)'
                        },
                        'max_size': {
                            'type': 'integer',
                            'description': 'Maximum size in bytes to read'
                        }
                    },
                    'required': ['path']
                }
            }
        }
    ]

async def process_tool_calls(tool_calls, mcp_process):
    '''Process tool calls from the LLM.'''
    log = structlog.get_logger()
    results = []

    # First check if the MCP process is still running
    if mcp_process.poll() is not None:
        stderr = mcp_process.stderr.read()
        log.error('MCP server has terminated', 
                 returncode=mcp_process.returncode,
                 stderr=stderr)
        for tool_call in tool_calls:
            results.append({
                'tool_call_id': tool_call.id,
                'role': 'tool',
                'name': tool_call.function.name,
                'content': json.dumps({'error': 'MCP server has terminated'})
            })
        return results

    for tool_call in tool_calls:
        function = tool_call.function
        method = function.name

        try:
            params = json.loads(function.arguments)
            log.info('Processing tool call', 
                    method=method, 
                    tool_call_id=tool_call.id,
                    params=params)

            # Send the request to MCP server
            response = await send_to_mcp(mcp_process, method, params)

            if 'error' in response:
                log.error('MCP server returned error', 
                         error=response['error'], 
                         method=method)
                content = json.dumps({'error': response['error']})
            else:
                content = json.dumps(response['result'])

            results.append({
                'tool_call_id': tool_call.id,
                'role': 'tool',
                'name': method,
                'content': content
            })

        except Exception as e:
            log.exception('Error processing tool call', 
                         error=str(e), 
                         method=method)
            results.append({
                'tool_call_id': tool_call.id,
                'role': 'tool',
                'name': method,
                'content': json.dumps({'error': str(e)})
            })

    return results

async def chat_with_llm(client, mcp_process, user_input):
    '''Chat with the LLM using MCP tools.'''
    log.info('Starting chat with LLM', user_input=user_input)
    messages = [{'role': 'user', 'content': user_input}]

    while True:
        try:
            log.debug('Sending request to LLM', messages=messages)
            response = client.chat.completions.create(
                model=LM_STUDIO_MODEL,
                messages=messages,
                tools=define_tools(),
                tool_choice='auto'
            )

            assistant_message = response.choices[0].message
            log.info('Received response from LLM', 
                    content=assistant_message.content,
                    has_tool_calls=bool(assistant_message.tool_calls))

            messages.append({'role': 'assistant', 'content': assistant_message.content})

            # Print the assistant's response
            print(f'Assistant: {assistant_message.content or '[No content, using tools]'}')

            # Check if the assistant requested to use a tool
            if assistant_message.tool_calls:
                print('Using tools...')
                tool_results = await process_tool_calls(assistant_message.tool_calls, mcp_process)
                messages.extend(tool_results)

                # Log the tool results
                log.info('Tool results processed', count=len(tool_results))

                # Continue the conversation with tool results
                continue

            # If no tool calls, we're done
            break

        except Exception as e:
            log.exception('Error in chat loop', error=str(e))
            print(f'Error: {str(e)}')
            break

    return messages

async def main():
    '''Main function to run the program.'''
    log.info('Starting Local LLM MCP Client')

    # Start MCP server
    mcp_process = start_mcp_server()
    print('MCP server started')

    # Create LLM client
    client = create_llm_client()
    print('LLM client created')

    # Start chat loop
    try:
        while True:
            user_input = input('\nYou: ')
            if user_input.lower() in ['exit', 'quit', 'q']:
                break

            await chat_with_llm(client, mcp_process, user_input)
    except KeyboardInterrupt:
        log.info('Received keyboard interrupt, shutting down')
    except Exception as e:
        log.exception('Unexpected error in main loop', error=str(e))
    finally:
        # Cleanup
        log.info('Terminating MCP server')
        mcp_process.terminate()

        # Check if process ended cleanly
        try:
            mcp_process.wait(timeout=5)
            log.info('MCP server terminated')
        except subprocess.TimeoutExpired:
            log.warning('MCP server did not terminate gracefully, killing')
            mcp_process.kill()

        print('\nMCP server terminated')

if __name__ == '__main__':
    asyncio.run(main())
