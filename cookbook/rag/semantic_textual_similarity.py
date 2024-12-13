'''
Using SentenceTransformer to implement explicit Semantic Textual Similarity (STS), i.e. from a list of strings,
without delegating to a vector DB

Can specialize the sim function when the model is loaded, e.g.
model = SentenceTransformer(ST_MODEL_NAME, similarity_fn_name=SimilarityFunction.DOT_PRODUCT)

In which case use `model.similarity(embeddings, embeddings)`

You can also work with separate lists of texts: `model.similarity(embeddings1, embeddings2)`

See also: https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html
'''

import fire
from sentence_transformers import SentenceTransformer, util

# Pre-trained sentence transformer model name
ST_MODEL_NAME = 'all-MiniLM-L6-v2'
model = SentenceTransformer(ST_MODEL_NAME)


def semantic_similarity(sentences, sentences2=None):
    '''
    Calculate semantic similarity between sentences using native SentenceTransformer cosine similarity.
    
    Args:
        sentences (list): A list of sentences to compare
    
    Returns:
        torch.Tensor: A similarity matrix showing semantic similarities
    '''
    emb1 = model.encode(sentences)  # Generate embeddings for the sentences
    emb2 = emb1 if sentences2 is None else model.encode(sentences)
    similarity_matrix = util.cos_sim(emb1, emb2)  # Calculate cosine similarity
    
    return similarity_matrix


def main():
    # Example sentences with semantic nuances
    sentences = [
        'The cat sat on the comfortable mat.',
        'A feline rested on the cozy rug.',
        'Dogs are running in the park.',
        'Machine learning is transforming industries.',
    ]
    similarities = semantic_similarity(sentences)
    print('Semantic Similarity Matrix:')
    for i, sentence1 in enumerate(sentences):
        for j, sentence2 in enumerate(sentences):
            print(f'{sentence1} <-> {sentence2}: {similarities[i][j]:.4f}')

if __name__ == '__main__':
    main()
