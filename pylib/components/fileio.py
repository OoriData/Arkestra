# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.fileio
'''
Common components for data pipelines & orchestration
'''
import json
# from pathlib import Path

# TODO: JSON streamer alternatives


class jsonable:
    '''
    On-disk file which can be read or written as JSON
    '''
    def __init__(self, full_path, jobid=None):
        self.jobid = jobid
        self.full_path = full_path

    def load(self):
        with self.full_path.open() as fp:
            obj = json.load(fp)
        return obj

    def save(self, obj):
        with self.full_path.open('w') as fp:
            obj = json.dump(obj, fp)
