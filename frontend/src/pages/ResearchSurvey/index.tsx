import React, { useState, useEffect } from 'react';
import { Button, Typography, Radio, Space, Spin, notification } from 'antd';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { SoundOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

// Helper function to call the text-to-speech API
const speak = async (text: string) => {
  try {
    // Available voices from ElevenLabs
    const AVAILABLE_VOICES = {
      "rachel": "EXAVITQu4vr4xnSDxMaL",
      "antoni": "ErXwobaYiN019PkySvjV",
      "elli": "MF3mGyEYCl7XYWbV9V6O",
      "domi": "AZnzlk1XvdvUeBnXmlld"
    };
    
    // Randomly select a voice
    const voices = Object.entries(AVAILABLE_VOICES);
    const randomVoice = voices[Math.floor(Math.random() * voices.length)];
    const voiceName = randomVoice[0];
    const voiceId = randomVoice[1];
    
    console.log(`Using voice: ${voiceName}`);
    
    const response = await axios.post('http://localhost:5003/text_to_speech', {
      text: text,
      voice_id: voiceId  // Pass the selected voice ID to the API
    }, {
      responseType: 'blob'
    });
    
    const audioBlob = response.data;
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    
    return new Promise((resolve) => {
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        resolve(null);
      };
      
      // Try to play the audio, and if it fails due to user interaction requirement,
      // show a message to the user
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          console.log('Audio playback failed:', error);
          // You could show a message to the user here if needed
        });
      }
    });
  } catch (error) {
    console.error('Error with text-to-speech:', error);
  }
};

const ResearchSurvey: React.FC = () => {
  const navigate = useNavigate();
  const [currentRound, setCurrentRound] = useState(1);
  const [loading, setLoading] = useState(false);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Get the question text for the current round
  const getQuestionText = (round: number): string => {
    switch(round) {
      case 1:
        return "What is your primary research objective?";
      case 2:
        return "What type of research data do you prefer?";
      case 3:
        return "What is your project timeline?";
      case 4:
        return "What's your budget range?";
      case 5:
        return "What research methods are you familiar with?";
      default:
        return "";
    }
  };

  // Read the question aloud when the round changes
  useEffect(() => {
    const questionText = getQuestionText(currentRound);
    if (questionText && hasInteracted) {
      setSpeaking(true);
      speak(questionText).finally(() => {
        setSpeaking(false);
      });
    }
  }, [currentRound, hasInteracted]);

  // Add a click handler to the container to detect user interaction
  const handleInteraction = () => {
    if (!hasInteracted) {
      setHasInteracted(true);
    }
  };

  const handleOptionSelect = (round: number, value: string) => {
    setResponses(prev => ({ ...prev, [round]: value }));
  };

  const handleNext = () => {
    if (!responses[currentRound]) {
      setError('Please select an option to continue.');
      return;
    }
    setError(null);
    setCurrentRound(prev => prev + 1);
  };

  const handleSubmit = async () => {
    if (!responses[currentRound]) {
      setError('Please select an option to continue.');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await axios.post('/api/submit-research-survey', responses);
      if (result.data.success) {
        navigate('/survey-results');
      } else {
        setError(result.data.message || 'Error submitting survey.');
      }
    } catch (err) {
      console.error('Survey submission error:', err);
      setError('An error occurred while submitting your responses.');
      notification.error({
        message: 'Survey Error',
        description: 'There was a problem submitting your survey. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg" onClick={handleInteraction}>
      <Title level={2} className="text-center mb-8">Research Discovery Plan</Title>
      <Paragraph className="text-center mb-8">
        Answer these questions to help us create your personalized research plan and discovery game.
      </Paragraph>

      {/* Round 1 */}
      {currentRound === 1 && (
        <div className="mb-8">
          <Title level={3} className="flex items-center">
            What is your primary research objective?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(1, e.target.value)} value={responses[1]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="user_needs" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Understand User Needs</Title>
                  <Paragraph>I need to discover what my users really want and need</Paragraph>
                </div>
              </Radio>
              <Radio value="market_validation" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Market Validation</Title>
                  <Paragraph>I need to validate if there's a market for my product/idea</Paragraph>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 2 */}
      {currentRound === 2 && (
        <div className="mb-8">
          <Title level={3} className="flex items-center">
            What type of research data do you prefer?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(2, e.target.value)} value={responses[2]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="qualitative" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Qualitative Insights</Title>
                  <Paragraph>I prefer rich, detailed insights from fewer people</Paragraph>
                </div>
              </Radio>
              <Radio value="quantitative" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Quantitative Data</Title>
                  <Paragraph>I prefer numerical data from larger sample sizes</Paragraph>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 3 */}
      {currentRound === 3 && (
        <div className="mb-8">
          <Title level={3} className="flex items-center">
            What is your project timeline?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(3, e.target.value)} value={responses[3]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="urgent" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Urgent (1-2 weeks)</Title>
                  <Paragraph>I need results very quickly</Paragraph>
                </div>
              </Radio>
              <Radio value="standard" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Standard (1-2 months)</Title>
                  <Paragraph>I have a reasonable timeframe</Paragraph>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 4 */}
      {currentRound === 4 && (
        <div className="mb-8">
          <Title level={3} className="flex items-center">
            What's your budget range?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(4, e.target.value)} value={responses[4]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="limited" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Limited Budget</Title>
                  <Paragraph>I need cost-effective research methods</Paragraph>
                </div>
              </Radio>
              <Radio value="flexible" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Flexible Budget</Title>
                  <Paragraph>I can invest in comprehensive research</Paragraph>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 5 */}
      {currentRound === 5 && (
        <div className="mb-8">
          <Title level={3} className="flex items-center">
            What research methods are you familiar with?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(5, e.target.value)} value={responses[5]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="interviews" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>User Interviews</Title>
                  <Paragraph>I'm comfortable with one-on-one interviews</Paragraph>
                </div>
              </Radio>
              <Radio value="surveys" className="p-4 border rounded mb-2 w-full">
                <div className="ml-2">
                  <Title level={5}>Surveys & Analytics</Title>
                  <Paragraph>I prefer data collection at scale</Paragraph>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {error && <div className="text-red-500 mb-4">{error}</div>}

      <div className="flex justify-between mt-8">
        {currentRound > 1 && (
          <Button 
            size="large" 
            onClick={() => setCurrentRound(prev => prev - 1)}
            disabled={loading}
          >
            Previous
          </Button>
        )}
        {currentRound < 5 ? (
          <Button 
            type="primary" 
            size="large" 
            onClick={handleNext}
            disabled={!responses[currentRound] || loading}
          >
            Next
          </Button>
        ) : (
          <Button 
            type="primary" 
            size="large" 
            onClick={handleSubmit}
            disabled={!responses[currentRound] || loading}
          >
            {loading ? <Spin size="small" /> : 'Reveal My Research Plan'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default ResearchSurvey; 