// TranscriptExplorer.tsx
import React, { useState } from 'react';
import TranscriptTab from './TranscriptTab';
import AnalysisTab from './AnalysisTab';
import SemanticSearchTab from './shared/SemanticSearchTab';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface TranscriptExplorerProps {
  messages: Message[];
  analysis?: { content: string };
}

const TranscriptExplorer: React.FC<TranscriptExplorerProps> = ({ messages, analysis }) => {
  const [activeTab, setActiveTab] = useState<'transcript' | 'analysis' | 'semantic'>('transcript');

  return (
    <div>
      <div className="flex gap-4 border-b mb-4">
        <button
          className={`pb-2 px-4 font-semibold ${activeTab === 'transcript' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
          onClick={() => setActiveTab('transcript')}
        >
          Transcript
        </button>
        <button
          className={`pb-2 px-4 font-semibold ${activeTab === 'analysis' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
          onClick={() => setActiveTab('analysis')}
        >
          Analysis
        </button>
        <button
          className={`pb-2 px-4 font-semibold ${activeTab === 'semantic' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
          onClick={() => setActiveTab('semantic')}
        >
          Semantic Search
        </button>
      </div>
      {activeTab === 'transcript' && <TranscriptTab messages={messages} />}
      {activeTab === 'analysis' && <AnalysisTab analysis={analysis} />}
      {activeTab === 'semantic' && <SemanticSearchTab messages={messages} analysis={analysis} />}
    </div>
  );
};

export default TranscriptExplorer;