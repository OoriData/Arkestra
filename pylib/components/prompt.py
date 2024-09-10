# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.prompt
'''
Common components for prompt loading, assembly & handling
'''
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

    fpath - path to Word Loom file
    relobj - Python object to use as base location for relative fpath, or more precisely the directory containing
        the file from which obj was loaded. Useful for loading Word Loom files included in Python packages
    '''
    if relobj:
        workingdir = obj_file_path_parent(relobj)
        fpath = workingdir / fpath

    with open(fpath, mode='rb') as fp:
        loom = word_loom.load(fp)

    return loom
