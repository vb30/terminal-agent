from setuptools import setup, find_packages

setup(
    name="terminal-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.8.4",
        "python-dotenv==1.0.1",
        "rich==13.9.4",
        "typer==0.15.2"
    ],
    entry_points={
        "console_scripts": [
            "terminal-agent=terminal_agent.cli:app",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="An AI-powered terminal agent using Google's Gemini 2.0",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/terminal-agent",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 