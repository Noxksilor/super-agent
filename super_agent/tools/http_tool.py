"""
HTTP and Web Search tools
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any, List
from .base import BaseTool, ToolResult


class HTTPTool(BaseTool):
    """Make HTTP requests"""
    
    name = "http_request"
    description = """Make HTTP requests to external APIs and services.
Supports GET, POST, PUT, DELETE methods.
Can be used to interact with Notion API, webhooks, and other HTTP endpoints."""
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to request"
            },
            "method": {
                "type": "string",
                "description": "HTTP method (GET, POST, PUT, DELETE)",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers",
                "additionalProperties": {"type": "string"}
            },
            "body": {
                "type": "string",
                "description": "Request body (for POST/PUT)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["url"]
    }
    
    def execute(self, url: str, method: str = "GET", 
                headers: Optional[Dict[str, str]] = None,
                body: Optional[str] = None,
                timeout: int = 30,
                **kwargs) -> ToolResult:
        try:
            # Check if HTTP requests are enabled
            if self.config and hasattr(self.config, 'tools'):
                if not self.config.tools.http_requests_enabled:
                    return ToolResult(
                        success=False,
                        output="",
                        error="HTTP requests are disabled in configuration"
                    )
            
            # Prepare request
            req_headers = headers or {}
            if 'User-Agent' not in req_headers:
                req_headers['User-Agent'] = 'SuperAgent/1.0'
            
            if body and 'Content-Type' not in req_headers:
                req_headers['Content-Type'] = 'application/json'
            
            # Create request
            req = urllib.request.Request(
                url,
                method=method.upper()
            )
            
            for key, value in req_headers.items():
                req.add_header(key, value)
            
            if body:
                req.data = body.encode('utf-8')
            
            # Execute request
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_body = response.read().decode('utf-8')
                
                # Try to parse as JSON
                try:
                    response_data = json.loads(response_body)
                    output = json.dumps(response_data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    response_data = None
                    output = response_body
                
                return ToolResult(
                    success=True,
                    output=output,
                    data={
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'url': response.url,
                        'response': response_data
                    }
                )
        except urllib.error.HTTPError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP Error {e.code}: {e.reason}",
                data={
                    'status_code': e.code,
                    'reason': e.reason
                }
            )
        except urllib.error.URLError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"URL Error: {e.reason}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )


class WebSearchTool(BaseTool):
    """Search the web for information"""
    
    name = "web_search"
    description = """Search the web for information using search engines.
Returns search results with titles, URLs, and snippets.
Useful for finding documentation, solutions to problems, and current information."""
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
    
    def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        try:
            # Check if web search is enabled
            if self.config and hasattr(self.config, 'tools'):
                if not self.config.tools.web_search_enabled:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Web search is disabled in configuration"
                    )
            
            # Try DuckDuckGo HTML search (no API key needed)
            results = self._search_ddg(query, num_results)
            
            if results:
                output_lines = [f"Search results for: {query}\n"]
                for i, result in enumerate(results[:num_results], 1):
                    output_lines.append(f"{i}. {result['title']}")
                    output_lines.append(f"   URL: {result['url']}")
                    if result.get('snippet'):
                        output_lines.append(f"   {result['snippet']}")
                    output_lines.append("")
                
                return ToolResult(
                    success=True,
                    output="\n".join(output_lines),
                    data={'results': results[:num_results], 'query': query}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="No search results found"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _search_ddg(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo HTML version"""
        import re
        
        results = []
        
        # Build search URL
        params = urllib.parse.urlencode({'q': query})
        url = f"https://html.duckduckgo.com/html/?{params}"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            with urllib.request.urlopen(req, timeout=15) as response:
                html_content = response.read().decode('utf-8')
            
            # Parse HTML to extract results
            # DuckDuckGo HTML uses class="result__a" for result links
            # and class="result__snippet" for snippets
            
            # Simple regex-based parsing
            result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'
            
            links = re.findall(result_pattern, html_content)
            snippets = re.findall(snippet_pattern, html_content)
            
            for i, (link_url, title) in enumerate(links[:num_results]):
                # DuckDuckGo uses redirect URLs, extract actual URL
                if 'uddg=' in link_url:
                    actual_url = urllib.parse.unquote(
                        link_url.split('uddg=')[-1].split('&')[0]
                    )
                else:
                    actual_url = link_url
                
                snippet = snippets[i] if i < len(snippets) else ""
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                
                results.append({
                    'title': title.strip(),
                    'url': actual_url,
                    'snippet': snippet
                })
            
            return results
        except Exception as e:
            # Fallback: return empty results
            return []
