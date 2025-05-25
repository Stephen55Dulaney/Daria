import React, { useState, useEffect, useRef } from 'react';
import { Typography, Input, Button, Card, Divider, notification } from 'antd';
import { SendOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

interface GameHistoryEntry {
  type: 'system' | 'player';
  text: string;
}

interface ResearchMethod {
  name: string;
  description: string;
  key_researchers: string[];
  common_techniques: string[];
}

interface GameState {
  history: GameHistoryEntry[];
  discovered_methods: any[];
  current_location: string;
  research_methods: ResearchMethod[];
}

const ResearchAdventure: React.FC = () => {
  const navigate = useNavigate();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const historyRef = useRef<HTMLDivElement>(null);

  // Initial load of game state
  useEffect(() => {
    const fetchGameState = async () => {
      try {
        const response = await axios.get('/api/game-state');
        if (response.data.success) {
          setGameState(response.data.game_state);
        } else {
          notification.error({
            message: 'Game Error',
            description: 'Could not load the research adventure. Please try again.',
          });
          navigate('/survey-results');
        }
      } catch (error) {
        console.error('Error loading game state:', error);
        notification.error({
          message: 'Game Error',
          description: 'Could not load the research adventure. Please try again.',
        });
      } finally {
        setInitialLoading(false);
      }
    };

    fetchGameState();
  }, [navigate]);

  // Scroll to bottom when history updates
  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [gameState?.history]);

  const handleCommandSubmit = async () => {
    if (!command.trim() || loading || !gameState) return;

    // Add player command to local history
    const updatedHistory: GameHistoryEntry[] = [
      ...gameState.history,
      { type: 'player', text: command }
    ];
    
    setGameState({
      ...gameState,
      history: updatedHistory
    });
    
    setLoading(true);
    
    try {
      const response = await axios.post('/api/game-action', { command });
      if (response.data.success) {
        // Add system response to history
        const newHistory: GameHistoryEntry[] = [
          ...updatedHistory,
          { type: 'system', text: response.data.message }
        ];
        
        setGameState({
          ...response.data.game_state,
          history: newHistory
        });
      } else {
        notification.error({
          message: 'Game Error',
          description: response.data.message || 'An error occurred.',
        });
      }
    } catch (error) {
      console.error('Error sending command:', error);
      notification.error({
        message: 'Game Error',
        description: 'Could not process your command. Please try again.',
      });
    } finally {
      setLoading(false);
      setCommand('');
    }
  };

  const handleNewGame = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/game-action', { command: 'new game' });
      if (response.data.success) {
        setGameState({
          ...response.data.game_state,
          history: [{ type: 'system', text: response.data.message }] as GameHistoryEntry[]
        });
      } else {
        notification.error({
          message: 'Game Error',
          description: response.data.message || 'An error occurred.',
        });
      }
    } catch (error) {
      console.error('Error resetting game:', error);
      notification.error({
        message: 'Game Error',
        description: 'Could not reset the game. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <Text>Loading your research adventure...</Text>
        </div>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="text-center p-8">
        <Title level={3} className="text-red-500">Could not load the game</Title>
        <Button type="primary" onClick={() => navigate('/survey-results')}>
          Return to Survey Results
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <Title level={2} className="text-center mb-6">Research Discovery Adventure</Title>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="h-full">
          <div className="mb-4 flex justify-between items-center">
            <Title level={4}>Research Methods Explorer</Title>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleNewGame}
              disabled={loading}
            >
              New Game
            </Button>
          </div>
          
          <Card title="Available Research Methods" className="mb-4">
            <div className="grid grid-cols-1 gap-4">
              {gameState.research_methods.map((method, index) => (
                <div key={index} className="p-3 border rounded hover:bg-gray-50">
                  <Text strong>{method.name}</Text>
                  <Text type="secondary" className="block text-sm">{method.description.substring(0, 100)}...</Text>
                </div>
              ))}
            </div>
          </Card>
          
          <Card title="Discovered Insights">
            {gameState.discovered_methods.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {gameState.discovered_methods.map((method, index) => (
                  <div key={index} className="p-3 border rounded bg-blue-50">
                    <Text strong>{method.name}</Text>
                    <Text className="block">{method.description}</Text>
                    <Divider className="my-2" />
                    <Text type="secondary">Key researchers: {method.researchers?.join(', ')}</Text>
                  </div>
                ))}
              </div>
            ) : (
              <Text type="secondary">You haven't discovered any research insights yet. Explore to learn more!</Text>
            )}
          </Card>
        </Card>
        
        <Card>
          <Title level={4}>Research Adventure</Title>
          <div 
            ref={historyRef}
            className="h-80 overflow-y-auto p-4 bg-gray-50 rounded mb-4 border"
          >
            {gameState.history.map((entry, index) => (
              <div 
                key={index} 
                className={`mb-3 p-2 rounded ${
                  entry.type === 'system' 
                    ? 'bg-blue-50 border-l-4 border-blue-500' 
                    : 'bg-gray-100 border-l-4 border-gray-500'
                }`}
              >
                <Text>{entry.text}</Text>
              </div>
            ))}
          </div>
          
          <div className="flex">
            <Input
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onPressEnter={handleCommandSubmit}
              placeholder="Enter your command (e.g., 'explore user interviews')"
              disabled={loading}
              className="flex-grow"
            />
            <Button 
              type="primary" 
              icon={<SendOutlined />} 
              onClick={handleCommandSubmit}
              disabled={!command.trim() || loading}
              className="ml-2"
            >
              Send
            </Button>
          </div>
          
          <div className="mt-4">
            <Text type="secondary">
              Try commands like: "look around", "explore [method name]", "learn about [technique]",
              "move to [method]", or "help" for more guidance.
            </Text>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ResearchAdventure; 