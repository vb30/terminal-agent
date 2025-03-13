import os
import sys
import re
import json
import time
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from rich.syntax import Syntax
from dotenv import load_dotenv, find_dotenv

import google.generativeai as genai

console = Console()

class AgentRole(Enum):
    TERMINAL = "terminal_assistant"

class Tool:
    """A tool that can be used by the agent."""
    
    def __init__(self, name: str, description: str, func):
        self.name = name
        self.description = description
        self.func = func
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class AgentAction:
    """An action taken by the agent."""
    
    def __init__(self, tool: str, tool_input: str, log: str = None):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log or f"Using {tool} with input: {tool_input}"

class AgentFinish:
    """Indicates the agent has finished."""
    
    def __init__(self, return_values: Dict[str, Any], log: str = None):
        self.return_values = return_values
        self.log = log or "Agent has finished."

class TerminalAgent:
    """A ReAct style agent that can use tools to achieve goals."""
    
    def __init__(self, api_key: str, tools: List[Tool]):
        self.api_key = api_key
        self.tools = tools
        self.tool_names = [tool.name for tool in tools]
        self.tool_descriptions = {tool.name: tool.description for tool in tools}
        
        # Combine tools into a mapping of name to tool
        self.tool_mapping = {tool.name: tool for tool in tools}
        
        # Initialize Gemini model with more permissive safety settings
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash',
            safety_settings=safety_settings
        )
    
    def get_react_system_prompt(self) -> str:
        """Get the ReAct system prompt for the terminal agent."""
        base_prompt = f"""You are an AI assistant that helps with terminal operations and file exploration.
You have access to the following tools:

"""
        # Add tool descriptions
        for tool_name, description in self.tool_descriptions.items():
            base_prompt += f"{tool_name}: {description}\n"
        
        base_prompt += """
To use a tool, please use the following format:
```
Thought: I need to analyze the problem and decide what to do
Action: tool_name
Action Input: the input to the tool
```

After you use a tool, I'll show you the output. You can then continue with:
```
Observation: [tool output will appear here]
Thought: I need to analyze the output and decide what to do next
Action: another_tool_name
Action Input: another input
```

When you have completed the task, respond with:
```
Thought: I have completed the task
Final Answer: [your detailed response]
```

Start by analyzing the user request and determining what tools you need to use.
ALWAYS begin with a "Thought:" where you think step-by-step about how to solve the problem.
ALWAYS follow the Thought, Action, Action Input, Observation pattern until you have the information needed, then conclude with Final Answer.

As the Terminal Assistant, you should:
- Execute shell commands to help the user
- Provide explanations of what commands do
- Be precise and thorough
- Take initiative to complete the full workflow without asking for additional inputs
- Use multiple commands in sequence when needed to solve complex tasks
- Explore and explain files and directories as needed
- Read and explain code and configuration files when asked
"""
        
        return base_prompt
    
    def parse_agent_response(self, text: str) -> Tuple[Any, bool]:
        """Parse the agent's response to extract tool calls or final answers."""
        # Check if the response contains a final answer
        final_answer_match = re.search(r"Final Answer: (.*?)(?:$|```)", text, re.DOTALL)
        if final_answer_match:
            return AgentFinish(
                return_values={"output": final_answer_match.group(1).strip()},
                log=f"Final Answer: {final_answer_match.group(1).strip()}"
            ), True
        
        # Look for thought, action, action input pattern
        thought_match = re.search(r"Thought: (.*?)(?:Action:|Final Answer:|$)", text, re.DOTALL)
        action_match = re.search(r"Action: (.*?)(?:Action Input:|$)", text, re.DOTALL)
        action_input_match = re.search(r"Action Input: (.*?)(?:Observation:|Thought:|$)", text, re.DOTALL)
        
        if action_match and action_input_match:
            tool = action_match.group(1).strip()
            tool_input = action_input_match.group(1).strip()
            thought = thought_match.group(1).strip() if thought_match else ""
            
            return AgentAction(
                tool=tool,
                tool_input=tool_input,
                log=f"Thought: {thought}\nAction: {tool}\nAction Input: {tool_input}"
            ), False
        
        # If no pattern is found, treat the whole thing as a final answer
        return AgentFinish(
            return_values={"output": text.strip()},
            log=f"Unparsed response treated as final answer: {text.strip()}"
        ), True
    
    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a query using ReAct style agent."""
        # Initialize the chat
        chat = self.model.start_chat(history=[])
        
        # Start with system prompt
        system_prompt = self.get_react_system_prompt()
        
        # Add context to the prompt if available
        user_prompt = query
        if context:
            if "working_dir" in context:
                user_prompt += f"\nCurrent working directory: {context['working_dir']}"
            if "command_history" in context and context["command_history"]:
                user_prompt += "\nPrevious command results:\n"
                for cmd, output in context["command_history"][-3:]:  # Only include last 3 for brevity
                    user_prompt += f"Command: {cmd}\nOutput: {output}\n\n"
        
        # Initialize the conversation with system prompt and user query
        response = chat.send_message(f"{system_prompt}\n\nUser request: {user_prompt}")
        
        # Initialize conversation history for tracking
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response.text}
        ]
        
        # Parse the response to get action or final answer
        action_or_finish, is_done = self.parse_agent_response(response.text)
        
        # Keep track of all thoughts, actions, and observations for final response
        agent_steps = [response.text]
        
        # Maximum iterations to prevent infinite loops
        max_iterations = 10
        iteration = 0
        
        # Continue the conversation until we get a final answer or reach max iterations
        while not is_done and iteration < max_iterations:
            iteration += 1
            
            if isinstance(action_or_finish, AgentAction):
                # Execute the tool if it exists
                tool_name = action_or_finish.tool
                tool_input = action_or_finish.tool_input
                
                console.print(f"[cyan]Agent is using tool: {tool_name}[/cyan]")
                console.print(f"[cyan]Tool input: {tool_input}[/cyan]")
                
                observation = "Tool execution failed: Tool not found"
                
                if tool_name in self.tool_mapping:
                    try:
                        tool = self.tool_mapping[tool_name]
                        observation = tool(tool_input)
                        if observation is None:
                            observation = "Tool executed successfully but returned no output."
                        elif isinstance(observation, dict):
                            # If a complex object is returned, convert to string representation
                            observation = json.dumps(observation, indent=2)
                    except Exception as e:
                        observation = f"Error executing tool: {str(e)}"
                
                console.print(f"[dim]Observation:[/dim]")
                console.print(Syntax(str(observation), "text", theme="monokai", word_wrap=True))
                
                # Add the observation to the conversation
                next_input = f"Observation: {observation}"
                conversation.append({"role": "user", "content": next_input})
                agent_steps.append(next_input)
                
                # Send the observation to the agent
                response = chat.send_message(next_input)
                conversation.append({"role": "assistant", "content": response.text})
                agent_steps.append(response.text)
                
                # Parse the new response
                action_or_finish, is_done = self.parse_agent_response(response.text)
            else:
                # This shouldn't happen, but just in case
                break
        
        # If we reach max iterations without finishing, force a final answer
        if iteration >= max_iterations and not is_done:
            console.print("[yellow]Reached maximum iterations without final answer. Forcing completion.[/yellow]")
            final_prompt = "You've taken several steps but need to conclude now. Please provide your Final Answer based on what you've learned so far."
            response = chat.send_message(final_prompt)
            conversation.append({"role": "user", "content": final_prompt})
            conversation.append({"role": "assistant", "content": response.text})
            agent_steps.append(final_prompt)
            agent_steps.append(response.text)
            
            action_or_finish, is_done = self.parse_agent_response(response.text)
            if not is_done:
                # If still no final answer, create one from the response
                action_or_finish = AgentFinish(
                    return_values={"output": response.text.strip()},
                    log=f"Forced final answer: {response.text.strip()}"
                )
        
        if isinstance(action_or_finish, AgentFinish):
            final_output = action_or_finish.return_values["output"]
        else:
            final_output = "Agent did not complete with a final answer."
        
        return {
            "response_text": final_output,
            "agent_steps": agent_steps,
            "commands_executed": [step for step in agent_steps if "Action: execute_command" in step]
        }

class TerminalCrew:
    """A simplified terminal agent that handles user requests."""
    
    def __init__(self, api_key: str):
        """Initialize the Terminal Agent with Gemini API key."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.working_dir = Path.cwd()
        
        # Create tools for the agent
        tools = [
            Tool(
                name="execute_command",
                description="Executes a shell command and returns the output. Use this for running terminal commands.",
                func=self.execute_command
            ),
            Tool(
                name="read_file",
                description="Reads the contents of a file. Input should be the path to the file.",
                func=self.read_file
            ),
            Tool(
                name="list_directory",
                description="Lists the contents of a directory. Input should be the path to the directory or '.' for current directory.",
                func=self.list_directory
            ),
            Tool(
                name="find_files",
                description="Finds files matching a pattern. Input should be a glob pattern like '*.py' or a search term.",
                func=self.find_files
            )
        ]
        
        # Create terminal agent
        self.terminal_agent = TerminalAgent(
            api_key=api_key,
            tools=tools
        )
        
        # Command history for context
        self.command_history = []
    
    def execute_command(self, command: str) -> str:
        """Execute a shell command and return the output."""
        try:
            # Change to the working directory before executing
            original_dir = os.getcwd()
            os.chdir(str(self.working_dir))
            
            console.print(f"[yellow]Executing command: {escape(command)}[/yellow]")
            
            # Use subprocess directly for better reliability
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception on non-zero exit
            )
            
            # Get the output
            stdout = process.stdout
            stderr = process.stderr
            
            # Combine stdout and stderr if there's an error
            output = stdout
            if process.returncode != 0:
                output = f"{stdout}\n{stderr}" if stdout else stderr
                console.print(f"[red]Command failed with exit code {process.returncode}[/red]")
            
            # Change back to original directory
            os.chdir(original_dir)
            
            # Add to history
            self.command_history.append((command, output))
            if len(self.command_history) > 5:  # Keep history manageable
                self.command_history.pop(0)
            
            return output
        except Exception as e:
            error_message = str(e)
            console.print(f"[red]Error during command execution: {error_message}[/red]")
            # Add failed command to history
            self.command_history.append((command, f"ERROR: {error_message}"))
            return f"ERROR: {error_message}"
    
    def read_file(self, file_path: str) -> str:
        """Read the contents of a file."""
        try:
            # Resolve the file path relative to the working directory
            full_path = (self.working_dir / file_path).resolve()
            
            console.print(f"[blue]Reading file: {escape(str(full_path))}[/blue]")
            
            # Check if the file exists
            if not full_path.exists():
                error = f"File not found: {file_path}"
                console.print(f"[red]{error}[/red]")
                return error
            
            # Check if it's a text file (simple heuristic)
            try:
                content = full_path.read_text(errors='replace')
                return content
            except UnicodeDecodeError:
                return f"Unable to read {file_path} as text. It may be a binary file."
        except Exception as e:
            error_message = str(e)
            console.print(f"[red]Error reading file: {error_message}[/red]")
            return f"ERROR: {error_message}"
    
    def list_directory(self, directory_path: str = ".") -> str:
        """List the contents of a directory."""
        try:
            # Resolve the directory path relative to the working directory
            if directory_path == ".":
                full_path = self.working_dir
            else:
                full_path = (self.working_dir / directory_path).resolve()
            
            console.print(f"[blue]Listing directory: {escape(str(full_path))}[/blue]")
            
            # Check if the directory exists
            if not full_path.exists():
                error = f"Directory not found: {directory_path}"
                console.print(f"[red]{error}[/red]")
                return error
            
            # Get the directory contents
            result = f"Contents of {full_path}:\n"
            for item in full_path.iterdir():
                # Format the output like ls -l
                item_stat = item.stat()
                item_type = "d" if item.is_dir() else "-"
                item_size = item_stat.st_size
                item_modified = time.ctime(item_stat.st_mtime)
                result += f"{item_type} {item_size:8d} {item_modified} {item.name}\n"
            
            return result
        except Exception as e:
            error_message = str(e)
            console.print(f"[red]Error listing directory: {error_message}[/red]")
            return f"ERROR: {error_message}"
    
    def find_files(self, pattern: str) -> str:
        """Find files matching a pattern."""
        try:
            console.print(f"[blue]Finding files matching: {escape(pattern)}[/blue]")
            
            # Use the find command for more powerful searching
            command = f"find . -type f -name '{pattern}' -o -path '*{pattern}*' 2>/dev/null | sort"
            result = self.execute_command(command)
            
            if not result.strip():
                return f"No files matching '{pattern}' found in {self.working_dir}"
            
            return f"Files matching '{pattern}':\n{result}"
        except Exception as e:
            error_message = str(e)
            console.print(f"[red]Error finding files: {error_message}[/red]")
            return f"ERROR: {error_message}"
    
    def process_request(self, user_input: str) -> None:
        """Process user request using the terminal agent."""
        try:
            # Handle special commands
            if user_input.lower().startswith("cd "):
                path = user_input[3:].strip()
                if self.change_directory(path):
                    console.print(f"[green]Changed directory to: {self.working_dir}[/green]")
                else:
                    console.print(f"[red]Failed to change directory to: {path}[/red]")
                return
            
            # Prepare context for the agent
            context = {
                "working_dir": self.working_dir,
                "command_history": self.command_history
            }
            
            # Get response from the terminal agent
            console.print("[bold]Processing your request...[/bold]")
            terminal_result = self.terminal_agent.process(user_input, context)
            
            # Print the agent's steps (for debugging/transparency)
            for i, step in enumerate(terminal_result.get("agent_steps", [])):
                if i % 2 == 0:  # Assistant messages
                    console.print(Panel(
                        step,
                        title=f"Agent Thinking Step {i//2 + 1}",
                        border_style="blue"
                    ))
                else:  # Observation messages
                    if step.startswith("Observation:"):
                        # Don't print these as they were already shown during execution
                        pass
            
            # Print the final response
            console.print(Panel(
                terminal_result["response_text"],
                title=f"Terminal Assistant Final Response",
                border_style="green"
            ))
                
        except Exception as e:
            console.print(f"[red]Error processing request: {str(e)}[/red]")
    
    def change_directory(self, path: str) -> bool:
        """Change the working directory."""
        try:
            new_path = (self.working_dir / path).resolve()
            if new_path.exists():
                self.working_dir = new_path
                os.chdir(str(new_path))  # Actually change the OS working directory
                return True
            return False
        except Exception:
            return False

# For backward compatibility
CustomCrew = TerminalCrew 
