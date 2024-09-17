# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.prompt
'''
Common components for prompt loading, assembly & handling
'''
from dataclasses import dataclass
from pathlib import Path

from ogbujipt import word_loom


# FIXME: Replace with utiloori.filepath.obj_file_path_parent
def obj_file_path_parent(obj):
    '''Cross-platform Python trick to get the path to a file containing a given object'''
    import inspect
    # Should already be an absolute path
    # from os.path import abspath
    # return abspath(inspect.getsourcefile(obj))
    return Path(inspect.getsourcefile(obj)).parent


def load_loom(fpath, relobj=None):
    '''
    Load a Word Loom file (e.g for prompts) which are relative to an object

    fpath (str or Path) - path to Word Loom file
    relobj - Python object to use as base location for relative fpath, or more precisely the directory containing
        the file from which obj was loaded. Useful for loading Word Loom files included in Python packages
    '''
    if isinstance(fpath, str):
        fpath = Path(fpath)
    if relobj:
        workingdir = obj_file_path_parent(relobj)
        fpath = workingdir / fpath

    with open(fpath, mode='rb') as fp:
        loom = word_loom.load(fp)

    return loom


@dataclass
class Base64Image:
    '''Base64 encoded image data'''
    # TODO: Override for full MIME types
    type: str
    filename: str
    data: str | bytes


def composite_prompt_content(text, base64_images=None):
    '''
    Support OpenAI-style prompting with included attachments
    Note: Image attachment types only, for now
    '''
    base64_images = base64_images or []
    if not base64_images:
        # Degenerate to scalar prompt
        return text
    content = [
            {
                'type': 'text',
                'text': text
            }
    ]
    for img in base64_images:
        content.append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:image/{img.type};base64,{img.data}'
                }
            })
    return content
