# demo/reddit_summarizer/main.py
'''
Summarize the most interesting Reddit posts

Uses:
* [AsyncPRAW](https://asyncpraw.readthedocs.io/en/stable) - Reddit API
* [python-fire](https://github.com/google/python-fire) - Convenient CLI

First set up your environment & secrets. Useful resource: https://huggingface.co/blog/ucheog/separate-env-setup-from-code

You need [Reddit app ID & Secrets](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps)

Give the app a name. Easiest to just make it script-type.

Following assumes using 1passwd for secrets

```sh
pip install -r requirements.txt

op run --env-file=.env -- python main.py summarize_hot
```
'''
import os
import logging
# from pathlib import Path
import ssl

import aiohttp
import asyncpraw

import fire
from ogbujipt.llm_wrapper import prompt_to_chat
from toolio.client import struct_mlx_chat_api

# <platform>:<app ID>:<version string> (by u/<Reddit username>
USER_AGENT = 'Python:Arkestra Agent:v0.1.0 (by u/CodeGriot'

SUBREDDIT = 'LocalLLaMA'

TOOLIO_BASE_URL = 'http://localhost:8000'

PROMPT = '''\
Here is a list of the top ten hottest post titles in the {subreddit} subreddit:

=== BEGIN POST TITLES
{titles}
=== END POST TITLES

Based on this, please provide a summary of the interesting topics of the day for a casual audience.
'''

logging.basicConfig(level=logging.INFO)  # =logging.DEBUG =logging.INFO =logging.WARNING
logging.getLogger().setLevel('INFO')  # 'INFO', etc. Seems redundant, but is necessary. Python logging is quirky
logger = logging.getLogger(__name__)

# Need this crap to avoid self-signed cert errors (really annoying, BTW!)
ssl_ctx = ssl.create_default_context(cafile=os.environ.get('CERT_FILE'))

async def summarize_host(subreddit: str):
    '''
    sources - Path (in string form) to directory full of materials to index
    '''
    with aiohttp.TCPConnector(ssl=ssl_ctx) as conn:
        session = aiohttp.ClientSession(connector=conn)

        reddit = asyncpraw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent=USER_AGENT,
            requestor_kwargs={'session': session},  # Custom HTTP session
        )

        subreddit_api = await reddit.subreddit(subreddit, fetch=True)
        posts = []
        async for submission in subreddit_api.hot(limit=20):  # , time_filter="day"
            print(submission.title)
            if submission.stickied:  # Pinned post
                 continue
            posts.append(submission)
            # post.id  # id
            # post.selftext  # body

    titles = [post.title for post in posts]

    prompt = PROMPT.format(subreddit=subreddit, titles='  * ' + '\n  * '.join(titles))
    llm = struct_mlx_chat_api(base_url=TOOLIO_BASE_URL)
    messages = prompt_to_chat(prompt)
    print(prompt)
    print('='*40)

    # resp = await llm(messages, json_schema=response_schema, trip_timeout=90)
    resp = await llm(messages, trip_timeout=90)
    print(f'LLM response:\n {resp.first_choice_text}')


if __name__ == '__main__':
    fire.Fire({
        'summarize_hot': summarize_host
    })
