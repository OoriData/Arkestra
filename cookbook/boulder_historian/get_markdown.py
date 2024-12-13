'''
Just pulls the data from https://www.bouldercoloradousa.com/travel-info/boulder-history/

Note: Docker not working ATM (playwright probs)
❯ docker build -t boulder-historian .
❯ docker run boulder-historian > boulder_history.md
'''

import fire
import asyncio
from crawl4ai import AsyncWebCrawler


async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url='https://www.bouldercoloradousa.com/travel-info/boulder-history/')
        md = result.markdown
    print(md)


if __name__ == '__main__':
    # fire.Fire({'main': main})
    fire.Fire(main)
