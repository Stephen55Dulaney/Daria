// AnnotationsTab.tsx
import React from 'react';
import type { Tag } from './shared/TagList';
import TagEditor from './shared/TagEditor';
import InsightAnnotation from './shared/InsightAnnotation';

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

interface Annotation {
  id: string;
  messageId: string;
  content: string;
  user: {
    name: string;
  };
  timestamp: string;
}

const AnnotationsTab: React.FC<AnnotationsTabProps> = ({ messages, sessionId }) => {
  const [selectedMessage, setSelectedMessage] = React.useState<string | null>(null);
  const [tags, setTags] = React.useState<{ [msgId: string]: Tag[] }>({});
  const [annotations, setAnnotations] = React.useState<{ [msgId: string]: Annotation[] }>({});
  const [newComment, setNewComment] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);

  // Load existing tags and annotations when component mounts
  React.useEffect(() => {
    const loadAnnotations = async () => {
      try {
        setIsLoading(true);
        // Only fetch participant messages to reduce payload size
        const participantMessages = messages.filter(msg => msg.role === 'participant' || msg.role === 'user');
        const response = await fetch(`/api/session/${sessionId}/annotations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            messageIds: participantMessages.map(msg => msg.id)
          })
        });
        const data = await response.json();
        if (data.tags) setTags(data.tags);
        if (data.annotations) setAnnotations(data.annotations);
      } catch (error) {
        console.error('Failed to load annotations:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadAnnotations();
  }, [sessionId, messages]);

  const handleAddTag = async (msgId: string, tag: Tag) => {
    try {
      const response = await fetch(`/api/session/${sessionId}/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messageId: msgId, tag })
      });
      
      if (response.ok) {
        setTags(prev => ({
          ...prev,
          [msgId]: [...(prev[msgId] || []), tag]
        }));
      }
    } catch (error) {
      console.error('Failed to add tag:', error);
    }
  };

  const handleRemoveTag = async (msgId: string, tagId: string) => {
    try {
      const response = await fetch(`/api/session/${sessionId}/tags/${tagId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setTags(prev => ({
          ...prev,
          [msgId]: (prev[msgId] || []).filter(t => t.id !== tagId)
        }));
      }
    } catch (error) {
      console.error('Failed to remove tag:', error);
    }
  };

  const handleAddAnnotation = async (msgId: string, content: string) => {
    try {
      const response = await fetch(`/api/session/${sessionId}/annotations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messageId: msgId, content })
      });
      
      if (response.ok) {
        const newAnnotation: Annotation = {
          id: Date.now().toString(),
          messageId: msgId,
          content,
          user: { name: 'Current User' }, // TODO: Get from auth context
          timestamp: new Date().toISOString()
        };
        setAnnotations(prev => ({
          ...prev,
          [msgId]: [...(prev[msgId] || []), newAnnotation]
        }));
        setNewComment('');
      }
    } catch (error) {
      console.error('Failed to add annotation:', error);
    }
  };

  // Filter to show only participant messages
  const participantMessages = messages.filter(msg => msg.role === 'participant' || msg.role === 'user');

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      {/* Left column - Transcript */}
      <div className="w-1/2">
        <h2 className="text-xl font-semibold mb-4">Participant Responses</h2>
        <div className="space-y-4">
          {participantMessages.map((message) => (
            <div 
              key={message.id} 
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedMessage === message.id ? 'border-purple-500 bg-purple-50' : 'hover:border-gray-300'
              }`}
              onClick={() => setSelectedMessage(message.id)}
            >
              <div className="flex items-center mb-2">
                <span className="font-semibold">Participant</span>
                <span className="ml-2 text-sm text-gray-500">
                  {new Date(message.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-gray-700">{message.content}</p>
              {tags[message.id]?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {tags[message.id].map(tag => (
                    <span 
                      key={tag.id}
                      className="px-2 py-1 text-sm rounded-full"
                      style={{ backgroundColor: tag.color || '#e5e7eb' }}
                    >
                      {tag.label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right column - Annotation tools */}
      <div className="w-1/2">
        <h2 className="text-xl font-semibold mb-4">Annotations</h2>
        {selectedMessage ? (
          <div className="space-y-6">
            <div className="p-4 border rounded-lg bg-gray-50">
              <h3 className="font-medium mb-2">Add Tags</h3>
              <TagEditor
                value={(tags[selectedMessage] || []).map(t => t.label)}
                onAdd={(tag) => handleAddTag(selectedMessage, { id: Date.now().toString(), label: tag })}
                onRemove={(tag) => handleRemoveTag(selectedMessage, tag)}
              />
            </div>

            <div className="p-4 border rounded-lg bg-gray-50">
              <h3 className="font-medium mb-2">Add Comment</h3>
              <InsightAnnotation
                value={newComment}
                onSave={(text) => handleAddAnnotation(selectedMessage, text)}
              />
            </div>

            {annotations[selectedMessage]?.length > 0 && (
              <div className="space-y-4">
                <h3 className="font-medium">Comments</h3>
                {annotations[selectedMessage].map(annotation => (
                  <div key={annotation.id} className="p-3 border rounded-lg bg-white">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium">{annotation.user.name}</span>
                      <span className="text-sm text-gray-500">
                        {new Date(annotation.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-gray-700">{annotation.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            Select a participant response to add annotations
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnotationsTab;