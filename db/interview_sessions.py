"""
Module for interacting with the InterviewSessions table in DynamoDB.
"""

import uuid
import json
import logging
import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from .database import get_dynamodb_resource, get_paginated_results

# Configure logging
logger = logging.getLogger(__name__)

# Table name
TABLE_NAME = 'InterviewSessions'


class InterviewSessionsDB:
    """Class for interacting with the InterviewSessions table in DynamoDB."""
    
    def __init__(self, use_local=None):
        """
        Initialize the InterviewSessionsDB object.
        
        Args:
            use_local (bool, optional): Whether to use local DynamoDB. Defaults to None.
        """
        self.dynamodb = get_dynamodb_resource(use_local)
        self.table = self.dynamodb.Table(TABLE_NAME)
    
    def create_session(self, title, character, sprint_id=None, metadata=None):
        """
        Create a new interview session.
        
        Args:
            title (str): Title of the interview session.
            character (str): Character used for the interview.
            sprint_id (str, optional): ID of the sprint associated with this session. Defaults to None.
            metadata (dict, optional): Additional metadata for the session. Defaults to None.
        
        Returns:
            dict: The created interview session data.
        """
        session_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        item = {
            'session_id': session_id,
            'created_at': created_at,
            'title': title,
            'character': character,
            'status': 'active'
        }
        
        if sprint_id:
            item['sprint_id'] = sprint_id
        
        if metadata:
            # Convert any decimal values to strings for JSON serialization
            for key, value in metadata.items():
                if isinstance(value, Decimal):
                    metadata[key] = str(value)
            item['metadata'] = metadata
        
        # Set expiration date (30 days from now)
        expires_at = int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
        item['expires_at'] = expires_at
        
        try:
            self.table.put_item(Item=item)
            logger.info(f"Created interview session {session_id}")
            return item
        except ClientError as e:
            logger.error(f"Error creating interview session: {e}")
            raise
    
    def get_session(self, session_id):
        """
        Get an interview session by session_id.
        
        Args:
            session_id (str): ID of the session to get.
        
        Returns:
            dict: The interview session data, or None if not found.
        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting interview session {session_id}: {e}")
            raise
    
    def update_session(self, session_id, updates):
        """
        Update an interview session.
        
        Args:
            session_id (str): ID of the session to update.
            updates (dict): Dictionary of attributes to update.
        
        Returns:
            dict: The updated interview session data.
        """
        # Get the created_at value which is part of the primary key
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        created_at = session['created_at']
        
        # Build update expression and attribute values
        update_expression = "SET "
        expression_attribute_values = {}
        
        for key, value in updates.items():
            # Skip primary key attributes
            if key in ('session_id', 'created_at'):
                continue
            
            update_expression += f"#{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value
        
        # Remove trailing comma and space
        update_expression = update_expression[:-2]
        
        # Build expression attribute names
        expression_attribute_names = {f"#{key}": key for key in updates if key not in ('session_id', 'created_at')}
        
        # Set the updated_at timestamp
        update_expression += ", #updated_at = :updated_at"
        expression_attribute_values[":updated_at"] = datetime.datetime.now().isoformat()
        expression_attribute_names["#updated_at"] = "updated_at"
        
        try:
            response = self.table.update_item(
                Key={
                    'session_id': session_id,
                    'created_at': created_at
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW"
            )
            logger.info(f"Updated interview session {session_id}")
            return response.get('Attributes')
        except ClientError as e:
            logger.error(f"Error updating interview session {session_id}: {e}")
            raise
    
    def delete_session(self, session_id):
        """
        Delete an interview session.
        
        Args:
            session_id (str): ID of the session to delete.
        
        Returns:
            bool: True if the session was deleted, False otherwise.
        """
        # Get the created_at value which is part of the primary key
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for deletion")
            return False
        
        created_at = session['created_at']
        
        try:
            self.table.delete_item(Key={
                'session_id': session_id,
                'created_at': created_at
            })
            logger.info(f"Deleted interview session {session_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting interview session {session_id}: {e}")
            raise
    
    def list_sessions(self, limit=None):
        """
        List all interview sessions.
        
        Args:
            limit (int, optional): Maximum number of sessions to return. Defaults to None.
        
        Returns:
            list: List of interview sessions.
        """
        scan_kwargs = {}
        if limit:
            scan_kwargs['Limit'] = limit
        
        try:
            return get_paginated_results(self.table, scan_kwargs=scan_kwargs)
        except ClientError as e:
            logger.error(f"Error listing interview sessions: {e}")
            raise
    
    def list_sessions_by_sprint(self, sprint_id):
        """
        List all interview sessions for a specific sprint.
        
        Args:
            sprint_id (str): ID of the sprint.
        
        Returns:
            list: List of interview sessions for the sprint.
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('sprint_id').eq(sprint_id)
            }
            return get_paginated_results(self.table, index_name='SprintIndex', query_kwargs=query_kwargs)
        except ClientError as e:
            logger.error(f"Error listing interview sessions for sprint {sprint_id}: {e}")
            raise
    
    def update_session_status(self, session_id, status):
        """
        Update the status of an interview session.
        
        Args:
            session_id (str): ID of the session to update.
            status (str): New status for the session.
        
        Returns:
            dict: The updated interview session data.
        """
        return self.update_session(session_id, {'status': status})
    
    def add_tag_to_session(self, session_id, tag):
        """
        Add a tag to an interview session.
        
        Args:
            session_id (str): ID of the session to update.
            tag (str): Tag to add to the session.
        
        Returns:
            dict: The updated interview session data.
        """
        # Get the current session
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get existing tags or create a new set
        tags = set(session.get('tags', []))
        
        # Add the new tag
        tags.add(tag)
        
        # Update the session
        return self.update_session(session_id, {'tags': list(tags)})
    
    def remove_tag_from_session(self, session_id, tag):
        """
        Remove a tag from an interview session.
        
        Args:
            session_id (str): ID of the session to update.
            tag (str): Tag to remove from the session.
        
        Returns:
            dict: The updated interview session data.
        """
        # Get the current session
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get existing tags
        tags = set(session.get('tags', []))
        
        # Remove the tag if it exists
        if tag in tags:
            tags.remove(tag)
        
        # Update the session
        return self.update_session(session_id, {'tags': list(tags)})
    
    def get_sessions_by_character(self, character):
        """
        Get all interview sessions for a specific character.
        
        Args:
            character (str): Character to filter by.
        
        Returns:
            list: List of interview sessions for the character.
        """
        try:
            scan_kwargs = {
                'FilterExpression': Attr('character').eq(character)
            }
            return get_paginated_results(self.table, scan_kwargs=scan_kwargs)
        except ClientError as e:
            logger.error(f"Error getting interview sessions for character {character}: {e}")
            raise 