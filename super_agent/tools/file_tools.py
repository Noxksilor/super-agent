"""
File system tools
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from .base import BaseTool, ToolResult


class FileReadTool(BaseTool):
    """Read file contents"""
    
    name = "file_read"
    description = "Read contents of a file. Returns the file content as string."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)",
                "default": "utf-8"
            }
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, encoding: str = "utf-8", **kwargs) -> ToolResult:
        try:
            # Validate path is in allowed directories
            if not self._is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied: path '{path}' is not in allowed directories"
                )
            
            if not os.path.exists(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {path}"
                )
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return ToolResult(
                success=True,
                output=content,
                data={'path': path, 'size': len(content)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _is_path_allowed(self, path: str) -> bool:
        if not self.config or not hasattr(self.config, 'tools'):
            return True
        allowed_dirs = self.config.tools.allowed_directories
        abs_path = os.path.abspath(path)
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                return True
        return False


class FileWriteTool(BaseTool):
    """Write content to a file"""
    
    name = "file_write"
    description = "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)",
                "default": "utf-8"
            },
            "create_dirs": {
                "type": "boolean",
                "description": "Create parent directories if they don't exist",
                "default": True
            }
        },
        "required": ["path", "content"]
    }
    
    def execute(self, path: str, content: str, encoding: str = "utf-8", 
                create_dirs: bool = True, **kwargs) -> ToolResult:
        try:
            # Validate path is in allowed directories
            if not self._is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied: path '{path}' is not in allowed directories"
                )
            
            # Create directories if needed
            if create_dirs:
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                data={'path': path, 'size': len(content)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _is_path_allowed(self, path: str) -> bool:
        if not self.config or not hasattr(self.config, 'tools'):
            return True
        allowed_dirs = self.config.tools.allowed_directories
        abs_path = os.path.abspath(path)
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                return True
        return False


class FileDeleteTool(BaseTool):
    """Delete a file or directory"""
    
    name = "file_delete"
    description = "Delete a file or directory. Use with caution!"
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file or directory to delete"
            },
            "recursive": {
                "type": "boolean",
                "description": "For directories, delete contents recursively",
                "default": False
            }
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, recursive: bool = False, **kwargs) -> ToolResult:
        try:
            # Validate path is in allowed directories
            if not self._is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied: path '{path}' is not in allowed directories"
                )
            
            if not os.path.exists(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path not found: {path}"
                )
            
            if os.path.isfile(path):
                os.remove(path)
                return ToolResult(
                    success=True,
                    output=f"Successfully deleted file: {path}"
                )
            elif os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
                return ToolResult(
                    success=True,
                    output=f"Successfully deleted directory: {path}"
                )
            return ToolResult(
                success=False,
                output="",
                error="Unknown path type"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _is_path_allowed(self, path: str) -> bool:
        if not self.config or not hasattr(self.config, 'tools'):
            return True
        allowed_dirs = self.config.tools.allowed_directories
        abs_path = os.path.abspath(path)
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                return True
        return False


class DirectoryListTool(BaseTool):
    """List contents of a directory"""
    
    name = "directory_list"
    description = "List files and directories in a given path"
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the directory to list"
            },
            "recursive": {
                "type": "boolean",
                "description": "List contents recursively",
                "default": False
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g., '*.py')"
            }
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, recursive: bool = False, 
                pattern: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            # Validate path is in allowed directories
            if not self._is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied: path '{path}' is not in allowed directories"
                )
            
            if not os.path.exists(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Directory not found: {path}"
                )
            
            if not os.path.isdir(path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path is not a directory: {path}"
                )
            
            items = []
            
            if recursive:
                for root, dirs, files in os.walk(path):
                    for d in dirs:
                        item_path = os.path.join(root, d)
                        if pattern is None or self._matches_pattern(d, pattern):
                            items.append({
                                'name': d,
                                'path': item_path,
                                'type': 'directory'
                            })
                    for f in files:
                        item_path = os.path.join(root, f)
                        if pattern is None or self._matches_pattern(f, pattern):
                            items.append({
                                'name': f,
                                'path': item_path,
                                'type': 'file',
                                'size': os.path.getsize(item_path)
                            })
            else:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if pattern is None or self._matches_pattern(item, pattern):
                        if os.path.isfile(item_path):
                            items.append({
                                'name': item,
                                'path': item_path,
                                'type': 'file',
                                'size': os.path.getsize(item_path)
                            })
                        else:
                            items.append({
                                'name': item,
                                'path': item_path,
                                'type': 'directory'
                            })
            
            # Format output
            output_lines = []
            for item in items:
                if item['type'] == 'directory':
                    output_lines.append(f"[DIR]  {item['name']}")
                else:
                    size = self._format_size(item.get('size', 0))
                    output_lines.append(f"[FILE] {item['name']} ({size})")
            
            return ToolResult(
                success=True,
                output="\n".join(output_lines) if output_lines else "Empty directory",
                data={'items': items, 'count': len(items)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _is_path_allowed(self, path: str) -> bool:
        if not self.config or not hasattr(self.config, 'tools'):
            return True
        allowed_dirs = self.config.tools.allowed_directories
        abs_path = os.path.abspath(path)
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                return True
        return False
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
