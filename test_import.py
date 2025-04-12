import sys
import os

print("Python Path:")
for path in sys.path:
    print(path)

print("\nCurrent Directory:", os.getcwd())

try:
    from src.vector_store import InterviewVectorStore
    print("\nSuccessfully imported InterviewVectorStore")
except ImportError as e:
    print("\nFailed to import:", str(e)) 