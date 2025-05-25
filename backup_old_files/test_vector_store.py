import unittest
from vector_store import InterviewVectorStore
import os
from datetime import datetime, now

class TestInterviewVectorStore(unittest.TestCase):
    def setUp(self):
        # Use a test API key - replace with your test key
        self.store = InterviewVectorStore(openai_api_key="your-test-key")
        
    def test_extract_user_responses(self):
        # Test normal case
        transcript = """
Daria: How do you use the system?
You: I use it daily for booking
Daria: Can you elaborate?
You: Yes, I book flights and hotels
"""
        responses = self.store._extract_user_responses(transcript)
        self.assertEqual(responses.split('\n'), ['I use it daily for booking', 'Yes, I book flights and hotels'])
        
        # Test with no user responses
        transcript = """
Daria: How do you use the system?
Daria: Can you elaborate?
"""
        responses = self.store._extract_user_responses(transcript)
        self.assertEqual(responses, '')
        
        # Test with malformed format
        transcript = """
How do you use the system?
I use it daily for booking
"""
        responses = self.store._extract_user_responses(transcript)
        self.assertEqual(responses, '')

    def test_clean_content(self):
        content = """
Daria: How often do you use it?
You: Daily usage
Previous response: noted
Role: interviewer
I use it for work
"""
        cleaned = self.store._clean_content(content)
        self.assertIn('Daily usage', cleaned)
        self.assertIn('I use it for work', cleaned)
        self.assertNotIn('Daria:', cleaned)
        self.assertNotIn('Previous response:', cleaned)
        self.assertNotIn('Role:', cleaned)

    def test_search_functionality(self):
        # Create test interviews
        interviews = [{
            'id': '1',
            'project_name': 'Test Project',
            'interview_type': 'Test Type',
            'date': now().isoformat(),
            'transcript': """
Daria: How do you use the system?
You: I use it for booking flights
Daria: Can you elaborate?
You: Specifically international flights
""",
            'analysis': 'User primarily books international flights'
        }]
        
        # Add to vector store
        self.store.add_interviews(interviews)
        
        # Test searching for user response content
        results = self.store.semantic_search('booking flights')
        self.assertTrue(len(results) > 0)
        self.assertIn('booking flights', results[0]['transcript_preview'].lower())
        
        # Test searching for analysis content
        results = self.store.semantic_search('primarily books international')
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['match_source'], 'analysis')
        
        # Test searching for Daria's content (should not match)
        results = self.store.semantic_search('How do you use the system')
        self.assertTrue(all('daria:' not in r['transcript_preview'].lower() for r in results))

    def test_similar_interviews(self):
        # Create test interviews
        interviews = [
            {
                'id': '1',
                'project_name': 'Test Project 1',
                'interview_type': 'Test Type',
                'date': now().isoformat(),
                'transcript': """
Daria: How do you use the system?
You: I use it for booking flights
""",
                'analysis': 'User books flights'
            },
            {
                'id': '2',
                'project_name': 'Test Project 2',
                'interview_type': 'Test Type',
                'date': now().isoformat(),
                'transcript': """
Daria: What's your experience?
You: I also book flights regularly
""",
                'analysis': 'Regular flight booker'
            }
        ]
        
        # Add to vector store
        self.store.add_interviews(interviews)
        
        # Test finding similar interviews
        results = self.store.find_similar_interviews('1')
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['metadata']['id'], '2')
        
    def tearDown(self):
        # Clean up test vector store
        if os.path.exists('vector_store'):
            import shutil
            shutil.rmtree('vector_store')

if __name__ == '__main__':
    unittest.main() 