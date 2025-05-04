"""
Main database module with shared functionality.
"""

import boto3
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables for configuration
USE_LOCAL_DB = os.environ.get('USE_LOCAL_DB', 'true').lower() == 'true'
DYNAMODB_ENDPOINT = os.environ.get('DYNAMODB_ENDPOINT', 'http://localhost:8000')
AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')


def get_dynamodb_resource(use_local=None):
    """
    Get a boto3 DynamoDB resource.
    
    Args:
        use_local (bool, optional): Whether to use local DynamoDB. Defaults to None (use environment variable).
    
    Returns:
        boto3.resource.DynamoDB: DynamoDB resource
    """
    if use_local is None:
        use_local = USE_LOCAL_DB
    
    if use_local:
        # For local development with DynamoDB Local
        return boto3.resource(
            'dynamodb',
            endpoint_url=DYNAMODB_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
    else:
        # For AWS cloud deployment
        return boto3.resource('dynamodb', region_name=AWS_REGION)


def get_dynamodb_client(use_local=None):
    """
    Get a boto3 DynamoDB client.
    
    Args:
        use_local (bool, optional): Whether to use local DynamoDB. Defaults to None (use environment variable).
    
    Returns:
        boto3.client.DynamoDB: DynamoDB client
    """
    if use_local is None:
        use_local = USE_LOCAL_DB
    
    if use_local:
        # For local development with DynamoDB Local
        return boto3.client(
            'dynamodb',
            endpoint_url=DYNAMODB_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
    else:
        # For AWS cloud deployment
        return boto3.client('dynamodb', region_name=AWS_REGION)


def check_table_exists(table_name, client=None):
    """
    Check if a DynamoDB table exists.
    
    Args:
        table_name (str): Name of the table to check.
        client (boto3.client.DynamoDB, optional): DynamoDB client. Defaults to None.
    
    Returns:
        bool: True if the table exists, False otherwise.
    """
    if client is None:
        client = get_dynamodb_client()
    
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def get_paginated_results(table, index_name=None, query_kwargs=None, scan_kwargs=None):
    """
    Get paginated results from a DynamoDB table.
    
    Args:
        table (boto3.resource.Table): DynamoDB table resource
        index_name (str, optional): Name of the index to query. Defaults to None.
        query_kwargs (dict, optional): Query parameters. Defaults to None.
        scan_kwargs (dict, optional): Scan parameters. Defaults to None.
    
    Returns:
        list: List of items from the table.
    """
    operation_kwargs = {}
    if index_name:
        operation_kwargs['IndexName'] = index_name
    
    if query_kwargs:
        operation = table.query
        operation_kwargs.update(query_kwargs)
    else:
        operation = table.scan
        if scan_kwargs:
            operation_kwargs.update(scan_kwargs)
    
    results = []
    last_evaluated_key = None
    
    while True:
        if last_evaluated_key:
            operation_kwargs['ExclusiveStartKey'] = last_evaluated_key
        
        response = operation(**operation_kwargs)
        results.extend(response.get('Items', []))
        
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    return results 