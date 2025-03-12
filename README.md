# Terminal Agent

An AI-powered terminal assistant using Google's Gemini 2.0 that can execute commands, explore file systems, and explain files using a ReAct (Reasoning + Acting) approach.

## Features

- **Multi-step Reasoning**: The agent uses a ReAct approach to think, plan, execute, and observe in steps
- **Autonomous Execution**: Automatically executes commands to complete tasks
- **File System Navigation**: Explore directories and find files
- **File Analysis**: Read and explain file contents
- **Command Chaining**: Execute multiple related commands to complete complex tasks

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/terminal-agent.git
cd terminal-agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

Before using the terminal agent, you need to set up your Gemini API key:

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/)
2. Create a `.env` file in the project root with:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

Then run the terminal agent:

```bash
terminal-agent
```

### Example commands:

- "Show me all Python files in this project"
- "Explain what's in the README.md file"
- "Create a simple example script"
- "Find all imports in the code"
- "Install numpy and show its version"

## How It Works

The Terminal Agent uses a ReAct (Reasoning + Acting) architecture:

1. **Think**: The agent analyzes the user request and plans the steps needed
2. **Act**: It executes commands or reads files as needed
3. **Observe**: It processes the results of its actions
4. **Repeat**: It continues this cycle until it completes the task

## Requirements

- Python 3.8+
- Google Gemini API key
- Required packages (installed automatically):
  - google-generativeai
  - python-dotenv
  - rich
  - typer

## Development

To set up the development environment:

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.