# from fastmcp import MCP, Tool
import sys
import json
from mcp.server.fastmcp import FastMCP as MCP

mcp = MCP(name='WeatherServer', version='1.0.0')

@mcp.tool('get-forecast')
async def get_forecast(location: str, days: int = 1):
    # In a real implementation, you would call a weather API here
    forecast = f'Weather forecast for {location} for the next {days} day(s): Sunny, 75°F'
    return forecast

if __name__ == '__main__':
    # For debugging, you can also add basic stdin handling to test
    # This allows you to test the server independently
    if not sys.stdin.isatty():
        try:
            request = json.loads(sys.stdin.readline())
            if request.get("type") == "invoke" and request.get("name") == "get-forecast":
                input_data = request.get("input", {})
                location = input_data.get("location", "unknown")
                days = input_data.get("days", 1)
                result = {
                    "type": "response",
                    "id": request.get("id", ""),
                    "output": f'Weather forecast for {location} for the next {days} day(s): Sunny, 75°F'
                }
                print(json.dumps(result))
                sys.exit(0)
        except json.JSONDecodeError:
            pass
            
    # Default MCP protocol via stdio
    mcp.run(transport='stdio')
