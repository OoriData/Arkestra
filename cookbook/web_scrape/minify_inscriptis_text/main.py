import sys
import fire
import traceback
import re2 as re

import httpx
import tiktoken
from minify_html import minify
from inscriptis import get_text
from selectolax.parser import HTMLParser


from toolio import load_or_connect, response_text

from arkestra.components.prompt import load_loom

LANG = load_loom('lang.toml')

TAGS_TO_REMOVE = ['script', 'style']


def process_html_with_links(tree):    
    # Find all 'a' tags and add custom markers so the link URLs are preserved
    for a_tag in tree.css('a'):
        href = a_tag.attributes.get('href', '')
        if href:
            a_tag.insert_before(f'[LINK_START:{href}]')
            a_tag.insert_after('[LINK_END]')
    
    # Convert to text using inscriptis
    text = get_text(tree.html)
    
    # Replace custom markers with Markdown-style links
    text = re.sub(r'\[LINK_START:(.*?)\](.*?)\[LINK_END\]', r'[\2](\1)', text)
    
    return text


def process_text(html):
    if isinstance(html, bytes):
        html = html.decode('utf-8')
    try:
        html = minify(html)
    except Exception as e:
        print(traceback.format_exception(e), file=sys.stderr)

    tree = HTMLParser(html)
    for tag in TAGS_TO_REMOVE:
        for elem in tree.css(tag):
            elem.decompose()
    text = process_html_with_links(tree)

    # text = get_text(post_processed_html_text)
    # print(text)
    return text


async def async_main(url, model='mlx-community/Mistral-Nemo-Instruct-2407-4bit', max_token_count=7000):
    llm = load_or_connect(model)
    with open('product.schema.json') as fp:
        schema = fp.read()

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        text = process_text(resp.content)

    encoding = tiktoken.get_encoding("cl100k_base")  # Token encoding
    tokens = encoding.encode(text)  # Encode text into tokens
    token_count = len(tokens)
    print(token_count)

    if token_count > max_token_count:
        print(f'Input text {token_count} tokens is larger than the set maximum.')
        return

    msgs = [{'role': 'user', 'content': LANG['product_extract'].format(webpage_text=text)}]
    print('Handing page over to the LLM for analysis')
    rt = await response_text(llm.complete(msgs, json_schema=schema, max_tokens=2048))
    print(rt)


if __name__ == '__main__':
    fire.Fire(async_main)
