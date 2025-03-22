# searxng_mcp_server.py

from mcp.server.fastmcp import FastMCP as MCP
import httpx
import json
import structlog
import sys
from config import SEARXNG_ENDPOINT

# Configure structlog for debugging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
)

log = structlog.get_logger()

# Initialize MCP server with debug logging
mcp = MCP(
    name='SearXNGServer',
    version='1.0.0',
    debug=True,  # Enable debug mode
    log=log
)

@mcp.tool('search')
async def search(
    query: str,
    category: str = 'general',
    language: str = 'en',
    max_results: int = 10
) -> dict:
    '''
    Search the web using a local SearXNG instance.

    Args:
        query: The search query string
        category: Search category (general, images, news, etc.)
        language: Language code for results
        max_results: Maximum number of results to return

    Returns:
        Dictionary containing search results
    '''
    log.info('Performing search', query=query, category=category, language=language)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                SEARXNG_ENDPOINT,
                params={
                    'q': query,
                    'categories': category,
                    'language': language,
                    'format': 'json',
                    'max_results': max_results
                },
                headers={'User-Agent': 'SearXNG-MCP-Client/1.0'},
                timeout=30.0
            )

            if response.status_code != 200:
                log.error('SearXNG error', status_code=response.status_code)
                return {'error': f'SearXNG returned status {response.status_code}'}

            results = response.json()
            return {
                'query': query,
                'results_count': len(results.get('results', [])),
                'results': results.get('results', [])[:max_results]
            }

        except httpx.RequestError as e:
            log.error('Network error', error=str(e))
            return {'error': f'Network error: {str(e)}'}
        except json.JSONDecodeError as e:
            log.error('Invalid JSON response', error=str(e))
            return {'error': 'Invalid response from SearXNG'}


if __name__ == '__main__':
    print(f'Starting SearXNG MCP Server - Using endpoint: {SEARXNG_ENDPOINT}', file=sys.stderr)
    log.info('Starting SearXNG MCP Server', endpoint=SEARXNG_ENDPOINT)

    try:
        # mcp.run(transport='sse', host='0.0.0.0', port=8000)
        mcp.run(transport='stdio')
    except BaseExceptionGroup as eg:
        log.error('Unhandled exception group', exceptions=eg.exceptions)
        sys.exit(1)
    except Exception as e:  # Catch-all for other exceptions
        log.error('Critical server error', error=str(e))
        sys.exit(1)
