// AnalysisTab.tsx
import React from 'react';

interface AnalysisTabProps {
  analysis?: { content: string };
}

const AnalysisTab: React.FC<AnalysisTabProps> = ({ analysis }) => (
  <div>
    {analysis?.content
      ? <pre className="whitespace-pre-wrap">{analysis.content}</pre>
      : <div className="text-gray-500 italic">No analysis available.</div>
    }
  </div>
);

export default AnalysisTab;