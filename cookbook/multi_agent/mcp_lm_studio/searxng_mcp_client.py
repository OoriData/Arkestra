# searxng_mcp_client.py

import subprocess
import json
import asyncio
from openai import OpenAI
import time
import sys
import structlog
from config import SEARXNG_ENDPOINT, LM_STUDIO_ENDPOINT, LM_STUDIO_MODEL

MPC_SERVER_TIMEOUT = 20.0  # Seconds

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
    log.info('Starting MCP server')
    try:
        process = subprocess.Popen(
            [sys.executable, 'searxng_mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Wait for the server to signal it's ready
        for line in process.stderr:
            if line.strip() == 'READY':
                break
            print(f'Server: {line.strip()}')  # Echo server startup messages

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

async def read_mcp_response(mcp_process):
    '''Read response from MCP server with improved error handling.'''
    response_str = await asyncio.wait_for(
        asyncio.to_thread(mcp_process.stdout.readline),
        timeout=MPC_SERVER_TIMEOUT
    )

    # Debug the raw response
    if not response_str:
        log.error('Empty response from MCP server')
        # Check if server is still running
        if mcp_process.poll() is not None:
            stderr = mcp_process.stderr.read()
            log.error('MCP server has terminated', 
                    returncode=mcp_process.returncode,
                    stderr=stderr)
            raise RuntimeError(f'MCP server terminated with code {mcp_process.returncode}: {stderr}')
        raise RuntimeError('MCP server returned empty response')

    log.debug('Raw response from MCP server', raw_response=response_str.strip())

    # Skip lines that don't look like JSON
    if not response_str.strip().startswith('{'):
        log.warning('Received non-JSON output, skipping', output=response_str.strip())
        return await read_mcp_response(mcp_process)

    return response_str

async def send_to_mcp(mcp_process, method, params=None, request_id=1):
    '''Send a request to the MCP server and get the response.'''
    log = structlog.get_logger()

    if mcp_process.poll() is not None:
        stderr = mcp_process.stderr.read()
        log.error('MCP server process has terminated',
                returncode=mcp_process.returncode,
                stderr=stderr)
        raise RuntimeError(f'MCP server process terminated with code {mcp_process.returncode}: {stderr}')

    request = {
        'jsonrpc': '2.0',
        'id': request_id,
        'method': method,
        'params': params or {}
    }

    request_str = json.dumps(request) + '\n'
    log.debug('Sending request to MCP server', request=request)

    try:
        # Write the request
        mcp_process.stdin.write(request_str)
        mcp_process.stdin.flush()

        # Read the response
        response_str = await read_mcp_response(mcp_process)

        try:
            response = json.loads(response_str)
            log.debug('Parsed response from MCP server', response=response)
            return response
        except json.JSONDecodeError as e:
            log.error('Failed to parse JSON response', 
                    error=str(e), 
                    raw_response=response_str)
            # Check if there's error output
            if mcp_process.poll() is not None:
                stderr = mcp_process.stderr.read()
                log.error('Server stderr', stderr=stderr)
            raise RuntimeError(f'Invalid JSON response: {response_str}')

    except asyncio.TimeoutError:
        log.error('Timeout waiting for MCP server response', method=method)
        raise
    except Exception as e:
        log.exception('Error communicating with MCP server',
                    error=str(e), method=method)
        raise

async def initialize_mcp(mcp_process):
    '''Initialize the MCP connection.'''
    log.info('Initializing MCP connection')

    # Check if the server is still running
    if mcp_process.poll() is not None:
        stderr = mcp_process.stderr.read()
        log.error('MCP server has terminated before initialization', 
                returncode=mcp_process.returncode,
                stderr=stderr)
        raise RuntimeError(f'MCP server terminated with code {mcp_process.returncode}: {stderr}')

    # Prepare initialization parameters
    params = {
        'protocolVersion': '0.1.0',
        'capabilities': {},
        'clientInfo': {
            'name': 'SearXNG-MCP-Client',
            'version': '1.0.0'
        }
    }

    # Send initialization request
    response = await send_to_mcp(mcp_process, 'initialize', params)
    if 'error' in response:
        log.error('MCP initialization failed', error=response['error'])
        raise RuntimeError(f'MCP initialization failed: {response['error']}')

    log.info('MCP connection initialized successfully')
    return response

async def handle_ping(mcp_process):
    '''Send a ping to the MCP server.'''
    log.debug('Sending ping to MCP server')
    response = await send_to_mcp(mcp_process, 'ping')
    return response

def create_llm_client():
    '''Create a client for LM Studio.'''
    log.info('Creating LLM client')
    return OpenAI(base_url=LM_STUDIO_ENDPOINT, api_key='lm-studio')

def define_tools():
    '''Define the search tool for the LLM.'''
    log.debug('Defining tools')
    return [
        {
            'type': 'function',
            'function': {
                'name': 'search',
                'description': 'Search the web using a local SearXNG instance',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'The search query string'
                        },
                        'category': {
                            'type': 'string',
                            'description': 'Search category (general, images, news, etc.)'
                        },
                        'language': {
                            'type': 'string',
                            'description': 'Language code for results'
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return'
                        }
                    },
                    'required': ['query']
                }
            }
        }
    ]

async def process_tool_calls(tool_calls, mcp_process):
    '''Process tool calls from the LLM.'''
    log = structlog.get_logger()
    results = []

    if mcp_process.poll() is not None:
        stderr = mcp_process.stderr.read()
        log.error('MCP server has terminated',
                returncode=mcp_process.returncode,
                stderr=stderr)
        return [{
            'tool_call_id': tool_call.id,
            'role': 'tool',
            'name': tool_call.function.name,
            'content': json.dumps({'error': 'MCP server has terminated'})
        } for tool_call in tool_calls]

    # Send a ping to maintain the session
    try:
        await handle_ping(mcp_process)
    except Exception as e:
        log.warning('Failed to ping MCP server', error=str(e))

    for tool_call in tool_calls:
        function = tool_call.function
        method = function.name
        try:
            params = json.loads(function.arguments)
            log.info('Processing tool call',
                    method=method,
                    tool_call_id=tool_call.id,
                    params=params)

            # For the search method, use the MCP protocol format
            if method == 'search':
                response = await send_to_mcp(mcp_process, 'tools/call', {
                    'name': 'search',
                    'arguments': params
                })
            else:
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

async def keep_alive_ping(mcp_process, interval=15):
    '''Send periodic pings to keep the MCP connection alive.'''
    while True:
        try:
            await asyncio.sleep(interval)
            if mcp_process.poll() is None:  # Only ping if server is still running
                await handle_ping(mcp_process)
            else:
                log.error('MCP server has terminated during keep-alive ping')
                break
        except Exception as e:
            log.warning('Keep-alive ping failed', error=str(e))
            # Don't break the loop on failure, just log and continue

async def main():
    '''Main function to run the program.'''
    log.info('Starting SearXNG MCP Client')

    # Start MCP server
    try:
        mcp_process = start_mcp_server()
        print(f'MCP server started - Using SearXNG endpoint: {SEARXNG_ENDPOINT}')
    except Exception as e:
        log.error('Failed to start MCP server', error=str(e))
        print(f'Failed to start MCP server: {str(e)}')
        return

    ping_task = None

    try:
        # Initialize the MCP connection
        print('Initializing MCP connection...')
        await initialize_mcp(mcp_process)
        print('MCP connection initialized successfully')

        # First ping to verify connection
        print('Sending initial ping...')
        ping_response = await handle_ping(mcp_process)
        print(f'Initial ping response: {ping_response}')

        # Start keep-alive ping task
        ping_task = asyncio.create_task(keep_alive_ping(mcp_process))

        # Create LLM client
        client = create_llm_client()
        print('LLM client created')

        # Start chat loop
        while True:
            user_input = input('\nYou: ')
            if user_input.lower() in ['exit', 'quit', 'q']:
                break

            # Chat with LLM
            messages = [{'role': 'user', 'content': user_input}]

            while True:
                try:
                    response = client.chat.completions.create(
                        model=LM_STUDIO_MODEL,
                        messages=messages,
                        tools=define_tools(),
                        tool_choice='auto'
                    )

                    assistant_message = response.choices[0].message
                    messages.append({'role': 'assistant', 'content': assistant_message.content})

                    print(f'Assistant: {assistant_message.content or '[No content, using tools]'}')

                    if assistant_message.tool_calls:
                        print('Searching...')
                        tool_results = await process_tool_calls(assistant_message.tool_calls, mcp_process)
                        messages.extend(tool_results)
                        continue

                    break

                except Exception as e:
                    log.exception('Error in chat loop', error=str(e))
                    print(f'Error: {str(e)}')
                    break

    except KeyboardInterrupt:
        log.info('Received keyboard interrupt, shutting down')
    except Exception as e:
        log.exception('Error in main function', error=str(e))
        print(f'Error: {str(e)}')
    finally:
        # Cancel ping task if it exists
        if ping_task:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

        log.info('Terminating MCP server')
        if mcp_process.poll() is None:  # Only terminate if still running
            mcp_process.terminate()
            try:
                mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mcp_process.kill()
        print('\nMCP server terminated')

if __name__ == '__main__':
    asyncio.run(main())
