# demo/simple_ogbujipt_pg_rag1.py
'''
Simple RAG demo using PGVector & Toolio

Uses:
* [OgbujiPT](https://github.com/OoriData/OgbujiPT) - Retrieval Augmentation phase via PGVector helper & for Generation
* [python-fire](https://github.com/google/python-fire) - Convenient CLI

First have a PG + PGVector instance available. Simple Docker formula:

```sh
docker pull pgvector/pgvector:pg16
docker run --name mock-postgres -p 5432:5432 -d pgvector/pgvector:pg16 \
    -e POSTGRES_USER=demo_user -e POSTGRES_PASSWORD="demo_password" -e POSTGRES_DB=demo_db
```

First set up your environment & secrets. Useful resource: https://huggingface.co/blog/ucheog/separate-env-setup-from-code

```sh
pip install toolio fire pgvector asyncpg docx2python PyPDF2 PyCryptodome
# pip install -r demo/requirements.txt  # Alternatively

python demo/simple_ogbujipt_pg_rag1.py prep
python demo/simple_ogbujipt_pg_rag1.py index --sources=simple_toolio_pg_rag1_files
python demo/simple_ogbujipt_pg_rag1.py query --prompt="Tell me something cool about Calabar"
python demo/simple_ogbujipt_pg_rag1.py clear  # To delete the DB
```

If, for example, you're using 1passwd for secrets, you might prep an `.env` file,
and prefix each command with `op run --env-file=.env -- ` , e.g.
`op run --env-file=.env -- python demo/simple_ogbujipt_pg_rag1.py prep`
'''
import os
import logging
from pathlib import Path

import fire
from sentence_transformers import SentenceTransformer  # May take a long time, the first time
from docx2python import docx2python
from PyPDF2 import PdfReader
from ogbujipt.embedding.pgvector import DataDB
from ogbujipt.text_helper import text_split_fuzzy
from ogbujipt.llm_wrapper import prompt_to_chat
from toolio.client import struct_mlx_chat_api

E_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

DB_PARAMS = {
    'embedding_model': E_MODEL,
    'table_name': 'ark_rag_demo',
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': os.environ.get('PG_PORT', 5432),
    'user': os.environ.get('PG_USER', 'demo_user'),
    'password': os.environ.get('PG_PASSWORD'),
    'db_name': os.environ.get('PG_DB_NAME', 'demo_db')
}

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

logging.basicConfig(level=logging.INFO)  # =logging.DEBUG =logging.INFO =logging.WARNING
logging.getLogger().setLevel('INFO')  # 'INFO', etc. Seems redundant, but is necessary. Python logging is quirky
logger = logging.getLogger(__name__)


async def index(sources: str):
    '''
    sources - Path (in string form) to directory full of materials to index
    '''
    sources = Path(sources)
    rag_db = await DataDB.from_conn_params(**DB_PARAMS)

    for fname in sources.iterdir():  # Use docs.glob(…) if you want to to be recursive
        # print(fname, fname.suffix)
        if fname.suffix in ['.doc', '.docx']:
            print('Processing as Word doc:', fname)
            with docx2python(fname) as docx_content:
                doctext = docx_content.text
        elif fname.suffix == '.pdf':
            pdf_reader = PdfReader(fname)
            doctext = ''.join((page.extract_text() for page in pdf_reader.pages))
        elif fname.suffix in ['.txt', '.md', '.mdx']:
            with open(fname) as docx_content:
                doctext = docx_content.read()
        chunks = text_split_fuzzy(doctext, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separator='\n')
        # Zip up text + metadata
        dataset = ((text, {'source': str(fname)}) for text in chunks)

        # metadata = {'title': 'DEMO', 'tags': ['x', 'y', 'z']}
        await rag_db.insert_many(dataset)


async def query(prompt: str, retrieved_k: int = 4, llm_api_base: str = 'http://localhost:8000', sys_prompt: str=''):
    '''Handle a RAG query'''
    rag_db = await DataDB.from_conn_params(**DB_PARAMS)
    llm = struct_mlx_chat_api(base_url=llm_api_base)
    if not sys_prompt:
        sys_prompt = '''\
You are a helpful assistant, who answers questions directly and as briefly as possible.
Consider the following context and answer the user\'s question.
If you cannot answer with the given context, just say so.\n\n
{retrieved_chunks}
'''
    results = await rag_db.search(text=prompt, limit=3)
    # print(list(results))
    retrieved_chunk_text = '\n\n'.join([d['content'] for d in results])
    messages = prompt_to_chat(prompt, system=sys_prompt.format(retrieved_chunks=retrieved_chunk_text))

    # resp = await llm(messages, json_schema=response_schema, trip_timeout=90)
    resp = await llm(messages, trip_timeout=90)
    print(f'LLM response: {resp.first_choice_text}')


async def clear():
    '''sources - Path to directory full of materials to index'''
    rag_db = await DataDB.from_conn_params(**DB_PARAMS)
    await rag_db.drop_table()
    logger.info('Database table removed')


async def prep():
    '''Initialize PG with PGVector'''
    rag_db = await DataDB.from_conn_params(**DB_PARAMS)
    await rag_db.create_table()
    logger.info('Database table setup complete')


if __name__ == '__main__':
    fire.Fire({
        'prep': prep,
        'index': index,
        'clear': clear,
        'query': query,
    })
