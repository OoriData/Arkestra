# cookbook/browserkit/tabluk/app.py
from litestar import Litestar, get, post, put, delete
from litestar.static_files import StaticFilesConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig
from litestar.static_files import create_static_files_router

from selectolax.parser import HTMLParser
# import asyncio

# from litestar.config.cors import CORSConfig

from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import webbrowser
import httpx
import asyncio
import uuid
from pathlib import Path

# Ensure data directory exists
data_dir = Path('data')
data_dir.mkdir(exist_ok=True)
tab_groups_file = data_dir / 'tab_groups.json'

# Initialize empty tab groups if file doesn't exist
if not tab_groups_file.exists():
    with open(tab_groups_file, 'w') as f:
        json.dump({}, f)

# I'd normally avoid Pydantic, but for this vibe-codey thing, OK—Uche
class TabLink(BaseModel):
    id: str
    url: str
    title: str

class TabGroup(BaseModel):
    id: str
    name: str
    links: List[TabLink]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

# ━━━━━━ ⬇ Helper functions ⬇ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_page_title(url: str) -> str:
    '''Fetch the actual title of a webpage using selectolax.'''
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                parser = HTMLParser(response.text)
                if title_tag := parser.css_first('title'):
                    print(f'GRIPPO!! {title_tag.text()}')
                    return title_tag.text().strip()
    except Exception as e:
        print(f'Error fetching title for {url}: {e}')

    # Fall back to hostname if we can't get the title
    from urllib.parse import urlparse
    return urlparse(url).netloc


def load_tab_groups() -> Dict[str, TabGroup]:
    with open(tab_groups_file, 'r') as f:
        data = json.load(f)
        return {group_id: TabGroup(**group_data) for group_id, group_data in data.items()}

def save_tab_groups(groups: Dict[str, TabGroup]):
    serializable_groups = {}
    for group_id, group in groups.items():
        if isinstance(group, TabGroup):
            serializable_groups[group_id] = group.model_dump()
        else:
            serializable_groups[group_id] = group  # Already a dict

    with open(tab_groups_file, 'w') as f:
        json.dump(serializable_groups, f, indent=2)

@get('/')
async def index() -> Template:
    return Template(template_name='index.html', context={})

@get('/api/groups')
async def get_groups() -> Dict[str, TabGroup]:
    return load_tab_groups()

@post('/api/groups')
async def create_group(data: dict) -> Dict[str, TabGroup]:
    groups = load_tab_groups()
    group_id = str(uuid.uuid4())
    new_group = TabGroup(
        id=group_id,
        name=data['name'],
        links=[]
    )
    groups[group_id] = new_group.dict()
    save_tab_groups(groups)
    return load_tab_groups()

@put('/api/groups/{group_id:str}')
async def update_group(group_id: str, data: dict) -> Dict[str, TabGroup]:
    groups = load_tab_groups()
    if group_id in groups:
        groups[group_id]['name'] = data['name']
        save_tab_groups(groups)
    return load_tab_groups()

@delete('/api/groups/{group_id:str}', status_code=200)
async def delete_group(group_id: str) -> Dict[str, TabGroup]:
    groups = load_tab_groups()
    if group_id in groups:
        del groups[group_id]
        save_tab_groups(groups)
    return load_tab_groups()

@post('/api/groups/{group_id:str}/links')
async def add_link(group_id: str, data: dict) -> Dict[str, TabGroup]:
    groups = load_tab_groups()
    if group_id in groups:
        url = data['url']
        # If no title provided, fetch the page title
        if not data.get('title'):
            data['title'] = await get_page_title(url)

        link_id = str(uuid.uuid4())
        new_link = TabLink(
            id=link_id,
            url=url,
            title=data['title']
        )

        if isinstance(groups[group_id], TabGroup):
            groups[group_id].links.append(new_link)
            groups[group_id] = groups[group_id].dict()
        else:
            groups[group_id].links.append(new_link.dict())

        save_tab_groups(groups)
    return load_tab_groups()

@delete('/api/groups/{group_id:str}/links/{link_id:str}', status_code=200)
async def delete_link(group_id: str, link_id: str) -> Dict[str, TabGroup]:
    groups = load_tab_groups()
    if group_id in groups:
        groups[group_id].links = [link for link in groups[group_id].links if link.id != link_id]
        save_tab_groups(groups)
    return load_tab_groups()

@post('/api/groups/{group_id:str}/launch')
async def launch_group(group_id: str) -> dict:
    groups = load_tab_groups()
    if group_id in groups:
        for link in groups[group_id].links:
            webbrowser.open_new_tab(link.url)
        return {'status': 'success', 'message': f'Launched {len(groups[group_id]['links'])} tabs'}
    return {'status': 'error', 'message': 'Group not found'}

@post('/api/chat')
async def chat(data: ChatRequest) -> ChatResponse:
    try:
        # Connect to LM Studio server (default port)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                'http://localhost:1234/v1/chat/completions',
                json={
                    'messages': [{'role': m.role, 'content': m.content} for m in data.messages],
                    'model': 'local-model',  # LM Studio will use whatever model is loaded
                    'temperature': 0.7,
                    'max_tokens': 500
                }
            )

            if response.status_code == 200:
                result = response.json()
                return ChatResponse(response=result['choices'][0]['message']['content'])
            else:
                return ChatResponse(response=f'Error: Unable to connect to LM Studio server. Status code: {response.status_code}')
    except Exception as e:
        return ChatResponse(response=f'Error: {str(e)}')

STATIC_DIR = Path('static')


app = Litestar(
    route_handlers=[
        index, get_groups, create_group, update_group, delete_group,
        add_link, delete_link, launch_group, chat,
        create_static_files_router(path="/static", directories=[STATIC_DIR])
    ],
    template_config=TemplateConfig(directory='templates', engine=JinjaTemplateEngine),
)
