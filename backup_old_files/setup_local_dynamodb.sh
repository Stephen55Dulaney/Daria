#!/bin/bash
set -e

echo "Setting up DynamoDB Local for development..."

# Create directories
mkdir -p dynamodb_local
cd dynamodb_local

# Download DynamoDB Local if not already downloaded
if [ ! -f "DynamoDBLocal.jar" ]; then
    echo "Downloading DynamoDB Local..."
    curl -O https://d1ni2b6xgvw0s0.cloudfront.net/v2.2.0/dynamodb_local_latest.tar.gz
    tar xzf dynamodb_local_latest.tar.gz
    rm dynamodb_local_latest.tar.gz
    echo "DynamoDB Local downloaded successfully!"
else
    echo "DynamoDB Local already downloaded."
fi

# Check if DynamoDB Local is already running
if nc -z localhost 8000 2>/dev/null; then
    echo "DynamoDB Local is already running on port 8000."
else
    echo "Starting DynamoDB Local on port 8000..."
    # Run DynamoDB Local in the background
    java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb &
    echo "DynamoDB Local started! PID: $!"
    
    # Give it a moment to start up
    sleep 2
    
    # Check if it's running
    if nc -z localhost 8000 2>/dev/null; then
        echo "DynamoDB Local is now running on port 8000."
    else
        echo "Failed to start DynamoDB Local. Please check Java installation and try again."
        exit 1
    fi
fi

cd ..

# Make the setup_dynamodb.py script executable
chmod +x setup_dynamodb.py

echo "Running DynamoDB setup script..."
python setup_dynamodb.py

echo "Setup complete! DynamoDB Local is running and tables are created."
echo "To create test data, run: python create_test_data.py" 