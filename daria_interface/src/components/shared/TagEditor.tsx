import React, { useState } from 'react';

interface TagEditorProps {
  value: string[];
  onAdd: (tag: string) => void;
  onRemove: (tag: string) => void;
  suggestions?: string[];
}

const TagEditor: React.FC<TagEditorProps> = ({ value, onAdd, onRemove, suggestions = [] }) => {
  const [input, setInput] = useState('');

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {value.map(tag => (
        <span key={tag} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
          {tag}
          <button className="ml-1 text-red-500" onClick={() => onRemove(tag)}>×</button>
        </span>
      ))}
      <input
        className="border rounded px-2 py-1 text-xs"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && input.trim()) {
            onAdd(input.trim());
            setInput('');
          }
        }}
        placeholder="Add tag..."
        list="tag-suggestions"
      />
      <datalist id="tag-suggestions">
        {suggestions.map(s => <option key={s} value={s} />)}
      </datalist>
    </div>
  );
};

export default TagEditor;
