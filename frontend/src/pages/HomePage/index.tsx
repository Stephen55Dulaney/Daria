import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Typography, Divider, message } from 'antd';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  RobotOutlined,
  FileSearchOutlined,
  TeamOutlined,
  ProjectOutlined,
  CommentOutlined,
  BarChartOutlined,
  NodeIndexOutlined,
  QuestionCircleOutlined,
  SoundOutlined,
  LoadingOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import './HomePage.css';

const { Title, Paragraph, Text } = Typography;

// Global flag to prevent audio API calls until user explicitly enables
let isAudioGloballyEnabled = false;

// Define ElevenLabs voice IDs - these match the IDs in app.py
const ELEVENLABS_VOICES = {
  rachel: "EXAVITQu4vr4xnSDxMaL",  // Professional Female
  antoni: "ErXwobaYiN019PkySvjV",  // Male
  elli: "MF3mGyEYCl7XYWbV9V6O",   // Female
  domi: "AZnzlk1XvdvUeBnXmlld",   // Female
  sam: "yoZ06aMxZJJ28mfd3POQ",    // Male
  josh: "TxGEqnHWrfWFTfGW9XjX"    // Male
};

// Map voice index to voice ID
const voiceMapping = [
  ELEVENLABS_VOICES.rachel, // Interview Assistant
  ELEVENLABS_VOICES.antoni, // Archive & Search
  ELEVENLABS_VOICES.elli,   // Interview Guides
  ELEVENLABS_VOICES.domi,   // Persona Generator
  ELEVENLABS_VOICES.sam,    // Journey Generator
  ELEVENLABS_VOICES.josh    // Transcript Analysis
];

interface FeatureCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  link: string;
  buttonText?: string;
  color?: string;
  isHighlighted?: boolean;
  speechText?: string;
  voiceIndex?: number;
  audioEnabled: boolean;
}

const FeatureCard = ({ 
  title, 
  description, 
  icon, 
  link, 
  buttonText = "Explore", 
  color = "#1890ff",
  isHighlighted = false,
  speechText,
  voiceIndex = 0,
  audioEnabled
}: FeatureCardProps) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioRef, setAudioRef] = useState<HTMLAudioElement | null>(null);

  // Only create audio element when audio is enabled
  useEffect(() => {
    // Don't initialize audio until explicitly enabled
    if (!audioEnabled) {
      return;
    }
    
    const audio = new Audio();
    audio.onended = () => setIsSpeaking(false);
    audio.onerror = () => {
      setIsSpeaking(false);
      message.error("Error playing audio");
    };
    setAudioRef(audio);
    
    // Cleanup on unmount
    return () => {
      if (audio) {
        audio.pause();
        audio.src = "";
      }
      // Hide any message notifications when component unmounts
      message.destroy();
    };
  }, [audioEnabled]); // Only recreate when audioEnabled changes

  const speakText = async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    // Don't even try if audio is disabled
    if (!audioEnabled) return;
    
    if (!speechText || isSpeaking || !audioRef) return;
    
    try {
      setIsSpeaking(true);
      
      // Stop any current playback
      audioRef.pause();
      
      // Only proceed with API call if globally enabled
      if (!isAudioGloballyEnabled) {
        throw new Error("Audio not globally enabled yet");
      }
      
      // Get voice ID based on index
      const voiceId = voiceMapping[voiceIndex % voiceMapping.length];
      
      // Request audio from backend
      const response = await axios.post('http://localhost:5003/text_to_speech', {
        text: speechText,
        voice_id: voiceId
      }, {
        responseType: 'blob'
      });
      
      // Create object URL from blob
      const audioUrl = URL.createObjectURL(response.data);
      
      // Set source and play
      audioRef.src = audioUrl;
      await audioRef.play();
      
      // Cleanup URL when done
      audioRef.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
    } catch (error) {
      console.error("Error playing audio:", error);
      
      // Show error message
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.status === 404) {
          message.warning("Using browser speech instead (ElevenLabs not available)");
        } else {
          message.warning(`Server error: ${error.response.status}. Using browser speech instead.`);
        }
      } else {
        message.warning("Using browser speech synthesis instead.");
      }
      
      // Fallback to browser speech synthesis
      if ('speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel(); // Stop any current speech
          
          const utterance = new SpeechSynthesisUtterance(speechText);
          
          // Get available voices
          const voices = window.speechSynthesis.getVoices();
          if (voices.length > 0) {
            // Use a different voice based on voiceIndex
            const voiceToUse = voices[voiceIndex % voices.length];
            utterance.voice = voiceToUse;
          }
          
          // Adjust pitch and rate slightly for variety
          utterance.pitch = 1.0 + (voiceIndex * 0.1 % 0.4);
          utterance.rate = 0.9 + (voiceIndex * 0.05 % 0.3);
          
          // Events to track speaking status
          utterance.onstart = () => setIsSpeaking(true);
          utterance.onend = () => setIsSpeaking(false);
          utterance.onerror = () => {
            setIsSpeaking(false);
            message.error("Speech synthesis failed.");
          };
          
          window.speechSynthesis.speak(utterance);
        } catch (synthError) {
          console.error("Speech synthesis error:", synthError);
          setIsSpeaking(false);
          message.error("Could not play audio. All speech methods failed.");
        }
      } else {
        setIsSpeaking(false);
        message.error("Speech synthesis not supported in this browser.");
      }
    }
  };

  const handleCardClick = () => {
    // Only try to speak if audio is enabled
    if (audioEnabled && speechText && !isSpeaking && audioRef) {
      speakText({ stopPropagation: () => {} } as React.MouseEvent);
    }
  };

  return (
    <Card 
      className={`feature-card ${isHighlighted ? 'highlighted' : ''}`}
      style={{ height: '100%' }}
      hoverable
      onClick={handleCardClick}
    >
      <div className="feature-icon" style={{ backgroundColor: color }}>
        {icon}
      </div>
      <div className="feature-header">
        <Title level={4}>{title}</Title>
        {speechText && audioEnabled && (
          <Button 
            type="text" 
            icon={isSpeaking ? <LoadingOutlined /> : <SoundOutlined />} 
            className={`audio-button ${isSpeaking ? 'speaking' : ''}`}
            onClick={speakText}
            loading={isSpeaking}
          />
        )}
      </div>
      <Paragraph className="feature-description">
        {description}
      </Paragraph>
      <div className="feature-action">
        <Link to={link} onClick={(e) => e.stopPropagation()}>
          <Button type="primary" style={{ backgroundColor: color, borderColor: color }}>
            {buttonText}
          </Button>
        </Link>
      </div>
    </Card>
  );
};

const HomePage = () => {
  // Add state to track if audio is enabled
  const [audioEnabled, setAudioEnabled] = useState(false);

  // Initialize audio globally when enabled
  useEffect(() => {
    if (audioEnabled) {
      isAudioGloballyEnabled = true;
      
      // Pre-load voices if using browser speech synthesis
      if ('speechSynthesis' in window) {
        // This helps initialize the voices array in some browsers
        window.speechSynthesis.getVoices();
      }
    }
  }, [audioEnabled]);

  // Text content for speech
  const speechTexts = {
    interviewAssistant: "With DARIA, teams can either conduct interviews live inside the tool, using AI-driven prompts to guide the conversation, or upload existing transcripts from prior research. It's flexible by design — meeting teams wherever they are in the project lifecycle.",
    interviewArchive: "All interviews and transcripts are automatically saved in the Interview Archive, neatly organized by project. And with DARIA's Advanced Search, you can quickly find insights across interviews using either semantic understanding or exact keyword matching, so knowledge is never lost or siloed.",
    interviewGuides: "Need to jumpstart a new research effort? DARIA, Deloitte's Advanced Research and Interview Assistant, uses Askia — our GPT-powered Interview Question Advisor — to help you do exactly that. Just provide your business goals and user context, and DARIA leverages Askia to generate a smart, structured interview guide. Each script is tailored, context-aware, and aligned with proven UX research practices — helping your team ask the right questions, uncover real insights, and avoid common pitfalls from day one.ate tailored interview guides for you. You simply input your business goals and user profiles, and Askia creates a strategic set of questions — helping teams conduct smarter, more targeted interviews from day one.",
    personaGenerator: "Once qualitative interviews are complete, Daria, seamlessly activates Thesia — our AI-powered Persona Architect. Thesia analyzes the raw transcript data to generate research-backed draft personas that highlight users goals, pain points, behaviors, and unmet needs. This enables Deloitte teams to move from insights to impact faster — with first-iteration personas grounded directly in real user voices, ready for expert refinement and strategic application",
    journeyGenerator: "Similarly, DARIA works hand-in-hand with Odysia, our journey mapping AI. While DARIA gathers and synthesizes insights from interviews, Odysia transforms that raw input into structured, draft user journeys. Together, they highlight emotional peaks, friction points, and opportunity zones — enabling Deloitte teams to visualize and improve user experiences earlier, faster, and with greater empathy.",
    transcriptAnalysis: "DARIA simplifies transcript analysis—just upload your interviews, and our AI goes to work. All insights are automatically extracted, thematically categorized, and made searchable across every project. But DARIA does not stop at surface-level summaries. With Skeptica, you get rigorous assumption testing. It identifies hidden biases, logical gaps, and contradictory statements—ensuring your insights are not just interesting, but evidence-based and decision-ready. Eurekia, on the other hand, helps you spot emerging patterns, unmet needs, and whitespace opportunities across your data. It generates strategic hypotheses grounded in what people actually say—not what you hope they mean. Together, Skeptica and Eurekia turn raw transcripts into validated insight—so your team moves forward with clarity, confidence, and rigor."
  };

  return (
    <div className="home-container">
      <div className="hero-section">
        <div className="hero-content">
          <Title>Daria Interview Tool</Title>
          <Title level={3}>Deloitte Advanced Research and Interview Assistant</Title>
          <Paragraph className="hero-description">
            Hi everyone — today I'm excited to introduce you to DARIA, our Gen AI-powered tool designed to make research, persona creation, and journey mapping faster, smarter, and more consistent across Deloitte projects.
          </Paragraph>
          
          {!audioEnabled && (
            <Button 
              type="primary" 
              size="large" 
              icon={<PlayCircleOutlined />} 
              className="start-presentation-btn"
              onClick={() => {
                setAudioEnabled(true);
                isAudioGloballyEnabled = true;
              }}
            >
              Start Presentation with Audio
            </Button>
          )}
          
          {audioEnabled && (
            <Paragraph className="audio-enabled-msg">
              <SoundOutlined /> Audio narration is now enabled. Click on any feature card to hear more about it.
            </Paragraph>
          )}
        </div>
      </div>

      <div className="features-section">
        <Title level={2} className="section-title">Key Features</Title>
        
        <Row gutter={[24, 24]}>
          {/* DARIA Interview Feature - Highlighted */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="DARIA Interview Assistant"
              description="With DARIA, teams can either conduct interviews live inside the tool, using AI-driven prompts, or upload existing transcripts from prior research. It's flexible by design — meeting teams wherever they are in the project lifecycle."
              icon={<RobotOutlined />}
              link="/interview/jarvis_test"
              buttonText="Try DARIA"
              color="#7B61FF"
              isHighlighted={true}
              speechText={speechTexts.interviewAssistant}
              voiceIndex={0}
              audioEnabled={audioEnabled}
            />
          </Col>
          
          {/* Archive & Search */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="Interview Archive & Smart Search"
              description="All interviews are automatically saved in the Interview Archive, neatly organized by project. With DARIA's Advanced Search, you can quickly find insights using semantic understanding or exact keyword matching."
              icon={<FileSearchOutlined />}
              link="/advanced-search"
              buttonText="Explore Archive"
              color="#eb2f96"
              isHighlighted={true}
              speechText={speechTexts.interviewArchive}
              voiceIndex={1}
              audioEnabled={audioEnabled}
            />
          </Col>
          
          {/* Create Interview Guides */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="Create Interview Guides"
              description="If you're starting a new engagement, DARIA can generate tailored interview guides. Input your business goals and user profiles, and DARIA creates strategic questions for smarter, more targeted interviews."
              icon={<QuestionCircleOutlined />}
              link="/new-interview"
              color="#FF6B3D"
              speechText={speechTexts.interviewGuides}
              voiceIndex={2}
              audioEnabled={audioEnabled}
            />
          </Col>
          
          {/* Persona Generator */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="Persona Generator"
              description="Once interviews are captured, DARIA instantly generates draft personas. By analyzing real interview data, it creates first-iteration user personas — capturing goals, frustrations, behaviors, and key needs."
              icon={<TeamOutlined />}
              link="/persona-generator"
              color="#1890ff"
              speechText={speechTexts.personaGenerator}
              voiceIndex={3}
              audioEnabled={audioEnabled}
            />
          </Col>
          
          {/* Journey Map Feature */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="Journey Generator"
              description="DARIA's Journey Generator takes interview transcripts and produces draft customer journeys. It highlights emotional highs and lows, pain points, and opportunity areas — mapping the user experience efficiently."
              icon={<NodeIndexOutlined />}
              link="/journey-map"
              color="#52c41a"
              speechText={speechTexts.journeyGenerator}
              voiceIndex={4}
              audioEnabled={audioEnabled}
            />
          </Col>

          {/* Transcript Analysis */}
          <Col xs={24} sm={24} md={12} lg={8}>
            <FeatureCard
              title="Transcript Analysis"
              description="Upload and analyze interview transcripts. DARIA extracts themes, insights, and sentiment patterns, making it easy to derive valuable findings across your research projects."
              icon={<CommentOutlined />}
              link="/interview-archive"
              color="#fa8c16"
              speechText={speechTexts.transcriptAnalysis}
              voiceIndex={5}
              audioEnabled={audioEnabled}
            />
          </Col>
        </Row>
      </div>

      <Divider />
      
      <div className="benefits-section">
        <Title level={2} className="section-title">Why Choose Daria?</Title>
        
        <Row gutter={[32, 32]}>
          <Col xs={24} md={8}>
            <div className="benefit-item">
              <div className="benefit-icon">
                <BarChartOutlined />
              </div>
              <div className="benefit-content">
                <Title level={4}>Deeper Insights</Title>
                <Text>Extract meaningful patterns and connections across multiple interviews that might otherwise be missed.</Text>
              </div>
            </div>
          </Col>
          
          <Col xs={24} md={8}>
            <div className="benefit-item">
              <div className="benefit-icon">
                <ProjectOutlined />
              </div>
              <div className="benefit-content">
                <Title level={4}>Time Efficiency</Title>
                <Text>Reduce analysis time by 70% with AI-powered tools that automate tedious aspects of research synthesis.</Text>
              </div>
            </div>
          </Col>
          
          <Col xs={24} md={8}>
            <div className="benefit-item">
              <div className="benefit-icon">
                <TeamOutlined />
              </div>
              <div className="benefit-content">
                <Title level={4}>Enhanced Collaboration</Title>
                <Text>Share insights, personas, and journey maps with stakeholders through easy-to-understand visualizations.</Text>
              </div>
            </div>
          </Col>
        </Row>
      </div>
      
      <div className="cta-section">
        <Card className="cta-card">
          <Title level={3}>Ready to transform your research workflow?</Title>
          <Paragraph>DARIA helps teams capture insights faster, build strategic deliverables earlier, and stay deeply connected to real user needs — all through the power of Gen AI.</Paragraph>
          <Link to="/new-interview">
            <Button type="primary" size="large">Start a New Interview</Button>
          </Link>
        </Card>
      </div>
    </div>
  );
};

export default HomePage; 