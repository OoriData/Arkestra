# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.website
'''
Common components for getting content from the web
'''
try:
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
except ImportError:
    raise ImportError(
        'Requires playwright_stealth. Possible fix: `pip install playwright_stealth`; then `playwright install`')

try:
    from markdownify import markdownify as md
except ImportError:
    raise ImportError('Requires markdownify. Possible fix: `pip install markdownify`')


async def load_page(url: str) -> str:
    '''
    Basic single web page loader, using browser engine to support dynamic DOM features

    >>> from arkestra.components.website import load_page
    >>> content = await load_page(url)
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()  # New browser context
        page = await ctx.new_page()
        await stealth_async(page)

        # Navigate to URL
        # await page.route('**/*.{png,jpg,jpeg}', lambda route: route.abort()) # Can speed up requests
        await page.goto(url)

        # Wait for dynamically loaded content
        await page.wait_for_load_state('domcontentloaded')
        content = await page.content()

        await browser.close()
        return content
