"""
Module for interacting with the Transcripts table in DynamoDB.
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
TABLE_NAME = 'Transcripts'


class TranscriptsDB:
    """Class for interacting with the Transcripts table in DynamoDB."""
    
    def __init__(self, use_local=None):
        """
        Initialize the TranscriptsDB object.
        
        Args:
            use_local (bool, optional): Whether to use local DynamoDB. Defaults to None.
        """
        self.dynamodb = get_dynamodb_resource(use_local)
        self.table = self.dynamodb.Table(TABLE_NAME)
    
    def add_message(self, session_id, role, content, analysis=None):
        """
        Add a message to a transcript.
        
        Args:
            session_id (str): ID of the interview session.
            role (str): Role of the message sender ('assistant', 'user', 'system').
            content (str): Content of the message.
            analysis (dict, optional): Analysis data for the message. Defaults to None.
        
        Returns:
            dict: The created message data.
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        item = {
            'session_id': session_id,
            'message_id': message_id,
            'role': role,
            'content': content,
            'timestamp': timestamp
        }
        
        if analysis:
            item['analysis'] = analysis
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Added message {message_id} to session {session_id}")
            return item
        except ClientError as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            raise
    
    def get_message(self, session_id, message_id):
        """
        Get a message from a transcript.
        
        Args:
            session_id (str): ID of the interview session.
            message_id (str): ID of the message to get.
        
        Returns:
            dict: The message data, or None if not found.
        """
        try:
            response = self.table.get_item(Key={
                'session_id': session_id,
                'message_id': message_id
            })
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting message {message_id} from session {session_id}: {e}")
            raise
    
    def update_message(self, session_id, message_id, updates):
        """
        Update a message in a transcript.
        
        Args:
            session_id (str): ID of the interview session.
            message_id (str): ID of the message to update.
            updates (dict): Dictionary of attributes to update.
        
        Returns:
            dict: The updated message data.
        """
        # Build update expression and attribute values
        update_expression = "SET "
        expression_attribute_values = {}
        
        for key, value in updates.items():
            # Skip primary key attributes
            if key in ('session_id', 'message_id'):
                continue
            
            update_expression += f"#{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value
        
        # Remove trailing comma and space
        update_expression = update_expression[:-2]
        
        # Build expression attribute names
        expression_attribute_names = {f"#{key}": key for key in updates if key not in ('session_id', 'message_id')}
        
        try:
            response = self.table.update_item(
                Key={
                    'session_id': session_id,
                    'message_id': message_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW"
            )
            logger.info(f"Updated message {message_id} in session {session_id}")
            return response.get('Attributes')
        except ClientError as e:
            logger.error(f"Error updating message {message_id} in session {session_id}: {e}")
            raise
    
    def delete_message(self, session_id, message_id):
        """
        Delete a message from a transcript.
        
        Args:
            session_id (str): ID of the interview session.
            message_id (str): ID of the message to delete.
        
        Returns:
            bool: True if the message was deleted, False otherwise.
        """
        try:
            self.table.delete_item(Key={
                'session_id': session_id,
                'message_id': message_id
            })
            logger.info(f"Deleted message {message_id} from session {session_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting message {message_id} from session {session_id}: {e}")
            raise
    
    def get_transcript(self, session_id):
        """
        Get all messages for an interview session, ordered by timestamp.
        
        Args:
            session_id (str): ID of the interview session.
        
        Returns:
            list: List of messages in the transcript.
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('session_id').eq(session_id)
            }
            messages = get_paginated_results(self.table, query_kwargs=query_kwargs)
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            
            return messages
        except ClientError as e:
            logger.error(f"Error getting transcript for session {session_id}: {e}")
            raise
    
    def add_analysis_to_message(self, session_id, message_id, analysis):
        """
        Add or update analysis data for a message.
        
        Args:
            session_id (str): ID of the interview session.
            message_id (str): ID of the message to update.
            analysis (dict): Analysis data for the message.
        
        Returns:
            dict: The updated message data.
        """
        return self.update_message(session_id, message_id, {'analysis': analysis})
    
    def add_tag_to_message(self, session_id, message_id, tag):
        """
        Add a tag to a message.
        
        Args:
            session_id (str): ID of the interview session.
            message_id (str): ID of the message to update.
            tag (str): Tag to add to the message.
        
        Returns:
            dict: The updated message data.
        """
        # Get the current message
        message = self.get_message(session_id, message_id)
        if not message:
            raise ValueError(f"Message {message_id} not found in session {session_id}")
        
        # Get existing tags or create a new set
        tags = set(message.get('tags', []))
        
        # Add the new tag
        tags.add(tag)
        
        # Update the message
        return self.update_message(session_id, message_id, {'tags': list(tags)})
    
    def delete_transcript(self, session_id):
        """
        Delete all messages for an interview session.
        
        Args:
            session_id (str): ID of the interview session.
        
        Returns:
            bool: True if the transcript was deleted, False otherwise.
        """
        try:
            # Get all messages for the session
            transcript = self.get_transcript(session_id)
            
            # Batch delete all messages
            with self.table.batch_writer() as batch:
                for message in transcript:
                    batch.delete_item(Key={
                        'session_id': session_id,
                        'message_id': message['message_id']
                    })
            
            logger.info(f"Deleted transcript for session {session_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting transcript for session {session_id}: {e}")
            raise
    
    def get_messages_by_role(self, session_id, role):
        """
        Get all messages with a specific role for an interview session.
        
        Args:
            session_id (str): ID of the interview session.
            role (str): Role to filter by ('assistant', 'user', 'system').
        
        Returns:
            list: List of messages with the specified role.
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('session_id').eq(session_id),
                'FilterExpression': Key('role').eq(role)
            }
            return get_paginated_results(self.table, query_kwargs=query_kwargs)
        except ClientError as e:
            logger.error(f"Error getting messages by role for session {session_id}: {e}")
            raise 