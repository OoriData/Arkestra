# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.prompt.notion
'''
Common components for prompt loading from Notion

Resources:
* https://developers.notion.com/docs/create-a-notion-integration
'''
# import os
import json
import httpx

# from ogbujipt import word_loom
from ogbujipt.word_loom import T

# NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_VERSION = '2022-06-28'  # See: https://developers.notion.com/reference/post-database-query
PAGES_PER_REQ = 100  # Max number of pages to get per HTTP request


class notion_loom_loader:
    '''
    >>> from arkestra.components.prompt.notion import notion_loom_loader
    >>> nl_loader = notion_loom_loader()
    >>> loom = nl_loader.load()
    '''
    def __init__(self, db_id, notion_token, prompt_id_field, prompt_text_field, params_field):
        self.db_id = db_id
        self.notion_token = notion_token
        self.prompt_id_field = prompt_id_field
        self.prompt_text_field = prompt_text_field
        self.params_field = params_field

    async def load(self):
        '''
        Load language info (e.g for prompts) from a Word Loom-like Notion DB

        fpath (str or Path) - path to Word Loom file
        relobj - Python object to use as base location for relative fpath, or more precisely the directory containing
            the file from which obj was loaded. Useful for loading Word Loom files included in Python packages

        '''
        loom = {}
        async for page in pages(self.db_id, self.notion_token):
            # assert page['object'] == 'page'
            page_id = page['id']
            # url = props['URL']['title'][0]['text']['content']
            # title = props['Title']['rich_text'][0]['text']['content']
            # published = props['Published']['date']['start']
            # published = datetime.fromisoformat(published)
            props = page['properties']
            try:
                prompt_id = props[self.prompt_id_field]
            except KeyError:
                raise ValueError(f'The prompt ID field name provided doesn\'t match a Notion page property')
            try:
                prompt_text = props[self.prompt_text_field]
            except KeyError:
                raise ValueError(f'The prompt text field name provided doesn\'t match a Notion page property')
            try:
                params = props[self.params_field]
            except KeyError:
                raise ValueError(f'The params field provided doesn\'t match a Notion page property')
            params = params['rich_text'][0]['plain_text'] if params['rich_text'] else ''
            params = [ p.strip() for p in params.split(',') ]
            prompt_id = prompt_id['title'][0]['plain_text']
            # rich_text or plain_text?
            loom[prompt_id] = T(prompt_text['rich_text'][0]['text']['content'], 'en', meta=None, markers=params)

        return loom


async def pages(db_id, notion_token, limit=None):
    '''
    Retrieve & yield all DB pages, or up to the limit, if given

    >>> from arkestra.components.prompt.notion import pages
    >>> async for p in pages(DB_ID, TOKEN):
    ...     print(p)
    ...     break
    '''
    url = f'https://api.notion.com/v1/databases/{db_id}/query'
    payload = json.dumps({'page_size': PAGES_PER_REQ})
    headers = {'Authorization': f'Bearer {notion_token}', 'Content-Type': 'application/json',
                'Notion-Version': NOTION_VERSION}

    async with httpx.AsyncClient() as client:
        yield_count = 0
        has_more = True
        start_cursor = None
        while (not limit or yield_count <= limit) and has_more:
            if start_cursor:
                payload['start_cursor'] = start_cursor
            resp = await client.post(url, data=payload, headers=headers)
            # print('Pulling: ', resp.url, 'with payload', payload)
            data = resp.json()
            if 'results' not in data:
                raise RuntimeError(f'Unexpected response: {resp.content}')
            has_more = data.get('has_more', False)
            if has_more:
                start_cursor = data['next_cursor']

            for result in data['results']:
                yield result
