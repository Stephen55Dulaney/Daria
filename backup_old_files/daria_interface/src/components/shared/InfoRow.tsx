import React from 'react';
import type { ReactNode } from 'react';

interface InfoRowProps {
  label: string;
  value: ReactNode;
  className?: string;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value, className = '' }) => {
  return (
    <div className={`mb-1 ${className}`}>
      <span className="font-medium text-gray-700">{label}: </span>
      <span className="text-gray-900">{value || '—'}</span>
    </div>
  );
};

export default InfoRow; 