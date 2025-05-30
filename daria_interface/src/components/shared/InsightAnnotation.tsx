import React, { useState } from 'react';

interface InsightAnnotationProps {
  value: string;
  onSave: (text: string) => void;
  user?: { name: string; avatarUrl?: string };
}

const InsightAnnotation: React.FC<InsightAnnotationProps> = ({ value, onSave, user }) => {
  const [text, setText] = useState(value);

  return (
    <div className="mt-2">
      <textarea
        className="w-full border rounded p-2 text-sm"
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Add an insight or note..."
        rows={2}
      />
      <button
        className="mt-1 bg-green-500 text-white px-3 py-1 rounded text-xs"
        onClick={() => onSave(text)}
      >
        Save
      </button>
      {user && (
        <span className="ml-2 text-xs text-gray-400">by {user.name}</span>
      )}
    </div>
  );
};

export default InsightAnnotation;
