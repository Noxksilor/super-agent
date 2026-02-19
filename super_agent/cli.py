#!/usr/bin/env python3
"""
Command-line interface for Super Agent
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional

from .config import AgentConfig, load_config, save_config
from .agent import Agent


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        prog="super-agent",
        description="Autonomous AI agent for PC automation"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command - execute a task
    run_parser = subparsers.add_parser("run", help="Execute a task")
    run_parser.add_argument(
        "task",
        help="Task description to execute"
    )
    run_parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    run_parser.add_argument(
        "--task-id", "-t",
        help="Custom task ID"
    )
    run_parser.add_argument(
        "--provider", "-p",
        choices=["openai", "anthropic", "google"],
        help="LLM provider to use"
    )
    run_parser.add_argument(
        "--model", "-m",
        help="Model to use"
    )
    run_parser.add_argument(
        "--max-iterations",
        type=int,
        help="Maximum number of iterations"
    )
    run_parser.add_argument(
        "--output", "-o",
        help="Output file for task report (JSON)"
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", help="Interactive mode")
    interactive_parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    
    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize default configuration file"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--set-provider",
        help="Set LLM provider"
    )
    config_parser.add_argument(
        "--set-model",
        help="Set LLM model"
    )
    config_parser.add_argument(
        "--set-api-key",
        help="Set API key (use environment variable for security)"
    )
    config_parser.add_argument(
        "--add-dir",
        help="Add allowed directory"
    )
    config_parser.add_argument(
        "--add-command",
        help="Add allowed command"
    )
    config_parser.add_argument(
        "--file",
        help="Configuration file path"
    )
    
    # Tools command
    tools_parser = subparsers.add_parser("tools", help="List available tools")
    tools_parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check system status")
    status_parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    
    return parser


def cmd_run(args) -> int:
    """Execute a task"""
    # Load configuration
    config = load_config(args.config)
    
    # Override with command-line arguments
    if args.provider:
        config.llm.provider = args.provider
    if args.model:
        config.llm.model = args.model
    if args.max_iterations:
        config.max_iterations = args.max_iterations
    
    # Check API key
    if not config.llm.api_key:
        print("Error: No API key configured.")
        print("Set environment variable (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)")
        print("Or use --config to specify a configuration file with api_key.")
        return 1
    
    # Create agent
    agent = Agent(config)
    
    # Set up logging
    if args.verbose:
        def log_callback(msg):
            print(msg)
        agent.on_log = log_callback
    
    # Execute task
    print(f"\n{'='*60}")
    print(f"Super Agent - Starting Task")
    print(f"{'='*60}")
    print(f"Task: {args.task}")
    print(f"Provider: {config.llm.provider}")
    print(f"Model: {config.llm.model}")
    print(f"{'='*60}\n")
    
    result = agent.execute_task(args.task, args.task_id)
    
    # Print report
    print("\n" + "="*60)
    print("Task Report")
    print("="*60)
    print(agent.get_task_report())
    
    # Save output if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to: {args.output}")
    
    # Return appropriate exit code
    if result.status == "completed":
        return 0
    elif result.status == "failed":
        return 1
    else:
        return 2


def cmd_interactive(args) -> int:
    """Run in interactive mode"""
    config = load_config(args.config)
    
    # Check API key
    if not config.llm.api_key:
        print("Error: No API key configured.")
        print("Set environment variable (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)")
        return 1
    
    agent = Agent(config)
    
    print("\n" + "="*60)
    print("Super Agent - Interactive Mode")
    print("="*60)
    print("Type your task and press Enter. The agent will execute it autonomously.")
    print("Type 'exit' or 'quit' to exit.")
    print("Type 'tools' to see available tools.")
    print("Type 'status' to check system status.")
    print("="*60 + "\n")
    
    while True:
        try:
            task = input("\n> ").strip()
            
            if not task:
                continue
            
            if task.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            if task.lower() == 'tools':
                print("\nAvailable tools:")
                for tool_name in agent.get_available_tools():
                    print(f"  - {tool_name}")
                continue
            
            if task.lower() == 'status':
                print("\nSystem status:")
                print(f"  Provider: {config.llm.provider}")
                print(f"  Model: {config.llm.model}")
                print(f"  Max iterations: {config.max_iterations}")
                print(f"  PS-Agent path: {config.ps_agent_mvp_path}")
                print(f"  n8n endpoint: {config.n8n_endpoint}")
                continue
            
            # Execute task
            print(f"\nExecuting task: {task}")
            print("-" * 40)
            
            result = agent.execute_task(task)
            
            print("\n" + "-" * 40)
            print(agent.get_task_report())
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break
    
    return 0


def cmd_config(args) -> int:
    """Manage configuration"""
    config_file = args.file or "super_agent_config.json"
    
    if args.init:
        # Create default configuration
        config = AgentConfig()
        save_config(config, config_file)
        print(f"Created configuration file: {config_file}")
        print("Edit this file to set your API key and preferences.")
        return 0
    
    if args.show:
        if os.path.exists(config_file):
            config = load_config(config_file)
            print(f"Configuration from: {config_file}")
            print(f"  Provider: {config.llm.provider}")
            print(f"  Model: {config.llm.model}")
            print(f"  Max iterations: {config.max_iterations}")
            print(f"  Log level: {config.log_level}")
            print(f"  Log dir: {config.log_dir}")
            print(f"  PS-Agent path: {config.ps_agent_mvp_path}")
            print(f"  n8n endpoint: {config.n8n_endpoint}")
            print(f"  Allowed commands: {config.tools.allowed_commands}")
            print(f"  Allowed directories: {config.tools.allowed_directories}")
        else:
            print(f"Configuration file not found: {config_file}")
            print("Use --init to create a default configuration.")
        return 0
    
    # Modify configuration
    if not os.path.exists(config_file):
        print(f"Configuration file not found: {config_file}")
        print("Use --init to create a default configuration first.")
        return 1
    
    config = load_config(config_file)
    
    if args.set_provider:
        config.llm.provider = args.set_provider
        print(f"Set provider: {args.set_provider}")
    
    if args.set_model:
        config.llm.model = args.set_model
        print(f"Set model: {args.set_model}")
    
    if args.set_api_key:
        config.llm.api_key = args.set_api_key
        print("Set API key (hidden)")
    
    if args.add_dir:
        if args.add_dir not in config.tools.allowed_directories:
            config.tools.allowed_directories.append(args.add_dir)
            print(f"Added allowed directory: {args.add_dir}")
    
    if args.add_command:
        if args.add_command not in config.tools.allowed_commands:
            config.tools.allowed_commands.append(args.add_command)
            print(f"Added allowed command: {args.add_command}")
    
    # Save changes
    save_config(config, config_file)
    print(f"Configuration saved to: {config_file}")
    
    return 0


def cmd_tools(args) -> int:
    """List available tools"""
    config = load_config(args.config)
    agent = Agent(config)
    
    print("\nAvailable tools:")
    print("="*60)
    
    for tool_name in agent.get_available_tools():
        tool = agent.tools[tool_name]
        print(f"\n{tool_name}:")
        print(f"  {tool.description}")
    
    return 0


def cmd_status(args) -> int:
    """Check system status"""
    config = load_config(args.config)
    
    print("\nSuper Agent Status")
    print("="*60)
    
    # LLM status
    print(f"\nLLM Configuration:")
    print(f"  Provider: {config.llm.provider}")
    print(f"  Model: {config.llm.model}")
    print(f"  API Key: {'configured' if config.llm.api_key else 'NOT SET'}")
    
    # PS-Agent status
    print(f"\nPS-Agent-MVP:")
    print(f"  Path: {config.ps_agent_mvp_path}")
    if os.path.exists(config.ps_agent_mvp_path):
        print(f"  Status: Found")
        orchestrator = os.path.join(config.ps_agent_mvp_path, "orchestrator.py")
        if os.path.exists(orchestrator):
            print(f"  Orchestrator: Available")
    else:
        print(f"  Status: NOT FOUND")
    
    # n8n status
    print(f"\nn8n:")
    print(f"  Endpoint: {config.n8n_endpoint}")
    
    # Allowed directories
    print(f"\nAllowed Directories:")
    for d in config.tools.allowed_directories:
        exists = "exists" if os.path.exists(d) else "not found"
        print(f"  - {d} ({exists})")
    
    # Allowed commands
    print(f"\nAllowed Commands:")
    print(f"  {', '.join(config.tools.allowed_commands)}")
    
    return 0


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Dispatch to command handler
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "interactive":
        return cmd_interactive(args)
    elif args.command == "config":
        return cmd_config(args)
    elif args.command == "tools":
        return cmd_tools(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
