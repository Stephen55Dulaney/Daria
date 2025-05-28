import React from 'react';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface AnnotationsTabProps {
  messages: Message[];
  sessionId: string;
}

const AnnotationsTab: React.FC<AnnotationsTabProps> = (props) => {
  return (
    <div className="text-gray-500 italic">Annotation features coming soon...</div>
  );
};

export default AnnotationsTab; 