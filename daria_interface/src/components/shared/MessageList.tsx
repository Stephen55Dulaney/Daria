import React from 'react';

export interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface MessageListProps {
  messages?: Message[];
  className?: string;
}

const MessageList: React.FC<MessageListProps> = ({ messages = [], className = '' }) => {
  if (!messages || messages.length === 0) {
    return (
      <div className={`p-4 text-gray-500 italic ${className}`}>
        No messages available
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {messages.map((message) => (
        <div
          key={message.id}
          className={`p-4 rounded-lg ${
            message.role === 'assistant'
              ? 'bg-blue-50 ml-4'
              : message.role === 'user'
              ? 'bg-gray-50 mr-4'
              : 'bg-yellow-50'
          }`}
        >
          <div className="flex justify-between items-start mb-2">
            <span className="font-medium">
              {message.role === 'assistant' ? 'Moderator' :
                message.role === 'user' ? 'Participant' : 'System'}
            </span>
            <span className="text-sm text-gray-500">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      ))}
    </div>
  );
};

export default MessageList; 