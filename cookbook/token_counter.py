# cookbook/token_counter.py
'''
Token Counter Utility

Simple command-line utility for counting tokens (how LLMs see text) in text files,
using various tiktoken encodings. Useful for comparing token efficiency across file formats,
quick token analysis for NLP and AI model prep, etc.

Usage Examples:
    # Count tokens in a single file
    python token_counter.py document.txt

    # Count tokens in multiple files
    python token_counter.py file1.json file2.yaml file3.txt

    # Specify a different encoding
    python token_counter.py --enc=p50k_base document.txt

Dependencies:
    - fire: For CLI argument parsing
    - tiktoken: For token encoding and counting

Note: 
    The default encoding (cl100k_base) is used by GPT-4 and many modern 
    OpenAI language models.
'''
import fire
import tiktoken

# Cache tiktoken encoding objects for improved performance
g_encodings = {}


def count_tokens(text, enc_name='cl100k_base'):
    '''
    Count tokens in a given text using the specified encoding.
    
    Args:
        text (str): Text to tokenize
        encoding_name (str): tiktoken encoding to use
    
    Returns:
        int: Number of tokens
    '''
    enc = g_encodings.setdefault(enc_name, tiktoken.get_encoding(enc_name))
    return len(enc.encode(text))


def main(*fpaths, enc='cl100k_base'):
    print(f'Token counts using tiktoken encoding {enc}:')
    for fpath in fpaths:
        with open(fpath) as fptr:
            toks = count_tokens(fptr.read())
        print(f'\t{fpath}: {toks} tokens')


if __name__ == '__main__':
    fire.Fire(main)
