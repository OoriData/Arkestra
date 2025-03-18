# searxng_mcp_server.py

from mcp.server.fastmcp import FastMCP as MCP
import requests
import json
import structlog
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
    try:
        params = {
            'q': query,
            'categories': category,
            'language': language,
            'format': 'json',
            'max_results': max_results
        }

        response = requests.get(
            SEARXNG_ENDPOINT,
            params=params,
            headers={'User-Agent': 'SearXNG-MCP-Client/1.0'},
            timeout=30  # Add timeout
        )

        if response.status_code != 200:
            log.error('SearXNG error', status_code=response.status_code, response=response.text)
            return {
                'error': f'SearXNG returned status code {response.status_code}',
                'details': response.text
            }

        results = response.json()
        log.info('Search completed', results_count=len(results.get('results', [])))
        return {
            'query': query,
            'results_count': len(results.get('results', [])),
            'results': results.get('results', [])[:max_results]
        }

    except Exception as e:
        log.exception('Error performing search', error=str(e))
        return {
            'error': f'Error performing search: {str(e)}'
        }


if __name__ == '__main__':
    import sys
    print(f'Starting SearXNG MCP Server - Using endpoint: {SEARXNG_ENDPOINT}', file=sys.stderr)
    log.info('Starting SearXNG MCP Server', endpoint=SEARXNG_ENDPOINT)

    print('READY', file=sys.stderr)  # Signal ready on stderr

    mcp.run(transport='stdio')
