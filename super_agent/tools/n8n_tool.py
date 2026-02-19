"""
n8n integration tool
"""

import json
import os
from typing import Optional, Dict, Any, List
from .base import BaseTool, ToolResult
from .http_tool import HTTPTool
from .command_tool import CommandTool


class N8NTool(BaseTool):
    """Interact with n8n workflow automation"""
    
    name = "n8n"
    description = """Interact with n8n workflow automation system.
Can start/stop workflows, trigger executions, check status, and manage workflows.
Requires n8n to be running (via Docker or local installation)."""
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["list_workflows", "get_workflow", "execute_workflow", 
                         "get_execution", "activate_workflow", "deactivate_workflow",
                         "create_webhook", "trigger_webhook", "check_health"]
            },
            "workflow_id": {
                "type": "string",
                "description": "ID of the workflow"
            },
            "execution_id": {
                "type": "string",
                "description": "ID of an execution"
            },
            "webhook_url": {
                "type": "string",
                "description": "Webhook URL for triggering workflows"
            },
            "webhook_data": {
                "type": "object",
                "description": "Data to send to webhook",
                "additionalProperties": {}
            },
            "api_key": {
                "type": "string",
                "description": "n8n API key (optional, uses config if not provided)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, config: Any = None):
        super().__init__(config)
        self.http_tool = HTTPTool(config)
        self.command_tool = CommandTool(config)
    
    def execute(self, action: str,
                workflow_id: Optional[str] = None,
                execution_id: Optional[str] = None,
                webhook_url: Optional[str] = None,
                webhook_data: Optional[Dict[str, Any]] = None,
                api_key: Optional[str] = None,
                **kwargs) -> ToolResult:
        try:
            # Get n8n endpoint
            endpoint = self._get_n8n_endpoint()
            headers = self._get_headers(api_key)
            
            if action == "check_health":
                return self._check_health(endpoint)
            elif action == "list_workflows":
                return self._list_workflows(endpoint, headers)
            elif action == "get_workflow":
                return self._get_workflow(endpoint, headers, workflow_id)
            elif action == "execute_workflow":
                return self._execute_workflow(endpoint, headers, workflow_id, webhook_data)
            elif action == "get_execution":
                return self._get_execution(endpoint, headers, execution_id)
            elif action == "activate_workflow":
                return self._activate_workflow(endpoint, headers, workflow_id, True)
            elif action == "deactivate_workflow":
                return self._activate_workflow(endpoint, headers, workflow_id, False)
            elif action == "create_webhook":
                return self._create_webhook_info(endpoint, headers, workflow_id)
            elif action == "trigger_webhook":
                return self._trigger_webhook(webhook_url, webhook_data)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _get_n8n_endpoint(self) -> str:
        """Get n8n API endpoint"""
        if self.config and hasattr(self.config, 'n8n_endpoint'):
            return self.config.n8n_endpoint
        return "http://localhost:5678"
    
    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get API headers"""
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["X-N8N-API-KEY"] = api_key
        return headers
    
    def _check_health(self, endpoint: str) -> ToolResult:
        """Check if n8n is running"""
        # Try to connect to n8n
        result = self.http_tool.execute(
            url=f"{endpoint}/healthz",
            method="GET",
            timeout=5
        )
        
        if result.success:
            return ToolResult(
                success=True,
                output="n8n is running and healthy",
                data={'endpoint': endpoint, 'status': 'healthy'}
            )
        else:
            # Try to start n8n via Docker
            return ToolResult(
                success=False,
                output="",
                error=f"n8n is not running at {endpoint}. Start it with: docker start n8n or run start_ps_agent.ps1"
            )
    
    def _list_workflows(self, endpoint: str, headers: Dict[str, str]) -> ToolResult:
        """List all workflows"""
        result = self.http_tool.execute(
            url=f"{endpoint}/api/v1/workflows",
            method="GET",
            headers=headers
        )
        
        if result.success:
            try:
                data = result.data.get('response', {}) if result.data else {}
                workflows = data.get('data', [])
                
                output_lines = ["Available n8n workflows:"]
                for wf in workflows:
                    status = "active" if wf.get('active') else "inactive"
                    output_lines.append(f"  [{status}] {wf.get('name', 'Unnamed')} (ID: {wf.get('id')})")
                
                return ToolResult(
                    success=True,
                    output="\n".join(output_lines),
                    data={'workflows': workflows}
                )
            except:
                return result
        return result
    
    def _get_workflow(self, endpoint: str, headers: Dict[str, str],
                      workflow_id: Optional[str]) -> ToolResult:
        """Get workflow details"""
        if not workflow_id:
            return ToolResult(
                success=False,
                output="",
                error="workflow_id is required for get_workflow action"
            )
        
        result = self.http_tool.execute(
            url=f"{endpoint}/api/v1/workflows/{workflow_id}",
            method="GET",
            headers=headers
        )
        
        if result.success:
            return ToolResult(
                success=True,
                output=f"Workflow details:\n{result.output}",
                data=result.data
            )
        return result
    
    def _execute_workflow(self, endpoint: str, headers: Dict[str, str],
                          workflow_id: Optional[str],
                          webhook_data: Optional[Dict[str, Any]]) -> ToolResult:
        """Execute a workflow manually"""
        if not workflow_id:
            return ToolResult(
                success=False,
                output="",
                error="workflow_id is required for execute_workflow action"
            )
        
        # n8n uses webhook URLs for manual execution
        # Try to execute via webhook path
        result = self.http_tool.execute(
            url=f"{endpoint}/webhook-test/{workflow_id}",
            method="POST",
            headers=headers,
            body=json.dumps(webhook_data or {})
        )
        
        if result.success:
            return ToolResult(
                success=True,
                output=f"Workflow {workflow_id} executed successfully",
                data=result.data
            )
        return result
    
    def _get_execution(self, endpoint: str, headers: Dict[str, str],
                       execution_id: Optional[str]) -> ToolResult:
        """Get execution details"""
        if not execution_id:
            return ToolResult(
                success=False,
                output="",
                error="execution_id is required for get_execution action"
            )
        
        result = self.http_tool.execute(
            url=f"{endpoint}/api/v1/executions/{execution_id}",
            method="GET",
            headers=headers
        )
        
        if result.success:
            return ToolResult(
                success=True,
                output=f"Execution details:\n{result.output}",
                data=result.data
            )
        return result
    
    def _activate_workflow(self, endpoint: str, headers: Dict[str, str],
                           workflow_id: Optional[str], activate: bool) -> ToolResult:
        """Activate or deactivate a workflow"""
        if not workflow_id:
            return ToolResult(
                success=False,
                output="",
                error="workflow_id is required for activate/deactivate action"
            )
        
        result = self.http_tool.execute(
            url=f"{endpoint}/api/v1/workflows/{workflow_id}/activate" if activate else f"{endpoint}/api/v1/workflows/{workflow_id}/deactivate",
            method="POST",
            headers=headers
        )
        
        if result.success:
            status = "activated" if activate else "deactivated"
            return ToolResult(
                success=True,
                output=f"Workflow {workflow_id} {status} successfully",
                data=result.data
            )
        return result
    
    def _create_webhook_info(self, endpoint: str, headers: Dict[str, str],
                             workflow_id: Optional[str]) -> ToolResult:
        """Get webhook URL for a workflow"""
        if not workflow_id:
            return ToolResult(
                success=False,
                output="",
                error="workflow_id is required for create_webhook action"
            )
        
        # Get workflow to find webhook nodes
        result = self.http_tool.execute(
            url=f"{endpoint}/api/v1/workflows/{workflow_id}",
            method="GET",
            headers=headers
        )
        
        if result.success:
            try:
                data = result.data.get('response', {}) if result.data else {}
                workflow = data.get('data', {})
                nodes = workflow.get('nodes', [])
                
                webhooks = []
                for node in nodes:
                    if node.get('type') == 'n8n-nodes-base.webhook':
                        webhook_path = node.get('parameters', {}).get('path', '')
                        webhook_url = f"{endpoint}/webhook/{webhook_path}"
                        webhooks.append({
                            'name': node.get('name', 'Webhook'),
                            'url': webhook_url,
                            'method': node.get('parameters', {}).get('httpMethod', 'POST')
                        })
                
                if webhooks:
                    output_lines = ["Webhook URLs for workflow:"]
                    for wh in webhooks:
                        output_lines.append(f"  {wh['name']}: {wh['method']} {wh['url']}")
                    
                    return ToolResult(
                        success=True,
                        output="\n".join(output_lines),
                        data={'webhooks': webhooks}
                    )
                else:
                    return ToolResult(
                        success=True,
                        output="No webhook nodes found in this workflow",
                        data={'webhooks': []}
                    )
            except:
                return result
        return result
    
    def _trigger_webhook(self, webhook_url: Optional[str],
                         webhook_data: Optional[Dict[str, Any]]) -> ToolResult:
        """Trigger a webhook URL"""
        if not webhook_url:
            return ToolResult(
                success=False,
                output="",
                error="webhook_url is required for trigger_webhook action"
            )
        
        result = self.http_tool.execute(
            url=webhook_url,
            method="POST",
            body=json.dumps(webhook_data or {})
        )
        
        if result.success:
            return ToolResult(
                success=True,
                output=f"Webhook triggered successfully: {webhook_url}",
                data=result.data
            )
        return result
