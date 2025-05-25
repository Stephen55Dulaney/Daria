# DARIA LangChain Prompt Manager

This repository contains the implementation of a Prompt Management system for the DARIA Interview Tool. The system allows users to create, edit, evaluate, and improve prompts used in AI-powered interviews.

## Features

- **Structured Prompt Management**: Create and edit YAML-formatted prompts with standardized fields
- **Prompt Evaluation**: Rate prompt performance with detailed metrics
- **Version History**: Track changes to prompts over time
- **Performance Tracking**: Collect feedback and score prompts on a 1-5 scale
- **Self-Improvement**: Generate suggestions for improving prompts based on feedback

## Installation

1. Clone the repository
2. Install the requirements:
   ```
   pip install -r requirements.txt
   ```

## Components

The Prompt Manager consists of several key components:

1. **PromptManager Class**: Core functionality for managing prompts
   - Located in `tools/prompt_manager/prompt_manager.py`
   - Handles loading, saving, versioning, and evaluating prompts

2. **Templates**: UI for interacting with prompts
   - Located in `tools/prompt_manager/templates/`
   - Provides interfaces for viewing, editing, and providing feedback on prompts

3. **Integration Module**: Connects prompt manager to the main application
   - Located in `langchain_features/prompt_integration.py`
   - Simplifies adding prompt management to Flask applications

4. **Routes**: API endpoints for prompt operations
   - Located in `tools/prompt_manager/prompt_routes.py`
   - Handles HTTP requests for prompt management functions

## Running the Application

To run the standalone prompt manager application:

```bash
python run_langchain_prompt_manager.py --port 5020 --debug
```

This will start a Flask server on http://127.0.0.1:5020 that you can access in your browser.

## Prompt Structure

Prompts are structured YAML files with the following fields:

```yaml
agent_name: interviewer
version: v1.0
description: A skilled professional interviewer
role: Research Interviewer
tone: Professional, warm, curious
core_objectives:
  - Ask focused, open-ended questions
  - Actively listen and follow up appropriately
  - Maintain a conversational flow
contextual_instructions: |
  You are a skilled professional interviewer conducting research interviews.
  Your goal is to gather rich, detailed information from subjects...
dynamic_prompt_prefix: |
  This is the system prompt that will be sent to the LLM...
improvement_suggestions:
  - Add more specific examples
  - Use simpler language
metrics:
  clarity: 4.2
  relevance: 3.8
  accuracy: 4.1
  helpfulness: 4.5
  completeness: 3.9
```

## Evaluation Metrics

Prompts are evaluated based on a rubric with the following categories:

- **Clarity**: How clear and understandable is the agent's response?
- **Relevance**: How relevant is the response to the user's query?
- **Accuracy**: How accurate and factually correct is the information provided?
- **Helpfulness**: How helpful is the response in addressing the user's needs?
- **Completeness**: How complete is the response in addressing all aspects of the query?

Each category is scored on a scale of 1-5, with an overall average score calculated from these values.

## Directory Structure

```
├── langchain_features/
│   ├── templates/
│   │   └── langchain/
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── interview_archive.html
│   │       ├── interview_details.html
│   │       ├── interview_setup.html
│   │       └── interview_test.html
│   └── prompt_integration.py
├── tools/
│   └── prompt_manager/
│       ├── prompts/
│       │   ├── interviewer.yml
│       │   └── researcher.yml
│       ├── templates/
│       │   └── prompts/
│       │       ├── add_feedback.html
│       │       ├── edit_prompt.html
│       │       └── view_prompt.html
│       ├── __init__.py
│       ├── prompt_manager.py
│       └── prompt_routes.py
└── run_langchain_prompt_manager.py
```

## Integration with Other Applications

You can integrate the prompt manager into your own Flask application using the integration module:

```python
from langchain_features.prompt_integration import configure_prompt_manager

# Initialize your Flask app
app = Flask(__name__)

# Configure the prompt manager
prompt_manager = configure_prompt_manager(app, 
                                        prompt_dir="path/to/prompts", 
                                        name_prefix="optional_prefix")
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 