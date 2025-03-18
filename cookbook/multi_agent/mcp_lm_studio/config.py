import os
# Root directory to scan (replace with your desired directory)
DEFAULT_ROOT_DIR = os.path.expanduser('~/Documents')
ROOT_DIR = os.environ.get('ROOT_DIR', DEFAULT_ROOT_DIR)

LM_STUDIO_ENDPOINT = os.environ.get('LM_STUDIO_ENDPOINT', 'http://localhost:1234/v1')
# Set to actual model name in LM Studio
LM_STUDIO_MODEL = os.environ.get('LM_STUDIO_MODEL', 'local-model')

SEARXNG_ENDPOINT = os.environ.get('SEARXNG_ENDPOINT', 'http://localhost:8000')
