import os
import pickle
import pprint
import warnings

import pandas as pd
import numpy as np
import tiktoken

from openai import OpenAI

# Old; no longer in OpeAI lib
# from openai.embeddings_utils import get_embedding, cosine_similarity

import fire
from sentence_transformers import SentenceTransformer
from ogbujipt.text_helper import text_split_fuzzy
from arkestra.metrics.textdiff_dataviz import html_table_viz, similarities_heatmap, plotly_3d_viz

OPENAI_EMB_MODEL = "text-embedding-3-small"
OPENAI_EMB_MODEL_ENC = "cl100k_base"  # embedding encoding
OPENAI_MAX_TOKENS = 8000  # maximum for text-embedding-3-small is 8191

MODELS_IN = ["all-MiniLM-L6-v2", "dunzhang/stella_en_1.5B_v5"]
# MODELS_IN = ["all-MiniLM-L6-v2"]
# Considered "jinaai/jina-embeddings-v3", but it seems to require RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = True
# Or `model = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)`
# Will require a later on proper security review
MODELS = {}
for modname in MODELS_IN:
    MODELS[modname.split('/')[-1]] = SentenceTransformer(modname)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 500

# Path to the local cache file
CACHE_PATH = "embedding_cache.pkl"

OAI_CLIENT = OpenAI()

# Load cache if it exists
if os.path.exists(CACHE_PATH):
    with open(CACHE_PATH, "rb") as f:
        embedding_cache = pickle.load(f)
else:
    embedding_cache = {}


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_embedding_cached(text, model=OPENAI_EMB_MODEL):
    # Check if embedding already exists in cache
    if text in embedding_cache:
        return embedding_cache[text]

    # Otherwise, fetch the embedding from OpenAI API and cache it
    embedding = OAI_CLIENT.embeddings.create(input = [text], model=model).data[0].embedding
    embedding_cache[text] = embedding

    # Save updated cache to file
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(embedding_cache, f)
    
    return embedding


def search_embs(text_embs, query, n=3):
    '''
    Based on OpenAI docs
    res = search_reviews(df, 'delicious beans', n=3)
    '''
    # Use cached embedding function
    q_emb = get_embedding_cached(query)
    similarities = [(t, cosine_similarity(e, q_emb)) for (t, e) in text_embs]
    similarities = similarities.sort(reverse=True)
    result = similarities[:n]
    return result


def main(docfile, query_file, html_table=False, sim_heatmap=False, dim3=False):
    if not any((html_table, sim_heatmap, dim3)):
        warnings.warn("No output visualizations specified. Choose some combo of --html-table, --sim-heatmap, or --dim3")
    with open(docfile, 'r') as fp:
        md = fp.read()
    with open(query_file, 'r') as fp:
        queries = fp.readlines()
    queries = [q for q in queries if not q.startswith('#')]
    # model = MODELS[MODELS_IN[0]]
    reftexts = []
    for i, s in enumerate(text_split_fuzzy(md, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separator=r'\n\n')):
        reftexts.append(s)

    similarities_dict = {}
    
    for modname, model in MODELS.items():
        embeddings1 = model.encode(reftexts)
        embeddings2 = model.encode(queries)
        similarities = model.similarity(embeddings1, embeddings2)
        
        # Choose your visualization method:
        if sim_heatmap:
            similarities_heatmap(reftexts, queries, similarities, modname)  # Heatmap
        if dim3:
            plotly_3d_viz(reftexts, queries, similarities, modname)  # 3D Plot

        similarities_dict[modname] = similarities
        # # Output the pairs with their score (maybe add a --plain-text option?)
        # for idx_i, sentence1 in enumerate(reftexts):
        #     print(sentence1)
        #     for idx_j, sentence2 in enumerate(target_texts):
        #         print(f" - {sentence2: <30}: {similarities[idx_i][idx_j]:.4f}")
    
    # Generate HTML visualization with all models
    if html_table:
        html_table_viz(reftexts, queries, similarities_dict)


if __name__ == "__main__":
    fire.Fire(main)
