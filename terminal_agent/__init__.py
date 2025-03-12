"""
Terminal Agent - An AI-powered terminal assistant using Google's Gemini 2.0

This package provides a ReAct-style terminal agent that can:
- Execute shell commands
- Read and analyze files
- Explore file systems
- Chain commands in a step-by-step reasoning process

The agent thinks, takes actions, and observes results to complete complex tasks.
"""

__version__ = "0.1.0"

from .terminal_agent import TerminalCrew, Tool 