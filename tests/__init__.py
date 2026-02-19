"""
Tests for Super Agent
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig(unittest.TestCase):
    """Test configuration module"""
    
    def test_default_config(self):
        """Test default configuration creation"""
        from super_agent.config import AgentConfig
        
        config = AgentConfig()
        self.assertEqual(config.name, "SuperAgent")
        self.assertEqual(config.max_iterations, 100)
        self.assertEqual(config.llm.provider, "openai")
        self.assertEqual(config.llm.model, "gpt-4")
    
    def test_load_config(self):
        """Test loading configuration"""
        from super_agent.config import load_config
        
        # Load without file (use defaults)
        config = load_config()
        self.assertIsNotNone(config)
        self.assertIsInstance(config.max_iterations, int)


class TestTools(unittest.TestCase):
    """Test tools module"""
    
    def test_tool_result(self):
        """Test ToolResult dataclass"""
        from super_agent.tools.base import ToolResult
        
        result = ToolResult(success=True, output="test output")
        self.assertTrue(result.success)
        self.assertEqual(result.output, "test output")
        self.assertIsNone(result.error)
    
    def test_file_read_tool_schema(self):
        """Test FileReadTool schema"""
        from super_agent.tools.file_tools import FileReadTool
        
        tool = FileReadTool()
        schema = tool.get_schema()
        
        self.assertEqual(schema['name'], 'file_read')
        self.assertIn('path', schema['parameters']['required'])


class TestLLM(unittest.TestCase):
    """Test LLM module"""
    
    def test_message_dataclass(self):
        """Test Message dataclass"""
        from super_agent.llm.base import Message
        
        msg = Message(role="user", content="Hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")
        
        msg_dict = msg.to_dict()
        self.assertEqual(msg_dict['role'], "user")
        self.assertEqual(msg_dict['content'], "Hello")
    
    def test_tool_call_dataclass(self):
        """Test ToolCall dataclass"""
        from super_agent.llm.base import ToolCall
        
        tc = ToolCall(id="123", name="test_tool", arguments={"arg1": "value1"})
        self.assertEqual(tc.id, "123")
        self.assertEqual(tc.name, "test_tool")
        self.assertEqual(tc.arguments["arg1"], "value1")
    
    def test_llm_response(self):
        """Test LLMResponse dataclass"""
        from super_agent.llm.base import LLMResponse, ToolCall
        
        response = LLMResponse(content="Hello")
        self.assertFalse(response.has_tool_calls)
        
        response_with_tools = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="1", name="tool", arguments={})]
        )
        self.assertTrue(response_with_tools.has_tool_calls)


class TestAgent(unittest.TestCase):
    """Test Agent module"""
    
    def test_task_step_dataclass(self):
        """Test TaskStep dataclass"""
        from super_agent.agent import TaskStep
        
        step = TaskStep(step_number=1, action="Test action")
        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.action, "Test action")
        self.assertFalse(step.success)
    
    def test_task_execution_dataclass(self):
        """Test TaskExecution dataclass"""
        from super_agent.agent import TaskExecution
        
        task = TaskExecution(task_id="test_001", task_description="Test task")
        self.assertEqual(task.task_id, "test_001")
        self.assertEqual(task.status, "pending")
        self.assertEqual(len(task.steps), 0)
    
    def test_agent_initialization(self):
        """Test Agent initialization"""
        from super_agent.agent import Agent
        from super_agent.config import AgentConfig
        
        config = AgentConfig()
        config.llm.api_key = "test_key"  # Set a test key
        
        agent = Agent(config)
        self.assertIsNotNone(agent.config)
        self.assertIsNotNone(agent.llm)
        self.assertGreater(len(agent.tools), 0)
    
    def test_agent_available_tools(self):
        """Test Agent available tools"""
        from super_agent.agent import Agent
        from super_agent.config import AgentConfig
        
        config = AgentConfig()
        config.llm.api_key = "test_key"
        
        agent = Agent(config)
        tools = agent.get_available_tools()
        
        self.assertIn("file_read", tools)
        self.assertIn("file_write", tools)
        self.assertIn("execute_command", tools)


if __name__ == "__main__":
    unittest.main()
