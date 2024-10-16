# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.jobs
'''
Maagement & orchestration of data pipeline jobs
'''
from uuid import uuid4

class manager:
    '''
    In-memory job manager
    Recommended to switch to a persistent job manager (on disk, in DB, etc.)
    '''
    def __init__(self):
        self.jobs = {}

    def new_jobid(self):
        return str(uuid4())

