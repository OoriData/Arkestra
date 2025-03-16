# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
# SPDX-License-Identifier: Apache-2.0
# cookbook/toolio_researcher_plus/main.py
'''
More sophistcated version of the research tool in Toolio's demo directory, combining LLMs and web search

1. Uses async/await throughout for efficient I/O
2. Toolio-guaranteed structured JSON schemas for LLM outputs
3. Chain-of-thought research planning upfront
4. Comprehensive tracing system recording every step
5. Configurable rigor level to control research depth
6. SearXNG integration (with optional Toolio tool features)
7. Clean separation of concerns between components

Research process:

1. Takes initial query and plans research steps using a structured schema
2. Executes planned steps combining web search and analysis
3. Can adaptively add steps based on findings
4. Uses rigor parameter to control depth/thoroughness
5. Maintains detailed trace of all operations

Usage:

```bash
python demo/tee_seek/main.py 'Impact of regenerative agriculture on soil health' --rigor 0.6
python demo/tee_seeker/main.py 'What's so valuable about DeepSeek's GRPO technique?' --rigor 0.5
```
'''
import os
import json
import asyncio
# from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional
import mimetypes
from urllib.parse import urlparse

import fire
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich import print as rprint
import trafilatura
from trafilatura.settings import use_config

console = Console()

# from toolio import load_or_connect
from toolio.llm_helper import local_model_runner
from toolio.tool import tool, param

# Settings that could be moved to config
SEARXNG_ENDPOINT = os.getenv('SEARXNG_ENDPOINT', 'http://localhost:8888/search')
RESULTS_PER_QUERY = 3  # Number of results to process per search
MAX_STEPS = 10  # Maximum steps before forcing termination
MIN_STEPS = 2  # Minimum steps before allowing early termination
DEFAULT_TRACE_FILE = 'researcher_trace.json'

# MODEL_DEFAULT = 'mlx-community/deepseek-r1-distill-qwen-1.5b-4bit'
# MODEL_DEFAULT = 'mlx-community/deepseek-r1-distill-qwen-1.5b'  # Think this is the same as mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-bf16
# MODEL_DEFAULT = 'mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit'
# MODEL_DEFAULT = 'mlx-community/DeepSeek-R1-Distill-Qwen-7B-8bit'
# MODEL_DEFAULT = 'mlx-community/DeepSeek-R1-Distill-Llama-8B-8bit'
MODEL_DEFAULT = 'mlx-community/Mistral-Nemo-Instruct-2407-4bit'

LAUNCH_PROMPT_TEMPLATE = '''\
You are a research assistant tasked with investigating the following main query:
{query}
Your task is to plan a series of research steps to thoroughly investigate this query.
Consider the following:
1. What initial information do we have?
2. What additional information do we need?
3. What steps will you take to gather this information?

Start by responding with a list of tasks, and only a list of tasks. You can work on additional steps, and the conclusion later.
Keep it brief!
'''

# Keep your response short, because you'll have a chance to elaborate as we go along.

# ━━━━━━ ⬇ Schemas ⬇ ━
# Schema for research planning response
PLAN_SCHEMA = {
    'type': 'object', 
    'properties': {
        'initial_thoughts': {'type': 'string'},
        'research_steps': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'step_type': {'type': 'string', 'enum': ['web_search', 'reasoning_step']},
                    'query': {'type': 'string'},
                    'reasoning': {'type': 'string'}
                },
                'required': ['step_type', 'reasoning']
            }
        },
        'success_criteria': {'type': 'string'}
    },
    'required': ['initial_thoughts', 'research_steps', 'success_criteria']
}


# Simplified schema for research planning response
PLAN_SCHEMA = {
    'type': 'object', 
    'properties': {
        'research_steps': {
            'type': 'array',
            'maxItems': 5,  # Limit number of steps
            'items': {
                'type': 'object',
                'properties': {
                    'step_type': {'type': 'string', 'enum': ['web_search', 'analysis']},
                    'query': {'type': 'string', 'maxLength': 100},  # Limit query length
                    'purpose': {'type': 'string', 'maxLength': 150}  # Brief explanation
                },
                'required': ['step_type', 'query', 'purpose']
            }
        },
        'goal': {'type': 'string', 'maxLength': 200}  # Brief success criteria
    },
    'required': ['research_steps', 'goal']
}

# Add a system prompt to encourage conciseness
PLAN_SYSPROMPT = '''Create a focused research plan with specific search queries.
Keep explanations brief and precise. Limit to 3-5 key search steps.'''


# Schema for research planning response
PLAN_PLUS_SCHEMA = {
    'type': 'object', 
    'properties': {
        'initial_thoughts': {'type': 'string'},
        'research_steps': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'step_type': {'type': 'string', 'enum': ['web_search', 'analysis', 'conclusion']},
                    'query': {'type': 'string'},
                    'reasoning': {'type': 'string'}
                },
                'required': ['step_type', 'reasoning']
            }
        },
        'success_criteria': {'type': 'string'}
    },
    'required': ['initial_thoughts', 'research_steps', 'success_criteria']
}


# Schema for analyzing search results
ANALYSIS_SCHEMA = {
    'type': 'object',
    'properties': {
        'key_findings': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'additional_questions': {
            'type': 'array', 
            'items': {'type': 'string'}
        },
        'research_complete': {'type': 'boolean'},
        'completion_reasoning': {'type': 'string'}
    },
    'required': ['key_findings', 'research_complete', 'completion_reasoning']
}


# ━━━━━━ ⬇ Processing file types from web search ⬇ ━
class content_processor:
    def __init__(self):
        # Configure trafilatura
        self.traf_config = use_config()
        self.traf_config.set('DEFAULT', 'EXTRACTION_TIMEOUT', '10')

    def classify_url(self, url: str) -> str:
        '''Classify URL by content type'''
        path = urlparse(url).path
        mime_type, _ = mimetypes.guess_type(path)

        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type == 'application/pdf':
                return 'pdf'
            elif mime_type.startswith('video/'):
                return 'video'
            elif mime_type.startswith('text/'):
                return 'text'
        return 'unknown'

    async def process_content(self, content: str, url: str) -> Dict:
        '''Process content based on type'''
        content_type = self.classify_url(url)

        if content_type == 'text':
            # Extract clean text with trafilatura
            extracted = trafilatura.extract(
                content,
                config=self.traf_config,
                include_comments=False,
                include_tables=True,
                output_format='markdown'
            )
            return {
                'type': content_type,
                'processed_content': extracted if extracted else content[:2000],
                'raw_content': content[:2000]
            }

        return {
            'type': content_type,
            'processed_content': f'[{content_type.upper()} content]',
            'raw_content': content[:2000] if content else ''
        }


# ━━━━━━ ⬇ Tools ⬇ ━
#Note: Not actually calling this via LLM tool-calling, but no harm declaring it that way
# XXX: If actually used tool-calling style, might need to curry it with partial to handle the progress param
@tool('searxng_search',
      desc='Run a Web search query and get relevant results',
      params=[param('query', str, 'search query text', True)])
async def searxng_search(query, progress=None):
    '''Execute a SearXNG search and return results'''

    processor = content_processor()
    qparams = {
        'q': query,
        'format': 'json',
        'categories': ['general'],
        'engines': ['qwant', 'duckduckgo', 'bing']
    }

    if progress:
        search_task = progress.add_task(f"[blue]Searching: {query}", total=RESULTS_PER_QUERY)

    async with httpx.AsyncClient() as client:
        # Execute search
        resp = await client.get(SEARXNG_ENDPOINT, params=qparams)
        results = resp.json()['results'][:RESULTS_PER_QUERY]

        # Get content for each result
        processed = []
        for idx, r in enumerate(results):
            try:
                if progress:
                    progress.update(search_task, description=f"[blue]Fetching ({idx + 1}/{RESULTS_PER_QUERY}): {r['url'][:50]}...")

                content_resp = await client.get(r['url'])
                content = content_resp.text

                # Process the content
                processed_content = await processor.process_content(content, r['url'])

                processed.append({
                    'title': r['title'],
                    'url': r['url'],
                    **processed_content
                })

                if progress:
                    progress.update(search_task, advance=1)

            except Exception as e:
                logging.warning(f'Error fetching {r["url"]}: {e}')
                console.print(f"[red]Error fetching {r['url']}: {e}")

        if progress:
            progress.update(search_task, completed=True)
        return processed


# ━━━━━━ ⬇ Main researcher class ⬇ ━
class tee_seeker:
    def __init__(self, llm, trace_file=DEFAULT_TRACE_FILE):
        self.llm = llm
        self.trace_file = trace_file
        self.trace = []

    async def research(self, query, rigor=0.5):
        '''Main research loop with progress tracking'''
        console.print(f"\n[bold cyan]Starting research on:[/] {query}\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Plan initial research steps
            plan_task = progress.add_task("[cyan]Planning research steps...", total=None)
            full_query = f'Plan research steps to answer: {query}'
            plan = await self.llm(full_query, 
                                json_schema=PLAN_SCHEMA,
                                sysprompt=PLAN_SYSPROMPT, 
                                max_tokens=2048)
            progress.update(plan_task, completed=True)

            plan = json.loads(plan)
            self._trace('plan', plan)

            # Print the plan
            console.print("\n[bold green]Research Plan:[/]")
            for idx, step in enumerate(plan['research_steps'], 1):
                console.print(f"[cyan]{idx}.[/] {step['purpose']}")
            console.print(f"\n[bold green]Goal:[/] {plan['goal']}\n")

            # Create overall progress bar
            total_steps = len(plan['research_steps'])
            research_task = progress.add_task(
                "[green]Executing research steps...",
                total=total_steps
            )

            completed_steps = 0
            findings = []

            for step_num, step in enumerate(plan['research_steps'], 1):
                if completed_steps >= MAX_STEPS:
                    break

                console.print(f"\n[bold cyan]Step {step_num}/{total_steps}:[/] {step['purpose']}")
                progress.update(research_task, description=f"[green]Executing step {step_num}/{total_steps}")
                self._trace('step_start', step)

                if step['step_type'] == 'web_search':
                    results = await searxng_search(step['query'], progress=progress)
                    self._trace('search_results', results)

                    # Print found URLs
                    console.print("\n[dim]Sources found:[/]")
                    for r in results:
                        console.print(f"[dim]• {r['title']} - {r['url']}[/]")

                    analysis = await self.llm(
                        f'Analyze these search results. Keep it succinct, with just 3-5 main takeaways:\n{json.dumps(results)}',
                        json_schema=ANALYSIS_SCHEMA,
                        max_tokens=4096
                    )
                    analysis = json.loads(analysis)
                    self._trace('analysis', analysis)

                    # Print key findings from this step
                    console.print("\n[bold green]Key findings from this step:[/]")
                    for finding in analysis['key_findings']:
                        console.print(f"• {finding}")
                    console.print()  # Add spacing

                    findings.extend(analysis['key_findings'])

                    if (completed_steps >= MIN_STEPS and 
                        analysis['research_complete'] and
                        rigor < 0.8):
                        console.print("[yellow]Research goals met early - proceeding to synthesis[/]\n")
                        break

                completed_steps += 1
                progress.update(research_task, advance=1)

            # Final synthesis
            console.print("\n[bold cyan]Synthesizing final results...[/]")
            synthesis_task = progress.add_task("[cyan]Creating final report...", total=None)
            summary = await self.llm(
                f'Synthesize this research in a report for me:\n{json.dumps(findings)}',
                max_tokens=8192
            )
            progress.update(synthesis_task, completed=True)

            self._trace('summary', summary)

            console.print("\n[bold green]Final Research Report:[/]")
            console.print("=" * 80)
            console.print(summary)
            console.print("=" * 80 + "\n")

            return summary

    def _trace(self, step_type, data):
        '''Record a trace entry'''
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': step_type,
            'data': data
        }
        self.trace.append(entry)

        # Write updated trace
        with open(self.trace_file, 'w') as f:
            json.dump(self.trace, f, indent=2)


def main(query, model: str = MODEL_DEFAULT, rigor: float = 0.5, trace_file: str=DEFAULT_TRACE_FILE):
    '''
    Research tool combining LLMs and web search

    Command line args:
    query: Research query
    model: Model ID or Toolio server URL
    trace-file: JSON file to record execution trace
    rigor: Research rigor level (0.0-1.0)
    '''
    # llm = load_or_connect(model)
    llm = local_model_runner(model)
    researcher = tee_seeker(llm, trace_file)
    summary = asyncio.run(researcher.research(query, rigor))
    print(f'\nResearch Summary:\n{summary}')


if __name__ == '__main__':
    fire.Fire(main)
