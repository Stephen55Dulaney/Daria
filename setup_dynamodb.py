#!/usr/bin/env python3
import boto3
import time
import logging
import json
import os
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DynamoDB client - using local endpoint for development
def get_dynamodb_client(use_local=True):
    if use_local:
        # For local development with DynamoDB Local
        return boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-west-2',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
    else:
        # For AWS cloud deployment
        return boto3.client('dynamodb')

def create_table(client, table_name, key_schema, attribute_definitions, provisioned_throughput=None, 
                 global_secondary_indexes=None, local_secondary_indexes=None):
    """Create a DynamoDB table with the specified parameters."""
    if provisioned_throughput is None:
        provisioned_throughput = {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    
    create_params = {
        'TableName': table_name,
        'KeySchema': key_schema,
        'AttributeDefinitions': attribute_definitions,
        'BillingMode': 'PROVISIONED',
        'ProvisionedThroughput': provisioned_throughput
    }
    
    if global_secondary_indexes:
        create_params['GlobalSecondaryIndexes'] = global_secondary_indexes
    
    if local_secondary_indexes:
        create_params['LocalSecondaryIndexes'] = local_secondary_indexes
    
    try:
        table = client.create_table(**create_params)
        logger.info(f"Created table {table_name}. Status: {table['TableDescription']['TableStatus']}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.warning(f"Table {table_name} already exists")
            return False
        else:
            logger.error(f"Error creating table {table_name}: {e}")
            raise

def wait_for_table_active(client, table_name, max_retries=10, delay=5):
    """Wait for the table to be in the ACTIVE state."""
    retries = 0
    while retries < max_retries:
        try:
            response = client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            if status == 'ACTIVE':
                logger.info(f"Table {table_name} is now ACTIVE")
                return True
            logger.info(f"Table {table_name} status is {status}, waiting...")
        except ClientError as e:
            logger.error(f"Error checking table status: {e}")
            return False
        
        retries += 1
        time.sleep(delay)
    
    logger.warning(f"Timeout waiting for table {table_name} to become ACTIVE")
    return False

def setup_core_tables(client):
    """Setup the core tables for the DARIA system."""
    
    # Table 1: InterviewSessions
    create_table(
        client,
        'InterviewSessions',
        key_schema=[
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
            {'AttributeName': 'sprint_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'SprintIndex',
                'KeySchema': [
                    {'AttributeName': 'sprint_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Table 2: Transcripts
    create_table(
        client,
        'Transcripts',
        key_schema=[
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'message_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'message_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'}
        ],
        local_secondary_indexes=[
            {
                'IndexName': 'TimestampIndex',
                'KeySchema': [
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ]
    )
    
    # Wait for tables to be active
    for table_name in ['InterviewSessions', 'Transcripts']:
        wait_for_table_active(client, table_name)
    
    logger.info("Core tables setup complete")

def setup_analysis_tables(client):
    """Setup the analysis tables for the DARIA system."""
    
    # Table 3: Sprints
    create_table(
        client,
        'Sprints',
        key_schema=[
            {'AttributeName': 'sprint_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'sprint_id', 'AttributeType': 'S'},
            {'AttributeName': 'start_date', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'StartDateIndex',
                'KeySchema': [
                    {'AttributeName': 'start_date', 'KeyType': 'HASH'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Table 4: Opportunities
    create_table(
        client,
        'Opportunities',
        key_schema=[
            {'AttributeName': 'opportunity_id', 'KeyType': 'HASH'},
            {'AttributeName': 'sprint_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'opportunity_id', 'AttributeType': 'S'},
            {'AttributeName': 'sprint_id', 'AttributeType': 'S'},
            {'AttributeName': 'impacted_persona', 'AttributeType': 'S'},
            {'AttributeName': 'priority_score', 'AttributeType': 'N'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'PersonaIndex',
                'KeySchema': [
                    {'AttributeName': 'impacted_persona', 'KeyType': 'HASH'},
                    {'AttributeName': 'priority_score', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'SprintPriorityIndex',
                'KeySchema': [
                    {'AttributeName': 'sprint_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'priority_score', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Table 5: Personas
    create_table(
        client,
        'Personas',
        key_schema=[
            {'AttributeName': 'persona_id', 'KeyType': 'HASH'},
            {'AttributeName': 'sprint_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'persona_id', 'AttributeType': 'S'},
            {'AttributeName': 'sprint_id', 'AttributeType': 'S'}
        ]
    )
    
    # Wait for tables to be active
    for table_name in ['Sprints', 'Opportunities', 'Personas']:
        wait_for_table_active(client, table_name)
    
    logger.info("Analysis tables setup complete")

def setup_output_tables(client):
    """Setup the output tables for the DARIA system."""
    
    # Table 6: AgileArtifacts
    create_table(
        client,
        'AgileArtifacts',
        key_schema=[
            {'AttributeName': 'artifact_id', 'KeyType': 'HASH'},
            {'AttributeName': 'opportunity_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'artifact_id', 'AttributeType': 'S'},
            {'AttributeName': 'opportunity_id', 'AttributeType': 'S'},
            {'AttributeName': 'type', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'TypeIndex',
                'KeySchema': [
                    {'AttributeName': 'type', 'KeyType': 'HASH'},
                    {'AttributeName': 'opportunity_id', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Table 7: CursorPrompts
    create_table(
        client,
        'CursorPrompts',
        key_schema=[
            {'AttributeName': 'prompt_id', 'KeyType': 'HASH'},
            {'AttributeName': 'opportunity_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'prompt_id', 'AttributeType': 'S'},
            {'AttributeName': 'opportunity_id', 'AttributeType': 'S'},
            {'AttributeName': 'generated_at', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'GeneratedIndex',
                'KeySchema': [
                    {'AttributeName': 'opportunity_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'generated_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Wait for tables to be active
    for table_name in ['AgileArtifacts', 'CursorPrompts']:
        wait_for_table_active(client, table_name)
    
    logger.info("Output tables setup complete")

def setup_management_tables(client):
    """Setup the management tables for the DARIA system."""
    
    # Table 8: Prototypes
    create_table(
        client,
        'Prototypes',
        key_schema=[
            {'AttributeName': 'prototype_id', 'KeyType': 'HASH'},
            {'AttributeName': 'prompt_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'prototype_id', 'AttributeType': 'S'},
            {'AttributeName': 'prompt_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'StatusIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Table 9: JourneyMaps
    create_table(
        client,
        'JourneyMaps',
        key_schema=[
            {'AttributeName': 'journey_id', 'KeyType': 'HASH'},
            {'AttributeName': 'persona_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'journey_id', 'AttributeType': 'S'},
            {'AttributeName': 'persona_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'CreatedAtIndex',
                'KeySchema': [
                    {'AttributeName': 'persona_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    # Wait for tables to be active
    for table_name in ['Prototypes', 'JourneyMaps']:
        wait_for_table_active(client, table_name)
    
    logger.info("Management tables setup complete")

def main():
    """Main function to set up all DynamoDB tables."""
    logger.info("Starting DynamoDB table setup...")
    
    # Get DynamoDB client - use local for development
    use_local = True  # Set to False for AWS cloud deployment
    client = get_dynamodb_client(use_local)
    
    # Create tables in priority order
    setup_core_tables(client)
    setup_analysis_tables(client)
    setup_output_tables(client)
    setup_management_tables(client)
    
    logger.info("DynamoDB table setup complete!")

if __name__ == "__main__":
    main() 