# Prompt Manager

A flexible YAML-based prompt management system for LLMs with evaluation, versioning, and feedback tracking.

## Overview

The Prompt Manager is a tool for creating, editing, and managing prompt templates for LLMs. It includes features for:

- Creating and editing prompt templates in YAML format
- Version tracking and history
- Feedback collection and performance analysis
- Web-based UI for prompt management

## Directory Structure

```
prompt_manager/
├── prompts/                # YAML prompt template files
│   ├── askia.yml           # Interview question assistant
│   ├── daria.yml           # Interviewer
│   ├── thesea.yml          # Persona analyzer
│   ├── odessia.yml         # Journey mapper
│   ├── eurekia.yml         # Opportunity identifier
│   └── skeptica.yml        # Assumption challenger
├── templates/              # HTML templates for web UI
│   └── prompts/            # Prompt manager templates
├── prompt_manager.py       # Core prompt management logic
├── prompt_routes.py        # Flask routes for web UI
├── requirements.txt        # Required packages
└── README.md               # This file
```

## Integration Guide

To integrate the Prompt Manager into your application:

1. Install the required dependencies:
   ```
   pip install -r tools/prompt_manager/requirements.txt
   ```

2. Copy the `prompt_manager` directory to your application

3. Register the prompt routes in your Flask application:
   ```python
   from tools.prompt_manager.prompt_routes import register_prompt_routes
   
   # Initialize your Flask app
   app = Flask(__name__)
   
   # Register prompt routes
   register_prompt_routes(app)
   ```

4. Access the Prompt Manager at `/prompts/` in your application

## Creating Custom Prompts

Prompt templates use YAML format and support the following fields:

- `agent_name`: Name of the agent/persona
- `version`: Version string (e.g., "v1.0")
- `description`: Brief description of the agent's purpose
- `role`: The role the agent plays
- `tone`: Tone descriptors (e.g., "Empathetic, professional")
- `core_objectives`: List of primary goals
- `contextual_instructions`: Specific guidance for the agent
- `dynamic_prompt_prefix`: Text prepended to every prompt
- `evaluation_metrics`: Metrics for evaluating performance
- `evaluation_notes`: Historical notes on prompt evolution

Example:
```yaml
agent_name: ExampleAgent
version: v1.0
description: >
  Example agent description
role: Assistant
tone: Helpful, friendly
core_objectives:
  - Help users with tasks
  - Provide accurate information
contextual_instructions: |
  - Be concise
  - Use examples when helpful
dynamic_prompt_prefix: |
  You are ExampleAgent, a helpful assistant.
evaluation_metrics:
  helpfulness: "How helpful are responses?"
  accuracy: "How accurate is the information?"
evaluation_notes:
  - "Initial version created"
```

## Customization

The Prompt Manager can be customized by:

1. Modifying the templates in the `templates/prompts/` directory
2. Extending the `PromptManager` class in `prompt_manager.py`
3. Adding new routes in `prompt_routes.py`

## License

This tool is provided for use within your projects. 