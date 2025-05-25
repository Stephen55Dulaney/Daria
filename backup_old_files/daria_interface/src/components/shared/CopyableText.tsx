import React, { useState } from 'react';

interface CopyableTextProps {
  text: string;
  className?: string;
}

const CopyableText: React.FC<CopyableTextProps> = ({ text, className = '' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <code className="text-xs break-all font-mono bg-gray-100 px-2 py-1 rounded">{text}</code>
      <button
        onClick={handleCopy}
        className="text-xs px-2 py-1 border rounded text-blue-500 border-blue-500 hover:bg-blue-50 transition-colors"
        title="Copy to clipboard"
      >
        {copied ? 'Copied!' : 'Copy ID'}
      </button>
    </div>
  );
};

export default CopyableText; 