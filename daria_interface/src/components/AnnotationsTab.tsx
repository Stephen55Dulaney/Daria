// TranscriptTab.tsx
import React from 'react';
import TagList from './shared/TagList';
import type { Tag } from './shared/TagList';
import TagEditor from './shared/TagEditor';
import InsightAnnotation from './shared/InsightAnnotation';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface TranscriptTabProps {
  messages: Message[];
}

// Dummy data for demonstration
const dummyTags: Tag[] = [
  { id: '1', label: 'Theme: Onboarding', color: '#c7d2fe', user: { name: 'Alice' } },
  { id: '2', label: 'Emotion: Frustration', color: '#fee2e2', user: { name: 'Bob' } }
];

const TranscriptTab: React.FC<TranscriptTabProps> = ({ messages }) => {
  // In real use, fetch tags/insights per message from API
  const [tags, setTags] = React.useState<{ [msgId: string]: Tag[] }>({});
  const [insights, setInsights] = React.useState<{ [msgId: string]: string }>({});

  const handleAddTag = (msgId: string, tag: string) => {
    // Call API, then update state
    setTags(prev => ({
      ...prev,
      [msgId]: [...(prev[msgId] || []), { id: Date.now().toString(), label: tag }]
    }));
  };

  const handleRemoveTag = (msgId: string, tag: string) => {
    setTags(prev => ({
      ...prev,
      [msgId]: (prev[msgId] || []).filter(t => t.label !== tag)
    }));
  };

  const handleSaveInsight = (msgId: string, text: string) => {
    setInsights(prev => ({ ...prev, [msgId]: text }));
  };

  return (
    <div>
      {messages.length === 0 ? (
        <div className="text-gray-500 italic">No messages available.</div>
      ) : (
        <ul>
          {messages.map((msg) => (
            <li key={msg.id} className="mb-4 border-b pb-2">
              <strong>{msg.role}:</strong> {msg.content}
              <span className="text-xs text-gray-400 ml-2">{msg.timestamp}</span>
              {/* Tag List */}
              <TagList tags={tags[msg.id] || dummyTags} showAvatars />
              {/* Tag Editor */}
              <TagEditor
                value={(tags[msg.id] || []).map(t => t.label)}
                onAdd={tag => handleAddTag(msg.id, tag)}
                onRemove={tag => handleRemoveTag(msg.id, tag)}
                suggestions={['Onboarding', 'Frustration', 'Delight']}
              />
              {/* Insight Annotation */}
              <InsightAnnotation
                value={insights[msg.id] || ''}
                onSave={text => handleSaveInsight(msg.id, text)}
                user={{ name: 'Current User' }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TranscriptTab;