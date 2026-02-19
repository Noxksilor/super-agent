"""
Core Agent implementation
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from .config import AgentConfig, load_config
from .llm.base import BaseLLM, Message, LLMResponse, ToolCall, get_llm_provider
from .tools.base import BaseTool, ToolResult


@dataclass
class TaskStep:
    """A single step in task execution"""
    step_number: int
    action: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskExecution:
    """Record of a task execution"""
    task_id: str
    task_description: str
    status: str = "pending"  # pending, running, completed, failed
    steps: List[TaskStep] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    final_report: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_description': self.task_description,
            'status': self.status,
            'steps': [
                {
                    'step_number': s.step_number,
                    'action': s.action,
                    'tool_name': s.tool_name,
                    'tool_args': s.tool_args,
                    'result': s.result,
                    'success': s.success,
                    'timestamp': s.timestamp
                }
                for s in self.steps
            ],
            'start_time': self.start_time,
            'end_time': self.end_time,
            'final_report': self.final_report,
            'error': self.error
        }


class Agent:
    """
    Autonomous AI Agent that executes tasks using LLM and tools.
    
    The agent:
    1. Receives a task description from the user
    2. Plans steps using LLM
    3. Executes tools to accomplish the task
    4. Iterates until task is complete or fails
    5. Provides a final report
    """
    
    SYSTEM_PROMPT = """You are an autonomous AI agent that executes tasks on a user's computer.

Your capabilities:
- Read, write, and delete files
- Execute shell commands (python, git, docker, n8n, etc.)
- Make HTTP requests and search the web
- Run Photoshop automation via ps-agent-mvp
- Interact with n8n workflows

IMPORTANT RULES:
1. You ONLY work on the task given by the user. Do NOT start new tasks or modify unrelated projects.
2. Plan your steps carefully before executing.
3. If a step fails, try alternative approaches before giving up.
4. Always verify your work and fix any issues.
5. Provide clear, actionable results.

When you complete a task:
- Summarize what was done
- List all files created/modified
- Explain how to use the result
- Note any remaining issues or follow-up steps

Use the available tools to accomplish the task. Think step by step.
When you believe the task is complete, respond with "TASK_COMPLETE:" followed by a summary.
If you encounter an unrecoverable error, respond with "TASK_FAILED:" followed by the error details."""

    def __init__(self, config: Optional[AgentConfig] = None, 
                 config_path: Optional[str] = None):
        """Initialize the agent"""
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = load_config(config_path)
        
        # Initialize LLM
        self.llm = self._init_llm()
        
        # Initialize tools
        self.tools: Dict[str, BaseTool] = {}
        self._init_tools()
        
        # State
        self.current_task: Optional[TaskExecution] = None
        self.messages: List[Message] = []
        self.iteration_count = 0
        
        # Callbacks
        self.on_step_start: Optional[Callable[[TaskStep], None]] = None
        self.on_step_end: Optional[Callable[[TaskStep], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
    
    def _init_llm(self) -> BaseLLM:
        """Initialize the LLM provider"""
        return get_llm_provider(
            provider=self.config.llm.provider,
            api_key=self.config.llm.api_key,
            model=self.config.llm.model,
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature
        )
    
    def _init_tools(self):
        """Initialize available tools"""
        from .tools import (
            FileReadTool, FileWriteTool, FileDeleteTool, DirectoryListTool,
            CommandTool, HTTPTool, WebSearchTool, PSAgentTool, N8NTool
        )
        
        tool_classes = [
            FileReadTool,
            FileWriteTool,
            FileDeleteTool,
            DirectoryListTool,
            CommandTool,
            HTTPTool,
            WebSearchTool,
            PSAgentTool,
            N8NTool
        ]
        
        for tool_class in tool_classes:
            tool = tool_class(self.config)
            self.tools[tool.name] = tool
    
    def _log(self, message: str):
        """Log a message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        
        if self.on_log:
            self.on_log(log_line)
        
        # Also print to console
        print(log_line)
    
    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all tools"""
        return [tool.get_schema() for tool in self.tools.values()]
    
    def execute_task(self, task_description: str, 
                     task_id: Optional[str] = None) -> TaskExecution:
        """
        Execute a task autonomously.
        
        Args:
            task_description: Description of the task to execute
            task_id: Optional task ID (auto-generated if not provided)
        
        Returns:
            TaskExecution record with all steps and results
        """
        # Create task execution record
        if not task_id:
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_task = TaskExecution(
            task_id=task_id,
            task_description=task_description,
            status="running",
            start_time=datetime.now().isoformat()
        )
        
        self._log(f"Starting task: {task_id}")
        self._log(f"Description: {task_description}")
        
        # Initialize messages
        self.messages = [
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=f"Task: {task_description}\n\nPlease complete this task. Plan your approach, execute the necessary steps, and provide a final report when done.")
        ]
        
        self.iteration_count = 0
        
        try:
            while self.iteration_count < self.config.max_iterations:
                self.iteration_count += 1
                self._log(f"\n--- Iteration {self.iteration_count} ---")
                
                # Get LLM response
                response = self._get_llm_response()
                
                # Check for task completion
                if "TASK_COMPLETE:" in response.content:
                    self.current_task.status = "completed"
                    self.current_task.final_report = response.content.split("TASK_COMPLETE:")[1].strip()
                    break
                
                if "TASK_FAILED:" in response.content:
                    self.current_task.status = "failed"
                    self.current_task.error = response.content.split("TASK_FAILED:")[1].strip()
                    break
                
                # Process tool calls
                if response.has_tool_calls:
                    self._process_tool_calls(response.tool_calls)
                else:
                    # No tool calls and not complete - ask for next step
                    self.messages.append(Message(
                        role="assistant",
                        content=response.content
                    ))
                    self.messages.append(Message(
                        role="user",
                        content="Continue with the task. Use the available tools to make progress."
                    ))
            
            # Check if we hit max iterations
            if self.iteration_count >= self.config.max_iterations:
                self.current_task.status = "timeout"
                self.current_task.error = f"Reached maximum iterations ({self.config.max_iterations})"
        
        except Exception as e:
            self.current_task.status = "error"
            self.current_task.error = str(e)
            self._log(f"Error: {e}")
        
        # Finalize task
        self.current_task.end_time = datetime.now().isoformat()
        self._log(f"\nTask {self.current_task.status}: {task_id}")
        
        if self.current_task.final_report:
            self._log(f"\nFinal Report:\n{self.current_task.final_report}")
        
        return self.current_task
    
    def _get_llm_response(self) -> LLMResponse:
        """Get response from LLM"""
        tools_schema = self._get_tools_schema()
        
        try:
            response = self.llm.generate(
                messages=self.messages,
                tools=tools_schema
            )
            return response
        except Exception as e:
            self._log(f"LLM error: {e}")
            raise
    
    def _process_tool_calls(self, tool_calls: List[ToolCall]):
        """Process tool calls from LLM response"""
        # Add assistant message with tool calls
        assistant_content = ""
        for tc in tool_calls:
            assistant_content += f"Calling {tc.name}({json.dumps(tc.arguments, indent=2)})\n"
        
        self.messages.append(Message(
            role="assistant",
            content=assistant_content
        ))
        
        # Execute each tool call
        for tc in tool_calls:
            step = TaskStep(
                step_number=len(self.current_task.steps) + 1,
                action=f"Execute {tc.name}",
                tool_name=tc.name,
                tool_args=tc.arguments
            )
            
            if self.on_step_start:
                self.on_step_start(step)
            
            self._log(f"Tool call: {tc.name}({json.dumps(tc.arguments)})")
            
            # Execute tool
            result = self._execute_tool(tc.name, tc.arguments)
            
            step.success = result.success
            step.result = result.output
            
            if self.on_step_end:
                self.on_step_end(step)
            
            self.current_task.steps.append(step)
            
            # Log result
            status = "SUCCESS" if result.success else "FAILED"
            self._log(f"Result ({status}): {result.output[:500]}...")
            
            # Add tool result to messages
            self.messages.append(Message(
                role="user",
                content=f"Tool {tc.name} result ({status}):\n{result.output}"
            ))
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name"""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        
        # Validate parameters
        is_valid, error = tool.validate_parameters(**arguments)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=error
            )
        
        # Execute
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
    
    def get_task_report(self) -> str:
        """Generate a human-readable task report"""
        if not self.current_task:
            return "No task has been executed yet."
        
        report = []
        report.append(f"Task Report: {self.current_task.task_id}")
        report.append(f"Status: {self.current_task.status}")
        report.append(f"Description: {self.current_task.task_description}")
        report.append(f"Start: {self.current_task.start_time}")
        report.append(f"End: {self.current_task.end_time}")
        report.append("")
        report.append("Steps:")
        
        for step in self.current_task.steps:
            status = "✓" if step.success else "✗"
            report.append(f"  {status} Step {step.step_number}: {step.action}")
            if step.tool_name:
                report.append(f"    Tool: {step.tool_name}")
            if step.result:
                result_preview = step.result[:200] + "..." if len(step.result) > 200 else step.result
                report.append(f"    Result: {result_preview}")
        
        if self.current_task.final_report:
            report.append("")
            report.append("Final Report:")
            report.append(self.current_task.final_report)
        
        if self.current_task.error:
            report.append("")
            report.append(f"Error: {self.current_task.error}")
        
        return "\n".join(report)
