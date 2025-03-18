'''
Fake MCP Client for LM Studio

```
# LM_STUDIO_ENDPOINT="http://localhost:1234/v1" LM_STUDIO_MODEL="lmstudio-community/llama-3.2-1b-instruct" python fake_mcp_client.py
LM_STUDIO_ENDPOINT="http://localhost:1234/v1" LM_STUDIO_MODEL="qwen2.5-14b-instruct-1m" python fake_mcp_client.py
```
'''
import json
import subprocess
import sys
from openai import OpenAI
from config import LM_STUDIO_ENDPOINT, LM_STUDIO_MODEL

# Start LM Studio server and load a model first

# Connect to LM Studio server
client = OpenAI(base_url=LM_STUDIO_ENDPOINT, api_key='lm-studio')

# Define a tool - make sure the name matches the server definition
get_forecast_tool = {
    'type': 'function',
    'function': {
        'name': 'get-forecast',  # Match the name in the server
        'description': 'Get weather forecast for a location',
        'parameters': {
            'type': 'object',
            'properties': {
                'location': {
                    'type': 'string',
                    'description': 'The location to get weather for'
                },
                'days': {
                    'type': 'number',
                    'description': 'Number of days to forecast'
                }
            },
            'required': ['location']
        }
    }
}

# Start a conversation
messages = [{'role': 'user', 'content': 'What\'s the weather like in San Francisco today?'}]

# First request to get tool call
response = client.chat.completions.create(
    model=LM_STUDIO_MODEL,
    messages=messages,
    tools=[get_forecast_tool],
    tool_choice='auto'  # Explicitly request tool use when applicable
)

print('Initial response:', response)
assistant_message = response.choices[0].message
messages.append(assistant_message)  # Add assistant's response to conversation history

# Check if there's a tool call
if assistant_message.tool_calls:
    # Loop through each tool call (there might be multiple)
    for tool_call in assistant_message.tool_calls:
        # Get function name and arguments
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f'\nTool call requested: {function_name}')
        print(f'Arguments: {function_args}')
        
        # Execute MCP server call via subprocess
        if function_name == 'get-forecast':
            # We'll use the server directly via subprocess
            cmd = ['python', 'fake_mcp_server.py']
            
            # Create stdin data in MCP format
            stdin_data = {
                'type': 'invoke',
                'id': tool_call.id,
                'name': function_name,
                'input': function_args
            }
            
            # Call the MCP server
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(json.dumps(stdin_data) + '\n')
            print(f'Server stderr: {stderr.strip()}')
            
            try:
                result = json.loads(stdout)
                tool_result = result.get('output', 'No output returned')
            except json.JSONDecodeError:
                tool_result = f'Error parsing server response: {stdout}'
        else:
            tool_result = f'Unknown function: {function_name}'
        
        # Add tool response to messages
        messages.append({
            'role': 'tool',
            'tool_call_id': tool_call.id,
            'name': function_name,
            'content': str(tool_result)
        })

    # Get a new response from the model with the tool results
    final_response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        messages=messages
    )
    
    print('\nFinal response after tool use:')
    print(final_response.choices[0].message.content)
else:
    print('\nThe model didn\'t choose to use the tool.')
