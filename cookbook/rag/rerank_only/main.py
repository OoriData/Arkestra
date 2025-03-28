'''Simple RAG demo with AnswerDotAI rerankers'''
import os
from typing import List

import fire
from rerankers import Reranker
from toolio.client import struct_mlx_chat_api
from ogbujipt.llm_wrapper import prompt_to_chat

# Following because not all GPUs support MPS, and you might get NotImplementedError
# os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# fire.core.INSPECTOR_THEME = 'dark'

# 'cpu', 'cuda' or 'mps'
DEVICE = os.getenv('INFERENCE_DEVICE', 'cpu')
RERANK_API_KEY = os.getenv('RERANK_API_KEY')

DEFAULT_DOCS = [
    "Machine learning is transforming artificial intelligence research.",
    "Neural networks are a key component of deep learning systems.",
    "Transformers have revolutionized natural language processing.",
    "Reinforcement learning enables adaptive AI agents.",
    "Computer vision relies on convolutional neural networks.",
    "Generative AI models like GPT have changed content creation.",
]

DEFAULT_QUERY = "Tell me about advances in AI technology"
# MODEL_NAME = 'answerdotai/answerai-colbert-small-v1'
MODEL_NAME = 'cross-encoder'
# MODEL_NAME = 'flashrank'
# MODEL_NAME = 'cohere'


async def query_with_reranking(query: str = DEFAULT_QUERY, docs: List[str] = DEFAULT_DOCS):
    '''
    Process query with reranking-enhanced RAG

    Args:
        query: User question/request
        docs: List of document texts to search
    '''
    # Initialize components
    reranker = Reranker(model_name=MODEL_NAME, device=DEVICE, api_key=RERANK_API_KEY)
    # Can't use device for API-based rerankers
    # reranker = Reranker(model_name=MODEL_NAME, api_key=RERANK_API_KEY)
    llm = struct_mlx_chat_api(base_url=os.environ.get('TOOLIO_BASE_URL', 'http://localhost:8000'))

    # Rerank documents
    ranked = reranker.rank(query=query, docs=docs)
    top_docs = [d.text for d in ranked.top_k(3)]  # Get top 3 relevant docs

    import pprint; pprint.pprint(top_docs)

    # Build LLM prompt
    prompt = f'''Answer this query: {query}

    Context:
    {" ".join(top_docs)}
    '''

    # Generate response
    response = await llm(prompt_to_chat(prompt))
    # return response.first_choice_text
    return response


if __name__ == '__main__':
    # fire.Fire({
    #     'query': query_with_reranking
    # })
    fire.Fire(query_with_reranking)
