# Prompt Manager Fix - Synthia Character

## Issue Description

The Prompt Manager is currently encountering errors when trying to view the Synthia character prompt:

```
Error: 'list object' has no attribute 'items'
```

This error suggests that the prompt manager is expecting a dictionary (with an `items()` method) but is receiving a list instead.

## Cause of the Issue

After examining `tools/prompt_manager/prompts/synthia.yml`, the likely issue is with the `evaluation_metrics` field. In Synthia's prompt file, this field is defined as a list:

```yaml
evaluation_metrics:
  - comprehensiveness: "Does the plan cover all necessary discovery activities?"
  - practicality: "Is the plan realistic given time and resource constraints?"
  - stakeholder_inclusion: "Are all relevant stakeholders engaged appropriately?"
  - methodology_mix: "Is there an appropriate mix of research methods?"
  - outcome_clarity: "Are deliverables and success criteria clearly defined?"
```

While in other character YAMLs like daria.yml, it's defined as a dictionary:

```yaml
evaluation_metrics:
  rapport_building: "How well did the agent establish rapport and comfort?"
  question_quality: "Were questions relevant, clear and insightful?"
  active_listening: "Did the agent follow up appropriately on user cues?"
  conversation_flow: "Was the conversation natural and well-paced?"
  insight_generation: "Did the interview uncover meaningful insights?"
```

The Prompt Manager view function is likely trying to call `items()` on this field, which works for dictionaries but not for lists.

## Solution

### Option 1: Fix the Synthia YAML file

Modify `tools/prompt_manager/prompts/synthia.yml` to use the same dictionary format for evaluation metrics:

```yaml
evaluation_metrics:
  comprehensiveness: "Does the plan cover all necessary discovery activities?"
  practicality: "Is the plan realistic given time and resource constraints?"
  stakeholder_inclusion: "Are all relevant stakeholders engaged appropriately?"
  methodology_mix: "Is there an appropriate mix of research methods?"
  outcome_clarity: "Are deliverables and success criteria clearly defined?"
```

### Option 2: Update the Prompt Manager code

If other character YAML files also use list format for evaluation_metrics, you might need to update the Prompt Manager code to handle both formats.

Look for the view_prompt function in run_interview_api.py, which likely contains code similar to:

```python
@app.route('/prompts/view/<prompt_id>')
def view_prompt(prompt_id):
    try:
        config = prompt_mgr.load_prompt(prompt_id)
        
        # This line might be causing the error:
        for key, value in config['evaluation_metrics'].items():
            # Process metrics
            pass
            
        # Rest of the function...
    except Exception as e:
        # Error handling
```

Update the code to handle both list and dictionary formats:

```python
@app.route('/prompts/view/<prompt_id>')
def view_prompt(prompt_id):
    try:
        config = prompt_mgr.load_prompt(prompt_id)
        
        # Check if evaluation_metrics is a list or dictionary
        eval_metrics = config.get('evaluation_metrics', {})
        formatted_metrics = {}
        
        if isinstance(eval_metrics, list):
            # Handle list format (convert to dictionary)
            for item in eval_metrics:
                if isinstance(item, dict):
                    for k, v in item.items():
                        formatted_metrics[k] = v
        else:
            # It's already a dictionary
            formatted_metrics = eval_metrics
            
        # Use formatted_metrics instead of config['evaluation_metrics']
        
        # Rest of the function...
    except Exception as e:
        # Error handling
```

## Testing the Fix

After applying either solution:

1. Restart the API server:
   ```bash
   pkill -f "python.*run_interview_api.py"
   python run_interview_api.py
   ```

2. Navigate to http://localhost:5010/prompts/

3. Try to view the Synthia character prompt again 