# filesystem_mcp_server
from mcp.server.fastmcp import FastMCP as MCP  # , Tool, Resource
import os
import datetime
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

from config import ROOT_DIR

# Initialize MCP server
mcp = MCP(name='FilesystemServer', version='1.0.0')


@mcp.tool('get-current-time')
async def get_current_time():
    '''Get the current system time.'''
    now = datetime.datetime.now()
    return {
        'iso_format': now.isoformat(),
        'readable': now.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': now.timestamp()
    }

@mcp.tool('list-files')
async def list_files(
    directory: str = ROOT_DIR,
    recursive: bool = False,
    include_hidden: bool = False,
    max_depth: int = 3
) -> List[Dict[str, Any]]:
    '''
    List files in the specified directory.

    Args:
        directory: Path to directory to list files from (default: ROOT_DIR)
        recursive: Whether to list files recursively
        include_hidden: Whether to include hidden files
        max_depth: Maximum depth for recursive search

    Returns:
        List of file information dictionaries
    '''
    directory = os.path.join(ROOT_DIR, directory) if not os.path.isabs(directory) else directory

    # Safety check to prevent escaping ROOT_DIR
    if not os.path.commonpath([os.path.abspath(directory), ROOT_DIR]) == ROOT_DIR:
        return {'error': f'Access denied. Cannot access directories outside of {ROOT_DIR}'}

    results = []

    def should_include(path):
        basename = os.path.basename(path)
        if not include_hidden and basename.startswith('.'):
            return False
        return True

    def scan_directory(dir_path, current_depth=0):
        if current_depth > max_depth:
            return

        try:
            for entry in os.scandir(dir_path):
                if not should_include(entry.path):
                    continue

                stat_info = entry.stat()
                info = {
                    'name': entry.name,
                    'path': entry.path,
                    'is_dir': entry.is_dir(),
                    'size_bytes': stat_info.st_size,
                    'size_human': format_size(stat_info.st_size),
                    'modified': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    'created': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                }

                results.append(info)

                if entry.is_dir() and recursive and current_depth < max_depth:
                    scan_directory(entry.path, current_depth + 1)
        except PermissionError:
            results.append({
                'path': dir_path,
                'error': 'Permission denied'
            })
        except Exception as e:
            results.append({
                'path': dir_path,
                'error': str(e)
            })

    scan_directory(directory)
    return results

@mcp.tool('search-files')
async def search_files(
    pattern: str = '*', 
    directory: str = ROOT_DIR,
    recursive: bool = True,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[str] = None,
    modified_before: Optional[str] = None,
    file_type: Optional[str] = None,
    max_results: int = 100
) -> List[Dict[str, Any]]:
    '''
    Search for files matching criteria.

    Args:
        pattern: File pattern (e.g., '*.txt')
        directory: Directory to search in (default: ROOT_DIR)
        recursive: Whether to search recursively
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        modified_after: Files modified after this date (ISO format)
        modified_before: Files modified before this date (ISO format)
        file_type: Filter by file extension (e.g., 'pdf')
        max_results: Maximum number of results to return

    Returns:
        List of files matching the criteria
    '''
    directory = os.path.join(ROOT_DIR, directory) if not os.path.isabs(directory) else directory

    # Safety check to prevent escaping ROOT_DIR
    if not os.path.commonpath([os.path.abspath(directory), ROOT_DIR]) == ROOT_DIR:
        return {'error': f'Access denied. Cannot access directories outside of {ROOT_DIR}'}

    # Parse dates if provided
    after_date = None
    before_date = None

    if modified_after:
        try:
            after_date = datetime.datetime.fromisoformat(modified_after).timestamp()
        except ValueError:
            return {'error': f'Invalid date format for modified_after: {modified_after}. Use ISO format (YYYY-MM-DDTHH:MM:SS).'}

    if modified_before:
        try:
            before_date = datetime.datetime.fromisoformat(modified_before).timestamp()
        except ValueError:
            return {'error': f'Invalid date format for modified_before: {modified_before}. Use ISO format (YYYY-MM-DDTHH:MM:SS).'}

    # File extension filter
    if file_type and not file_type.startswith('.'):
        file_type = f'.{file_type}'

    results = []

    for root, dirs, files in os.walk(directory):
        if not recursive and root != directory:
            continue

        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue

            file_path = os.path.join(root, file)

            # Match pattern
            if not Path(file_path).match(pattern):
                continue

            # Match extension
            if file_type and not file.endswith(file_type):
                continue

            try:
                stat_info = os.stat(file_path)

                # Size filters
                if min_size is not None and stat_info.st_size < min_size:
                    continue
                if max_size is not None and stat_info.st_size > max_size:
                    continue

                # Date filters
                if after_date is not None and stat_info.st_mtime < after_date:
                    continue
                if before_date is not None and stat_info.st_mtime > before_date:
                    continue

                # Add to results
                results.append({
                    'name': file,
                    'path': file_path,
                    'size_bytes': stat_info.st_size,
                    'size_human': format_size(stat_info.st_size),
                    'modified': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    'created': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                })

                if len(results) >= max_results:
                    break
            except (PermissionError, FileNotFoundError):
                continue

        if len(results) >= max_results:
            break

    return results

@mcp.tool('get-file-info')
async def get_file_info(path: str) -> Dict[str, Any]:
    '''
    Get detailed information about a specific file.

    Args:
        path: Path to the file

    Returns:
        Dictionary with file information
    '''
    path = os.path.join(ROOT_DIR, path) if not os.path.isabs(path) else path

    # Safety check to prevent escaping ROOT_DIR
    if not os.path.commonpath([os.path.abspath(path), ROOT_DIR]) == ROOT_DIR:
        return {'error': f'Access denied. Cannot access files outside of {ROOT_DIR}'}

    try:
        stat_info = os.stat(path)
        file_info = {
            'name': os.path.basename(path),
            'path': path,
            'exists': os.path.exists(path),
            'is_file': os.path.isfile(path),
            'is_dir': os.path.isdir(path),
            'size_bytes': stat_info.st_size,
            'size_human': format_size(stat_info.st_size),
            'modified': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            'accessed': datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            'created': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            'extension': os.path.splitext(path)[1],
        }
        return file_info
    except FileNotFoundError:
        return {'error': 'File not found', 'path': path}
    except PermissionError:
        return {'error': 'Permission denied', 'path': path}
    except Exception as e:
        return {'error': str(e), 'path': path}

@mcp.tool('recent-large-files')
async def recent_large_files(
    directory: str = ROOT_DIR,
    days: int = 7,
    min_size_gb: float = 1.0,
    max_results: int = 20
) -> List[Dict[str, Any]]:
    '''
    Find recent large files (specifically for the query mentioned).

    Args:
        directory: Directory to search in
        days: How many days back to look
        min_size_gb: Minimum size in GB
        max_results: Maximum number of results

    Returns:
        List of large files modified recently
    '''
    min_size_bytes = int(min_size_gb * 1024 * 1024 * 1024)
    now = datetime.datetime.now()
    after_date = (now - datetime.timedelta(days=days)).isoformat()

    return await search_files(
        directory=directory,
        recursive=True,
        min_size=min_size_bytes,
        modified_after=after_date,
        max_results=max_results
    )

# Alternative:
# @mcp.tool('file-preview')
# Main difference: tools are for operations (functions/methods) while resources are for accessing data
# Either approach is reasonable here, but tools have a simpler parameter handling mechanism

@mcp.resource('file-preview/{path}/{max_size}')
async def file_preview(path: str, max_size: int = 10 * 1024 * 1024) -> str:
    '''
    Get a preview of a file's contents.

    Args:
        path: Path to the file
        max_size: Maximum size in bytes to read

    Returns:
        File contents as string
    '''
    path = os.path.join(ROOT_DIR, path) if not os.path.isabs(path) else path

    # Safety check to prevent escaping ROOT_DIR
    if not os.path.commonpath([os.path.abspath(path), ROOT_DIR]) == ROOT_DIR:
        return {'error': f'Access denied. Cannot access files outside of {ROOT_DIR}'}

    try:
        if not os.path.isfile(path):
            return {'error': 'Not a file', 'path': path}

        stat_info = os.stat(path)
        if stat_info.st_size > max_size:
            return {'error': f'File too large (limit: {format_size(max_size)})', 'path': path}

        with open(path, 'r', errors='replace') as f:
            return f.read()
    except FileNotFoundError:
        return {'error': 'File not found', 'path': path}
    except PermissionError:
        return {'error': 'Permission denied', 'path': path}
    except Exception as e:
        return {'error': str(e), 'path': path}

def format_size(size_bytes):
    '''Format file size in a human-readable format.'''
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.2f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    else:
        return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'

if __name__ == '__main__':
    print(f'Starting Filesystem MCP Server - Serving files under: {ROOT_DIR}')
    mcp.run(transport='stdio')
