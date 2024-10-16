# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.jobs.pg_manager
'''
Maagement & orchestration of data pipeline jobs
'''
from uuid import uuid4
from datetime import datetime, timezone

# https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-identity-column/
CREATE_JOB_TABLE = '''-- Create a table to hold jobs info
CREATE TABLE IF NOT EXISTS {table_name} (
    id INT GENERATED ALWAYS AS IDENTITY,
    job_start TIMESTAMP WITH TIME ZONE,     -- timestamp of job start
    job_end TIMESTAMP WITH TIME ZONE,       -- timestamp of job end (successful or not)
    success BOOL,                           -- did the job succeed?
    request JSON,                           -- job request params JSON
    response JSON,                          -- job response JSON
    pipeline_version TEXT,                  -- Version indicator for the pipeline which ran the job
    metadata JSON                           -- Any additional metadata
)
'''

JOB_INSERT_SQL= '''
INSERT INTO {table_name} (job_start, success, request, response, pipeline_version, metadata)
VALUES ($1, $2, $3, $4, $5) RETURNING id
'''


class pg_manager:
    '''
    PostgreSQL job manager
    '''
    def __init__(self, dsn, table_name):
        self.table_name = table_name
        self.jobs = {}

    def new_jobid(self):
        return str(uuid4())

    async def async_init(self, pool):
        self.pool = pool
        # Create job table if it doesn't yet exist
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(CREATE_JOB_TABLE.format(self.table_name))

    async def new(self, operation: str, params: dict | None = None, metadata: dict | None = None):
        params = params or {}
        metadata = metadata or {}
        start_ts = datetime.now(tz=timezone.utc)
        # metadata = metadata or {}  # Eh! Null is fine
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    JOB_INSERT_SQL.format(self.table_name),
                    start_ts, params, metadata)
        return row['id']
