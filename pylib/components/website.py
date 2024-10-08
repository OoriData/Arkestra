# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.website
'''
Common components for getting content from the web
'''
import urllib
try:
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
except ImportError:
    async_playwright = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from markdownify import markdownify as md
except ImportError:
    raise ImportError('Requires markdownify. Possible fix: `pip install markdownify`')

HTTP_OK = 200


async def load_page_aiohttp(url: str, acceptable_http_codes=None, user_agent=None, header_overrides=None) -> str:
    '''
    Basic single web page loader, using browser engine to support dynamic DOM features

    >>> from arkestra.components.website import load_page_aiohttp
    >>> content = await load_page_aiohttp(url)
    '''
    if aiohttp is None:
        raise ImportError(
            'Requires aiohttp. Possible fix: `pip install aiohttp`')

    # TODO: Session reuse, HTTP error handling, alternate headers, etc.
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=header_overrides) as resp:
            content = await resp.read()
        return content


async def load_page_playwright_stealth(url: str, acceptable_http_codes=None, user_agent=None, header_overrides=None) -> str:
    '''
    Basic single web page loader, using browser engine to support dynamic DOM features

    >>> from arkestra.components.website import load_page
    >>> content = await load_page(url)
    '''
    if async_playwright is None:
        raise ImportError(
            'Requires playwright_stealth. Possible fix: `pip install playwright_stealth`; then `playwright install`')

    if not acceptable_http_codes:
        acceptable_http_codes = [HTTP_OK]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=user_agent)  # New browser context
        page = await ctx.new_page()
        if header_overrides:
            await page.set_extra_http_headers(header_overrides)
        await stealth_async(page)

        # await page.route('**/*.{png,jpg,jpeg}', lambda route: route.abort()) # Can speed up requests
        response = await page.goto(url)  # Navigate to URL
        if response.status not in acceptable_http_codes:
            content = await page.content()
            # FIXME: Pass on headers (penult). See https://github.com/python/cpython/blob/main/Lib/urllib/error.py#L39
            raise urllib.error.HTTPError(url, response.status, content, None, None)

        # Wait for dynamically loaded content
        await page.wait_for_load_state('domcontentloaded')
        content = await page.content()

        await browser.close()
        return content


async def load_page_markdown(url: str, acceptable_http_codes=None, user_agent=None, header_overrides=None,
                             engine=load_page_aiohttp) -> str:
    '''
    Download HTML page loader, and convert to Markdown

    Can use multiple engines; `load_page_aiohttp` for simple page loading or load_page_playwright_stealth
    for more scraper sophistication

    >>> from arkestra.components.website import load_page_markdown
    >>> md_content = await load_page_markdown(url)
    '''
    content = await engine(url, acceptable_http_codes=acceptable_http_codes, user_agent=user_agent,
                              header_overrides=header_overrides)
    md_content = md(content)
    return md_content
