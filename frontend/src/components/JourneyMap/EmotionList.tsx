import React from 'react';

interface Emotion {
  stage?: string;
  emotion: string;
  description?: string;
  intensity?: number;
  [key: string]: any;
}

interface EmotionListProps {
  emotions: Emotion[];
}

export const EmotionList: React.FC<EmotionListProps> = ({ emotions }) => {
  if (!emotions || emotions.length === 0) return null;

  // Map emotion names to emoji
  const getEmotionEmoji = (emotion: string) => {
    const emotionMap: Record<string, string> = {
      happy: '😊',
      excited: '🤩',
      satisfied: '😌',
      neutral: '😐',
      confused: '😕',
      anxious: '😰',
      frustrated: '😤',
      disappointed: '😞',
      angry: '😠',
      sad: '😢'
    };
    
    // Check for emotion word in the string
    const key = Object.keys(emotionMap).find(key => 
      emotion.toLowerCase().includes(key)
    );
    
    return key ? emotionMap[key] : '😐'; // Default to neutral
  };

  return (
    <div className="bg-purple-50 p-6 rounded-lg shadow-md border border-purple-100">
      <h2 className="text-xl font-bold text-purple-800 mb-4">User Emotions</h2>
      
      <div className="space-y-4">
        {emotions.map((emotion, index) => (
          <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
            {emotion.stage && (
              <div className="text-xs font-semibold text-purple-600 mb-1">
                {emotion.stage}
              </div>
            )}
            
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2" role="img" aria-label={emotion.emotion}>
                {getEmotionEmoji(emotion.emotion)}
              </span>
              <span className="font-medium text-purple-700">{emotion.emotion}</span>
              
              {emotion.intensity !== undefined && (
                <div className="ml-auto flex items-center">
                  <div className="w-20 h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-purple-600" 
                      style={{ width: `${Math.min(100, emotion.intensity * 20)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 ml-1">{emotion.intensity}/5</span>
                </div>
              )}
            </div>
            
            {emotion.description && (
              <p className="text-gray-700 text-sm">{emotion.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}; 