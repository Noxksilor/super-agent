"""
PS-Agent-MVP integration tool
"""

import os
import json
from typing import Optional, Dict, Any
from .base import BaseTool, ToolResult
from .command_tool import CommandTool


class PSAgentTool(BaseTool):
    """Run Photoshop automation pipeline via ps-agent-mvp"""
    
    name = "ps_agent"
    description = """Run the Photoshop automation pipeline (ps-agent-mvp).
This tool executes the orchestrator.py script to process Photoshop jobs.
Can create PNG outputs, process templates, and generate logs."""
    parameters_schema = {
        "type": "object",
        "properties": {
            "config_file": {
                "type": "string",
                "description": "Path to the job configuration JSON file"
            },
            "job_name": {
                "type": "string",
                "description": "Name for the job (will create config if not exists)"
            },
            "template_path": {
                "type": "string",
                "description": "Path to Photoshop template file"
            },
            "output_dir": {
                "type": "string",
                "description": "Output directory for results"
            },
            "variables": {
                "type": "object",
                "description": "Variables to substitute in template",
                "additionalProperties": {"type": "string"}
            },
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["run_job", "create_config", "list_jobs", "check_status"],
                "default": "run_job"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, config: Any = None):
        super().__init__(config)
        self.command_tool = CommandTool(config)
    
    def execute(self, action: str = "run_job", 
                config_file: Optional[str] = None,
                job_name: Optional[str] = None,
                template_path: Optional[str] = None,
                output_dir: Optional[str] = None,
                variables: Optional[Dict[str, str]] = None,
                **kwargs) -> ToolResult:
        try:
            # Get ps-agent-mvp path from config
            ps_agent_path = self._get_ps_agent_path()
            
            if not os.path.exists(ps_agent_path):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"ps-agent-mvp not found at: {ps_agent_path}"
                )
            
            if action == "run_job":
                return self._run_job(ps_agent_path, config_file, job_name)
            elif action == "create_config":
                return self._create_config(ps_agent_path, job_name, template_path, 
                                          output_dir, variables)
            elif action == "list_jobs":
                return self._list_jobs(ps_agent_path)
            elif action == "check_status":
                return self._check_status(ps_agent_path, job_name)
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
    
    def _get_ps_agent_path(self) -> str:
        """Get ps-agent-mvp installation path"""
        if self.config and hasattr(self.config, 'ps_agent_mvp_path'):
            return self.config.ps_agent_mvp_path
        return "C:\\ps_jobs\\job_0001"
    
    def _run_job(self, ps_agent_path: str, 
                 config_file: Optional[str],
                 job_name: Optional[str]) -> ToolResult:
        """Run a Photoshop job"""
        # Determine config file
        if not config_file:
            if job_name:
                config_file = os.path.join(ps_agent_path, "configjson", f"{job_name}.json")
            else:
                config_file = os.path.join(ps_agent_path, "configjson", "example_job.json")
        
        if not os.path.exists(config_file):
            return ToolResult(
                success=False,
                output="",
                error=f"Config file not found: {config_file}"
            )
        
        # Run orchestrator
        command = f"python orchestrator.py {config_file}"
        result = self.command_tool.execute(command, cwd=ps_agent_path)
        
        if result.success:
            # Parse output to find generated files
            output_info = self._parse_job_output(result.output, ps_agent_path)
            return ToolResult(
                success=True,
                output=f"Job completed successfully.\n{result.output}",
                data={
                    'config_file': config_file,
                    'output_files': output_info.get('output_files', []),
                    'log_files': output_info.get('log_files', [])
                }
            )
        return result
    
    def _create_config(self, ps_agent_path: str,
                       job_name: Optional[str],
                       template_path: Optional[str],
                       output_dir: Optional[str],
                       variables: Optional[Dict[str, str]]) -> ToolResult:
        """Create a new job configuration"""
        if not job_name:
            return ToolResult(
                success=False,
                output="",
                error="job_name is required for create_config action"
            )
        
        config_dir = os.path.join(ps_agent_path, "configjson")
        os.makedirs(config_dir, exist_ok=True)
        
        config = {
            "job_name": job_name,
            "template_path": template_path or "",
            "output_dir": output_dir or os.path.join(ps_agent_path, "output", job_name),
            "variables": variables or {}
        }
        
        config_file = os.path.join(config_dir, f"{job_name}.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return ToolResult(
            success=True,
            output=f"Created config file: {config_file}",
            data={'config_file': config_file, 'config': config}
        )
    
    def _list_jobs(self, ps_agent_path: str) -> ToolResult:
        """List available job configurations"""
        config_dir = os.path.join(ps_agent_path, "configjson")
        
        if not os.path.exists(config_dir):
            return ToolResult(
                success=True,
                output="No jobs configured yet",
                data={'jobs': []}
            )
        
        jobs = []
        for f in os.listdir(config_dir):
            if f.endswith('.json'):
                config_file = os.path.join(config_dir, f)
                try:
                    with open(config_file, 'r', encoding='utf-8') as cf:
                        config = json.load(cf)
                    jobs.append({
                        'name': f[:-5],
                        'config_file': config_file,
                        'template': config.get('template_path', 'N/A')
                    })
                except:
                    jobs.append({
                        'name': f[:-5],
                        'config_file': config_file,
                        'template': 'Error reading config'
                    })
        
        output_lines = ["Available jobs:"]
        for job in jobs:
            output_lines.append(f"  - {job['name']}: {job['config_file']}")
        
        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={'jobs': jobs}
        )
    
    def _check_status(self, ps_agent_path: str, 
                      job_name: Optional[str]) -> ToolResult:
        """Check status of a job (look for output files and logs)"""
        if not job_name:
            return ToolResult(
                success=False,
                output="",
                error="job_name is required for check_status action"
            )
        
        output_dir = os.path.join(ps_agent_path, "output", job_name)
        logs_dir = os.path.join(ps_agent_path, "logs")
        
        status = {
            'job_name': job_name,
            'output_dir': output_dir,
            'exists': os.path.exists(output_dir),
            'output_files': [],
            'log_files': []
        }
        
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                if f.endswith(('.png', '.jpg', '.psd', '.pdf')):
                    status['output_files'].append(os.path.join(output_dir, f))
        
        if os.path.exists(logs_dir):
            for f in os.listdir(logs_dir):
                if job_name in f and f.endswith('.log'):
                    status['log_files'].append(os.path.join(logs_dir, f))
        
        output_lines = [f"Status for job: {job_name}"]
        output_lines.append(f"  Output directory: {output_dir}")
        output_lines.append(f"  Exists: {status['exists']}")
        output_lines.append(f"  Output files: {len(status['output_files'])}")
        for f in status['output_files']:
            output_lines.append(f"    - {f}")
        output_lines.append(f"  Log files: {len(status['log_files'])}")
        for f in status['log_files']:
            output_lines.append(f"    - {f}")
        
        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data=status
        )
    
    def _parse_job_output(self, output: str, ps_agent_path: str) -> Dict[str, Any]:
        """Parse job output to extract generated files"""
        import re
        
        result = {
            'output_files': [],
            'log_files': []
        }
        
        # Look for output file patterns
        output_patterns = [
            r'Output:\s*(.+\.png)',
            r'Output:\s*(.+\.jpg)',
            r'Saved:\s*(.+\.png)',
            r'Created:\s*(.+\.psd)',
        ]
        
        for pattern in output_patterns:
            matches = re.findall(pattern, output)
            result['output_files'].extend(matches)
        
        # Look for log files
        log_pattern = r'Log:\s*(.+\.log)'
        result['log_files'] = re.findall(log_pattern, output)
        
        return result
