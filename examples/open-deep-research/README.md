# Open Deep Research Agent

A powerful research assistant agent that can perform deep web searches, analyze documents, and handle visual content. This agent is designed to help with complex research tasks by combining web browsing capabilities with document analysis and visual understanding.

## Features

- 🌐 Advanced web browsing with multiple navigation tools
- 📄 Document inspection and analysis capabilities
- 👁️ Visual content understanding and analysis
- 🔍 Archive search functionality
- 📚 Support for various file formats (PDF, TXT, etc.)
- 🤖 Multi-agent architecture with specialized agents for different tasks

## Framework Components Used

This example demonstrates several advanced features of the Galadriel framework:

- `CodeAgent`: Main agent capable of executing Python code and managing other agents
- `ToolCallingAgent`: Specialized agent for web searching and browsing
- `GradioClient`: Handles input/output through a Gradio interface
- `LiteLLMModel`: Integration with language models
- Custom tools:
  - `SimpleTextBrowser`: Advanced web browsing capabilities
  - `TextInspectorTool`: Document analysis
  - Various browser tools (Search, Visit, PageUp/Down, Find, etc.)
  - Visual QA tool for image analysis

## Setup and Running

1. Setup local env and install `galadriel` and required dependencies:

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file with the following variables:

```bash
OPENAI_API_KEY=
SERPAPI_API_KEY=  # Optional, for enhanced search capabilities
```

3. Run the agent:

```bash
python agent.py
```

## Supported Libraries

The agent comes with a pre-authorized set of Python libraries for various analysis tasks:
- Data analysis: pandas, numpy, scipy, sklearn
- Scientific computing: sympy
- Web scraping: requests, bs4
- File handling: zipfile, PyPDF2, pptx
- Machine learning: torch
- Bioinformatics: Bio
- And many more!

## Architecture

The system uses a multi-agent architecture:
- A manager agent (`CodeAgent`) that oversees the entire operation and can execute Python code
- A specialized web browsing agent (`ToolCallingAgent`) for handling internet searches and navigation
- Various tools for document inspection, visual analysis, and web browsing

## Usage

The agent can be used for complex research tasks such as:
- Searching and analyzing web content
- Processing and analyzing documents
- Understanding visual content
- Performing comparative analysis of different sources
- Handling multiple file formats and data types

The agent maintains context during conversations and can perform multi-step research tasks while providing detailed summaries of its findings.