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
    <div onClick={handleInteraction}>
      <Title level={2} className="text-center mb-6">Research Discovery Plan</Title>
      <Paragraph className="text-center mb-8 text-lg">
        Answer these questions to help us create your personalized research plan and discovery game.
      </Paragraph>

      {/* Round 1 */}
      {currentRound === 1 && (
        <div className="survey-question">
          <Title level={3} className="flex items-center mb-6">
            What is your primary research objective?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(1, e.target.value)} value={responses[1]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="user_needs" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Understand User Needs</div>
                  <div className="survey-option-description">I need to discover what my users really want and need</div>
                </div>
              </Radio>
              <Radio value="market_validation" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Market Validation</div>
                  <div className="survey-option-description">I need to validate if there's a market for my product/idea</div>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 2 */}
      {currentRound === 2 && (
        <div className="survey-question">
          <Title level={3} className="flex items-center mb-6">
            What type of research data do you prefer?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(2, e.target.value)} value={responses[2]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="qualitative" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Qualitative Insights</div>
                  <div className="survey-option-description">I prefer rich, detailed insights from fewer people</div>
                </div>
              </Radio>
              <Radio value="quantitative" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Quantitative Data</div>
                  <div className="survey-option-description">I prefer numerical data from larger sample sizes</div>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 3 */}
      {currentRound === 3 && (
        <div className="survey-question">
          <Title level={3} className="flex items-center mb-6">
            What is your project timeline?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(3, e.target.value)} value={responses[3]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="urgent" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Urgent (1-2 weeks)</div>
                  <div className="survey-option-description">I need results very quickly</div>
                </div>
              </Radio>
              <Radio value="standard" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Standard (1-2 months)</div>
                  <div className="survey-option-description">I have a reasonable timeframe</div>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 4 */}
      {currentRound === 4 && (
        <div className="survey-question">
          <Title level={3} className="flex items-center mb-6">
            What's your budget range?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(4, e.target.value)} value={responses[4]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="limited" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Limited Budget</div>
                  <div className="survey-option-description">I need cost-effective research methods</div>
                </div>
              </Radio>
              <Radio value="flexible" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Flexible Budget</div>
                  <div className="survey-option-description">I can invest in comprehensive research</div>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {/* Round 5 */}
      {currentRound === 5 && (
        <div className="survey-question">
          <Title level={3} className="flex items-center mb-6">
            What research methods are you familiar with?
            {speaking && <SoundOutlined spin className="ml-2 text-blue-500" />}
          </Title>
          <Radio.Group onChange={(e) => handleOptionSelect(5, e.target.value)} value={responses[5]} className="w-full">
            <Space direction="vertical" className="w-full">
              <Radio value="interviews" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">User Interviews</div>
                  <div className="survey-option-description">I'm comfortable with one-on-one interviews</div>
                </div>
              </Radio>
              <Radio value="surveys" className="survey-option">
                <div className="survey-option-content">
                  <div className="survey-option-title">Surveys & Analytics</div>
                  <div className="survey-option-description">I prefer data collection at scale</div>
                </div>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      )}

      {error && <div className="text-red-500 mb-6 font-medium">{error}</div>}

      <div className="flex justify-between mt-8">
        {currentRound > 1 && (
          <Button 
            size="large" 
            onClick={() => setCurrentRound(prev => prev - 1)}
            disabled={loading}
            className="px-6 h-10"
          >
            Previous
          </Button>
        )}
        <div className="flex-1"></div>
        {currentRound < 5 ? (
          <Button 
            type="primary" 
            size="large" 
            onClick={handleNext}
            disabled={!responses[currentRound] || loading}
            className="px-8 h-10 font-medium"
          >
            Next
          </Button>
        ) : (
          <Button 
            type="primary" 
            size="large" 
            onClick={handleSubmit}
            disabled={!responses[currentRound] || loading}
            className="px-8 h-10 font-medium"
          >
            {loading ? <Spin size="small" /> : 'Reveal My Research Plan'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default ResearchSurvey; 