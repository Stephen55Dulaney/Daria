#!/bin/bash
# Simple script to test the Memory Companion API

echo "Testing Memory Companion API..."
curl -s http://localhost:5030/api/memory_companion/test | python3 -m json.tool

if [ $? -eq 0 ]; then
    echo -e "\n✅ Memory Companion API is working!"
else
    echo -e "\n❌ Memory Companion API is not responding. Please check server logs."
fi
