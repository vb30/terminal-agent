import os
import typer
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from .terminal_agent import TerminalCrew

console = Console()
app = typer.Typer()

def get_api_key() -> str:
    """Get the API key from environment variables."""
    # Try to load from .env file
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    
    # Check if the key is in environment variables
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found in environment variables or .env file.[/red]")
        console.print("[yellow]Please set your Gemini API key in a .env file or as an environment variable.[/yellow]")
        console.print("[yellow]Example .env file content: GEMINI_API_KEY=your_api_key_here[/yellow]")
        sys.exit(1)
    
    return api_key

@app.command()
def main():
    """
    Run the Terminal Agent.
    
    This agent uses a ReAct-style thinking loop to solve tasks step-by-step.
    """
    console.print("[bold blue]Welcome to the ReAct Terminal Agent![/bold blue]")
    console.print("[bold blue]This agent uses a ReAct-style thinking loop to solve your tasks step-by-step:[/bold blue]")
    console.print("[bold blue]• Think: Reasons about what to do next[/bold blue]")
    console.print("[bold blue]• Act: Executes commands automatically[/bold blue]")
    console.print("[bold blue]• Observe: Processes the results and continues[/bold blue]")
    console.print("[bold yellow]All commands are executed automatically and the agent can chain multiple steps together![/bold yellow]")
    console.print("[bold yellow]You'll see the agent's thought process as it works on your request.[/bold yellow]")
    console.print("Type your requests in natural language. Type 'exit' to quit.\n")
    
    # Get API key and initialize the agent
    api_key = get_api_key()
    agent = TerminalCrew(api_key=api_key)
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_input = console.input("[bold green]>>> [/bold green]")
            
            # Exit condition
            if user_input.lower() in ("exit", "quit", "bye"):
                console.print("[bold blue]Goodbye![/bold blue]")
                break
            
            # Process the user request
            agent.process_request(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[bold blue]Exiting Terminal Agent...[/bold blue]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")

if __name__ == "__main__":
    app() 