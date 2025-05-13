"""
Module for interacting with the CursorPrompts table in DynamoDB.
"""

import uuid
import logging
import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .database import get_dynamodb_resource, get_paginated_results

# Configure logging
logger = logging.getLogger(__name__)

# Table name
TABLE_NAME = 'CursorPrompts'


class CursorPromptsDB:
    """Class for interacting with the CursorPrompts table in DynamoDB."""
    
    def __init__(self, use_local=None):
        """
        Initialize the CursorPromptsDB object.
        
        Args:
            use_local (bool, optional): Whether to use local DynamoDB. Defaults to None.
        """
        self.dynamodb = get_dynamodb_resource(use_local)
        self.table = self.dynamodb.Table(TABLE_NAME)
    
    def create_prompt(self, opportunity_id, prompt_content, prompt_type="ui_design", metadata=None):
        """
        Create a new CursorAI prompt based on an opportunity.
        
        Args:
            opportunity_id (str): ID of the opportunity this prompt is based on.
            prompt_content (str): The prompt content to be sent to CursorAI.
            prompt_type (str, optional): Type of the prompt (e.g., 'ui_design', 'code_implementation'). 
                                        Defaults to "ui_design".
            metadata (dict, optional): Additional metadata for the prompt. Defaults to None.
        
        Returns:
            dict: The created prompt data.
        """
        prompt_id = str(uuid.uuid4())
        generated_at = datetime.datetime.now().isoformat()
        
        item = {
            'prompt_id': prompt_id,
            'opportunity_id': opportunity_id,
            'prompt_content': prompt_content,
            'prompt_type': prompt_type,
            'generated_at': generated_at,
            'status': 'created'
        }
        
        if metadata:
            item['metadata'] = metadata
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Created CursorAI prompt {prompt_id} for opportunity {opportunity_id}")
            return item
        except ClientError as e:
            logger.error(f"Error creating CursorAI prompt: {e}")
            raise
    
    def get_prompt(self, prompt_id, opportunity_id):
        """
        Get a CursorAI prompt by prompt_id and opportunity_id.
        
        Args:
            prompt_id (str): ID of the prompt to get.
            opportunity_id (str): ID of the opportunity.
        
        Returns:
            dict: The prompt data, or None if not found.
        """
        try:
            response = self.table.get_item(Key={
                'prompt_id': prompt_id,
                'opportunity_id': opportunity_id
            })
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting prompt {prompt_id}: {e}")
            raise
    
    def update_prompt(self, prompt_id, opportunity_id, updates):
        """
        Update a CursorAI prompt.
        
        Args:
            prompt_id (str): ID of the prompt to update.
            opportunity_id (str): ID of the opportunity.
            updates (dict): Dictionary of attributes to update.
        
        Returns:
            dict: The updated prompt data.
        """
        # Build update expression and attribute values
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        for key, value in updates.items():
            # Skip primary key attributes
            if key in ('prompt_id', 'opportunity_id'):
                continue
            
            update_expression += f"#{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value
            expression_attribute_names[f"#{key}"] = key
        
        # Remove trailing comma and space
        update_expression = update_expression[:-2]
        
        try:
            response = self.table.update_item(
                Key={
                    'prompt_id': prompt_id,
                    'opportunity_id': opportunity_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW"
            )
            logger.info(f"Updated prompt {prompt_id}")
            return response.get('Attributes')
        except ClientError as e:
            logger.error(f"Error updating prompt {prompt_id}: {e}")
            raise
    
    def delete_prompt(self, prompt_id, opportunity_id):
        """
        Delete a CursorAI prompt.
        
        Args:
            prompt_id (str): ID of the prompt to delete.
            opportunity_id (str): ID of the opportunity.
        
        Returns:
            bool: True if the prompt was deleted, False otherwise.
        """
        try:
            self.table.delete_item(Key={
                'prompt_id': prompt_id,
                'opportunity_id': opportunity_id
            })
            logger.info(f"Deleted prompt {prompt_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting prompt {prompt_id}: {e}")
            raise
    
    def list_prompts_by_opportunity(self, opportunity_id):
        """
        List all prompts for a specific opportunity.
        
        Args:
            opportunity_id (str): ID of the opportunity.
        
        Returns:
            list: List of prompts for the opportunity.
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('opportunity_id').eq(opportunity_id)
            }
            results = get_paginated_results(self.table, index_name='GeneratedIndex', query_kwargs=query_kwargs)
            
            # Sort by generated_at descending (newest first)
            results.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
            
            return results
        except ClientError as e:
            logger.error(f"Error listing prompts for opportunity {opportunity_id}: {e}")
            raise
    
    def update_prompt_status(self, prompt_id, opportunity_id, status):
        """
        Update the status of a CursorAI prompt.
        
        Args:
            prompt_id (str): ID of the prompt to update.
            opportunity_id (str): ID of the opportunity.
            status (str): New status for the prompt.
        
        Returns:
            dict: The updated prompt data.
        """
        return self.update_prompt(prompt_id, opportunity_id, {'status': status})
    
    def generate_prompt_from_opportunity(self, opportunity_id, persona_id=None, user_story_id=None):
        """
        Generate a structured CursorAI prompt from an opportunity and related data.
        
        Args:
            opportunity_id (str): ID of the opportunity to generate a prompt for.
            persona_id (str, optional): ID of the persona to include. Defaults to None.
            user_story_id (str, optional): ID of the user story to include. Defaults to None.
        
        Returns:
            dict: The created prompt data including the formatted prompt content.
        """
        # This would require access to OpportunitiesDB, PersonasDB, and AgileArtifactsDB
        # We'll implement a placeholder and enhance it when those modules are available
        
        # Placeholder for now - in a real implementation, we would:
        # 1. Get the opportunity details
        # 2. Get the persona details if persona_id is provided
        # 3. Get the user story details if user_story_id is provided
        # 4. Format the prompt according to the template
        
        placeholder_prompt = """
Design a user interface prototype based on the following research-based opportunity:

**Target User:** [Placeholder for persona description]

**Problem Summary:** [Placeholder for opportunity description]

**User Story:**  
"As a [user type], I want to [do something] so that [benefit]."

**Key Insights from Research:**
- [Insight 1]
- [Insight 2]

**Ethical Considerations:**  
- Respect privacy by avoiding unnecessary data collection.
- Ensure design is usable for all users.
- Avoid bias in design and functionality.

**Requested Deliverables:**  
- A wireframe or low-fidelity UI sketch
- Include core components based on the user needs
- Design should support multiple platforms/devices.

Generate the design using Figma-compatible format if possible, and return the code or markup that can be rendered by React or HTML/CSS.
"""
        
        # Create and return the prompt
        return self.create_prompt(
            opportunity_id=opportunity_id,
            prompt_content=placeholder_prompt,
            prompt_type="ui_design",
            metadata={
                "persona_id": persona_id,
                "user_story_id": user_story_id,
                "is_placeholder": True  # Flag to indicate this is a placeholder
            }
        ) 