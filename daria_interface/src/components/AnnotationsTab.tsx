// AnnotationsTab.tsx
import React from 'react';
import TagEditor from './shared/TagEditor';
import InsightAnnotation from './shared/InsightAnnotation';
import AnnotationDetails from './shared/AnnotationDetails';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
  tags?: string[]; // AI-assigned tags
  semantic?: {
    themes?: string[];
    emotions?: string[];
    intent?: string;
    task_success?: string;
    goal_satisfaction?: string;
    persona?: string;
    frustration_markers?: string[];
    ux_heuristic_violations?: string[];
    pain_points?: { issue: string; severity_score: number }[];
    quotes?: { text: string }[];
    affinity_hint?: string;
    interaction_modality?: string;
  };
  // Allow for possible typo in data
  [key: string]: any;
}

interface AnnotationsTabProps {
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

interface TagColor {
  id: string;
  name: string;
  color: string;
  category: string;
}

// Tag component for colored badges
const Tag = ({ label, color }: { label: string, color: string }) => (
  <span style={{
    background: color,
    color: '#fff',
    borderRadius: '8px',
    padding: '2px 8px',
    marginRight: '4px',
    fontSize: '0.85em'
  }}>{label}</span>
);

const colorMap = {
  theme: '#a78bfa', // purple
  emotion: '#60a5fa', // blue
  intent: '#34d399', // green
  task_success: '#fbbf24', // yellow
  goal_satisfaction: '#f472b6', // pink
  persona: '#f87171', // red
  heuristic: '#f59e42', // orange
  pain: '#ef4444', // red
};

const prettyLabels = {
  themes: 'Theme',
  emotions: 'Emotion',
  affinity_hint: 'Affinity Hint',
  // ...etc
};

const Message = ({ msg }: { msg: any }) => {
  const s = msg.semantic || {};
  return (
    <div className="mb-4 p-3 bg-white rounded shadow">
      <div className="font-semibold">{msg.role}</div>
      <div>{msg.content}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {Object.entries(s).map(([key, value]) => {
          if (Array.isArray(value) && value.length > 0) {
            return value.map((v, i) => (
              <span key={`${key}-${i}`} className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 border border-gray-200">
                {typeof v === 'string' ? v : JSON.stringify(v)}
              </span>
            ));
          }
          if (typeof value === 'string' && value.trim() && value !== 'not applicable') {
            return (
              <span key={key} className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 border border-gray-200">
                {value}
              </span>
            );
          }
          return null;
        })}
      </div>
      {/* Optionally, show quotes */}
      {s.quotes && s.quotes.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Quotes: {s.quotes.map((q: any, i: number) => <span key={i} style={{ background: '#e0e7ff', borderRadius: 4, padding: '2px 4px', marginRight: 4 }}>{q.text}</span>)}
        </div>
      )}
    </div>
  );
};

const ColorManagementModal: React.FC<{
  tagColors: TagColor[];
  onUpdateColor: (tagId: string, newColor: string) => void;
  onClose: () => void;
}> = ({ tagColors, onUpdateColor, onClose }) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
    <div className="bg-white p-6 rounded-lg w-96">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Manage Tag Colors</h3>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      {tagColors.map(tag => (
        <div key={tag.id} className="flex items-center gap-2 mb-2">
          <input 
            type="color" 
            value={tag.color}
            onChange={(e) => onUpdateColor(tag.id, e.target.value)}
          />
          <span>{tag.name}</span>
        </div>
      ))}
    </div>
  </div>
);

const AnnotationsTab: React.FC<AnnotationsTabProps> = ({ sessionId }) => {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [activeMsgId, setActiveMsgId] = React.useState<string | null>(null);
  const [annotations, setAnnotations] = React.useState<{ [msgId: string]: Annotation[] }>({});
  const [newComment, setNewComment] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  // Local state for tags (themes) and insight for the selected message
  const [localTags, setLocalTags] = React.useState<string[]>([]);
  const [localInsight, setLocalInsight] = React.useState<string>('');
  const [tagColors, setTagColors] = React.useState<TagColor[]>([]);
  const [showDetailedView, setShowDetailedView] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<{ name: string } | null>(null);

  React.useEffect(() => {
    const loadMessages = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/session/${sessionId}/messages_with_semantics`);
        const data = await response.json();
        if (data.success && data.messages) {
          setMessages(data.messages);
        } else {
          setMessages([]);
          setError('No messages found');
        }
      } catch (e: any) {
        setError('Failed to load messages');
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };
    loadMessages();
  }, [sessionId]);

  React.useEffect(() => {
    // When activeMsg changes, update local tags and insight
    if (activeMsg) {
      setLocalTags(activeMsg.semantic?.themes || []);
      setLocalInsight((activeMsg as any).insight || '');
    } else {
      setLocalTags([]);
      setLocalInsight('');
    }
  }, [activeMsgId]);

  // Only participant messages are annotatable
  const isParticipant = (msg: Message) => msg.role === 'participant' || msg.role === 'user';

  const handleAddAnnotation = async () => {
    if (!activeMsgId || !newComment.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/analysis/session/${sessionId}/annotations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId: activeMsgId, content: newComment }),
        credentials: 'include',
      });
      const data = await response.json();
      if (data.success && data.annotation) {
        setAnnotations(prev => ({
          ...prev,
          [activeMsgId]: [...(prev[activeMsgId] || []), data.annotation]
        }));
        setNewComment('');
      } else {
        setError(data.error || 'Failed to add annotation');
      }
    } catch (e: any) {
      setError('Failed to add annotation');
    } finally {
      setIsLoading(false);
    }
  };

  // Find the currently active participant message
  const activeMsg = messages.find(m => m.id === activeMsgId && isParticipant(m));

  // Patch activeMsg to ensure pain_points have all required fields and only pass if activeMsg is defined
  const patchedActiveMsg = activeMsg
    ? {
        content: activeMsg.content,
        semantic: {
          ...activeMsg.semantic,
          pain_points: activeMsg.semantic?.pain_points?.map((p: any) => ({
            quote: p.quote ?? activeMsg.content ?? '',
            issue: p.issue,
            severity_score: p.severity_score,
            sentiment: p.sentiment ?? '',
          })),
        },
      }
    : undefined;

  // Handlers for TagEditor
  const handleSaveTags = async () => {
    if (!activeMsgId) return;
    
    setIsSaving(true);
    try {
      const response = await fetch(`/api/session/${sessionId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messageId: activeMsgId,
          tags: localTags
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to save tags');
      }
      
      setMessages(prev => prev.map(msg => 
        msg.id === activeMsgId 
          ? { ...msg, tags: localTags }
          : msg
      ));
    } catch (error) {
      console.error('Error saving tags:', error);
      // Show error message
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddTag = async (tag: string) => {
    if (!localTags.includes(tag)) {
      const res = await fetch(`/api/session/${sessionId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messageId: activeMsgId,
          tags: [...localTags, tag]
        })
      });
      if (res.ok) {
        setLocalTags([...localTags, tag]);
        setMessages(prev => prev.map(msg => 
          msg.id === activeMsgId 
            ? { ...msg, tags: [...msg.tags, tag] }
            : msg
        ));
        handleSaveTags();
      } else {
        setError('Failed to add tag');
      }
    }
  };

  const handleRemoveTag = (tag: string) => {
    const updatedTags = localTags.filter(t => t !== tag);
    setLocalTags(updatedTags);
    setMessages(prev => prev.map(msg => 
      msg.id === activeMsgId 
        ? { ...msg, tags: updatedTags }
        : msg
    ));
    handleSaveTags();
  };

  // Handler for InsightAnnotation
  const handleSaveInsight = async (text: string) => {
    setLocalInsight(text);
    // Optionally, persist to backend:
    // await fetch(`/api/session/${sessionId}/insight`, { ... });
  };

  return (
    <div className="flex gap-6 h-[80vh]">
      {/* Left column: Transcript */}
      <div className="w-4/6 overflow-y-auto pr-4 border-r">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Transcript</h2>
          <button
            onClick={() => setShowDetailedView(!showDetailedView)}
            className="px-4 py-2 text-sm bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-md transition-colors flex items-center gap-2"
          >
            <span>{showDetailedView ? 'Hide Details' : 'Show Details'}</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        <div className="space-y-4">
          {messages.map((msg) => {
            // Patch for possible typo in data: support both semantic and semsntic
            const semantic = msg.semantic || msg.semsntic;
            return (
              <div
                key={msg.id}
                className={`p-4 rounded-lg transition-colors group relative ${
                  isParticipant(msg)
                    ? activeMsgId === msg.id
                      ? 'border-2 border-purple-500 bg-purple-50 cursor-pointer'
                      : 'hover:border-gray-300 border cursor-pointer'
                    : 'bg-gray-50 border cursor-default'
                }`}
                onClick={() => isParticipant(msg) && setActiveMsgId(msg.id)}
                style={{ opacity: isParticipant(msg) ? 1 : 0.7 }}
              >
                {/* Add edit button that appears on hover */}
                {isParticipant(msg) && (
                  <button 
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMsgId(msg.id);
                    }}
                    title="Edit annotations for this message"
                  >
                    <span className="text-gray-500 hover:text-gray-700">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </span>
                  </button>
                )}
                <div className="flex items-center mb-1">
                  <span className={`font-semibold ${msg.role === 'assistant' || msg.role === 'moderator' ? 'text-gray-500 text-sm' : ''}`}>
                    {msg.role === 'assistant' || msg.role === 'moderator' ? 'Moderator' : 'Participant'}
                  </span>
                  <span className="ml-2 text-xs text-gray-400">
                    {new Date(msg.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className={`text-gray-900 ${msg.role === 'assistant' || msg.role === 'moderator' ? 'text-sm' : ''}`}>{msg.content}</div>
                {/* Show tags for participant messages */}
                {isParticipant(msg) && msg.tags && msg.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {msg.tags.map((tag, i) => (
                      <span key={i} className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {/* Render semantic badges inline for all semantic fields */}
                {semantic && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {/* Always show themes and emotions */}
                    {msg.semantic?.themes?.map((theme, index) => (
                      <Tag key={index} label={`Theme: ${theme}`} color={colorMap.theme} />
                    ))}
                    {msg.semantic?.emotions?.map((emotion, index) => (
                      <Tag key={index} label={`Emotion: ${emotion}`} color={colorMap.emotion} />
                    ))}
                    
                    {/* Show these only in detailed view */}
                    {showDetailedView && (
                      <>
                        {msg.semantic?.intent && (
                          <Tag label={`Intent: ${msg.semantic.intent}`} color={colorMap.intent} />
                        )}
                        {msg.semantic?.task_success && (
                          <Tag label={`Task: ${msg.semantic.task_success}`} color={colorMap.task_success} />
                        )}
                        {msg.semantic?.goal_satisfaction && (
                          <Tag label={`Goal: ${msg.semantic.goal_satisfaction}`} color={colorMap.goal_satisfaction} />
                        )}
                        {msg.semantic?.persona && (
                          <Tag label={`Persona: ${msg.semantic.persona}`} color={colorMap.persona} />
                        )}
                        {msg.semantic?.frustration_markers?.map((marker, index) => (
                          <Tag key={index} label={`Frustration: ${marker}`} color={colorMap.pain} />
                        ))}
                        {msg.semantic?.ux_heuristic_violations?.map((violation, index) => (
                          <Tag key={index} label={`UX: ${violation}`} color={colorMap.heuristic} />
                        ))}
                        {msg.semantic?.pain_points?.map((point, index) => (
                          <Tag key={index} label={`Pain: ${point.issue}`} color={colorMap.pain} />
                        ))}
                        {msg.semantic?.affinity_hint && (
                          <Tag label={`Affinity: ${msg.semantic.affinity_hint}`} color={colorMap.theme} />
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Right column: Annotation workspace */}
      <div className="w-2/6 pl-6 flex flex-col">
        {activeMsg && (
          <div className="mb-2 p-2 bg-gray-50 border-b">
            <div className="text-xs text-gray-500 font-semibold">
              {activeMsg.role === 'user' || activeMsg.role === 'participant' ? 'Participant' : 'Moderator'}{' '}
              {new Date(activeMsg.timestamp).toLocaleString()}
            </div>
            <div className="text-sm text-gray-800 truncate">{activeMsg.content}</div>
          </div>
        )}
        {patchedActiveMsg ? (
          <>
            {/* TagEditor for themes/tags */}
            <div className="mb-4">
              <h3 className="font-medium mb-2">Tags (Themes)</h3>
              <div className="flex flex-wrap gap-2 mb-2">
                {localTags.map((tag, i) => (
                  <span key={i} className="flex items-center px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-700 border border-purple-200 mr-2">
                    {tag}
                    <button
                      className="ml-1 text-purple-500 hover:text-purple-800"
                      onClick={() => handleRemoveTag(tag)}
                      aria-label={`Remove tag ${tag}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <TagEditor
                value={localTags}
                onAdd={handleAddTag}
                onRemove={handleRemoveTag}
                suggestions={['workflow', 'frustration', 'insight', 'opportunity', 'emotion', 'goal']}
              />
            </div>
            {/* AnnotationDetails for semantic fields */}
            <AnnotationDetails
              message={{ ...patchedActiveMsg, semantic: { ...patchedActiveMsg.semantic, themes: localTags } }}
              onSaveComment={handleAddAnnotation}
            />
            {/* InsightAnnotation for key insight */}
            <div className="mb-4">
              <h3 className="font-medium mb-2">Key Insight</h3>
              <InsightAnnotation
                value={localInsight}
                onSave={handleSaveInsight}
                user={{ name: 'Researcher' }}
              />
            </div>
            {/* Comments section */}
            <div>
              <h3 className="font-medium mb-2">Comments</h3>
              {activeMsgId && annotations[activeMsgId]?.length > 0 ? (
                <div className="space-y-4">
                  {annotations[activeMsgId].map((annotation: Annotation) => (
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
              ) : (
                <div className="text-gray-500">No annotations for this message yet.</div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center text-gray-500 py-8">
            Select a participant response to view/add tags and annotations
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnotationsTab;
