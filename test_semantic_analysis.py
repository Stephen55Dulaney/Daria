import unittest
from semantic_analysis import SemanticAnalyzer
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSemanticAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up SemanticAnalyzer instance once for all tests."""
        cls.analyzer = SemanticAnalyzer()

    def test_analyze_emotions_happy(self):
        """Test emotion analysis with happy text."""
        text = "I'm really excited and happy about this amazing project! It's going great!"
        result = self.analyzer.analyze_emotions(text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('label', result)
        self.assertIn('score', result)
        self.assertIsInstance(result['score'], float)
        self.assertTrue(0 <= result['score'] <= 1)
        logger.info(f"Happy text emotion result: {result}")

    def test_analyze_emotions_neutral(self):
        """Test emotion analysis with neutral text."""
        text = "The meeting is scheduled for tomorrow at 2pm."
        result = self.analyzer.analyze_emotions(text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('label', result)
        self.assertIn('score', result)
        logger.info(f"Neutral text emotion result: {result}")

    def test_analyze_emotions_empty(self):
        """Test emotion analysis with empty text."""
        text = ""
        result = self.analyzer.analyze_emotions(text)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['label'], 'neutral')
        self.assertEqual(result['score'], 0.0)
        logger.info(f"Empty text emotion result: {result}")

    def test_analyze_chunk_complete(self):
        """Test complete chunk analysis including emotions and themes."""
        text = """[Interviewer] How do you feel about the new design system?
        [Participant] I'm really impressed with how intuitive it is. The color scheme is perfect 
        for accessibility, and the components are so well documented. It's definitely going to 
        speed up our development process."""
        
        result = self.analyzer.analyze_chunk(text)
        
        # Verify structure
        self.assertIsInstance(result, dict)
        self.assertIn('text', result)
        self.assertIn('emotion', result)
        self.assertIn('emotion_intensity', result)
        self.assertIn('themes', result)
        self.assertIn('insight_tags', result)
        self.assertIn('sentiment_score', result)
        
        # Verify types
        self.assertIsInstance(result['themes'], list)
        self.assertIsInstance(result['insight_tags'], list)
        self.assertIsInstance(result['emotion_intensity'], int)
        self.assertTrue(1 <= result['emotion_intensity'] <= 5)
        
        logger.info(f"Complete chunk analysis result: {result}")

    def test_analyze_chunk_error_handling(self):
        """Test chunk analysis error handling with problematic text."""
        text = None  # This should trigger error handling
        result = self.analyzer.analyze_chunk(text)
        
        # Verify we get default values on error
        self.assertIsInstance(result, dict)
        self.assertEqual(result['emotion'], 'neutral')
        self.assertEqual(result['emotion_intensity'], 3)
        self.assertIsInstance(result['themes'], list)
        self.assertIsInstance(result['insight_tags'], list)
        
        logger.info(f"Error handling test result: {result}")

    def test_emotion_classification_various(self):
        """Test emotion analysis with various emotional content."""
        test_cases = [
            {
                "text": "I'm really frustrated with this interface. It's so confusing and hard to use!",
                "expected_emotion": "anger"
            },
            {
                "text": "I love how easy this is to use. The design is beautiful!",
                "expected_emotion": "joy"
            },
            {
                "text": "I'm worried that we won't meet the deadline. There's so much left to do.",
                "expected_emotion": "fear"
            },
            {
                "text": "The old system was much better. This is disappointing.",
                "expected_emotion": "sadness"
            },
            {
                "text": "Wow! I didn't expect it to work so well! This is amazing!",
                "expected_emotion": "surprise"
            },
            {
                "text": "[Participant] So basically what I do is I open the application, then I click on the dashboard, and then I can see all my tasks.",
                "expected_emotion": "neutral"
            },
            {
                "text": "The button is in the top right corner. When you click it, a menu appears.",
                "expected_emotion": "neutral"
            }
        ]

        for i, case in enumerate(test_cases):
            result = self.analyzer.analyze_emotions(case["text"])
            logger.info(f"\nTest case {i+1}:")
            logger.info(f"Text: {case['text']}")
            logger.info(f"Expected emotion: {case['expected_emotion']}")
            logger.info(f"Got result: {result}")
            logger.info(f"Score: {result['score']:.2f}")
            
            self.assertIsInstance(result, dict)
            self.assertIn('label', result)
            self.assertIn('score', result)
            self.assertIsInstance(result['score'], float)
            self.assertTrue(0 <= result['score'] <= 1)

    def test_analyze_chunk_with_strong_emotion(self):
        """Test chunk analysis with text containing strong emotional content."""
        text = """[Interviewer] What frustrates you most about the current system?
        [Participant] Oh my god, it's absolutely terrible! The system crashes constantly, 
        I lose all my work, and the interface is so confusing. I hate using it every single day. 
        It's the most frustrating thing I've ever had to work with!"""
        
        result = self.analyzer.analyze_chunk(text)
        logger.info(f"\nStrong emotion chunk analysis:")
        logger.info(f"Text: {text}")
        logger.info(f"Emotion: {result['emotion']}")
        logger.info(f"Score: {result['sentiment_score']:.2f}")
        logger.info(f"Emotion intensity: {result['emotion_intensity']}")
        
        self.assertIsInstance(result, dict)
        self.assertNotEqual(result['emotion'], 'neutral', "Strong emotional content was classified as neutral")
        self.assertTrue(result['sentiment_score'] > 0.6, "Strong emotional content had low confidence score")

    def test_analyze_chunk_with_mixed_emotions(self):
        """Test chunk analysis with text containing mixed emotions."""
        text = """[Interviewer] How do you feel about the transition to the new system?
        [Participant] Well, I'm excited about the new features, they look really promising.
        But I'm also nervous about learning everything from scratch. The training timeline
        seems a bit rushed, which worries me. Still, I think once we get used to it,
        it will be much better than what we had before."""
        
        result = self.analyzer.analyze_chunk(text)
        logger.info(f"\nMixed emotions chunk analysis:")
        logger.info(f"Text: {text}")
        logger.info(f"Emotion: {result['emotion']}")
        logger.info(f"Score: {result['sentiment_score']:.2f}")
        logger.info(f"Emotion intensity: {result['emotion_intensity']}")
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['sentiment_score'] > 0.5, "Mixed emotional content had very low confidence score")

if __name__ == '__main__':
    unittest.main() 