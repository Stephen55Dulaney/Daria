import React from 'react';

interface JourneyMapHeaderProps {
  title: string;
  description: string;
}

export const JourneyMapHeader: React.FC<JourneyMapHeaderProps> = ({ title, description }) => {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-blue-800 mb-2">{title}</h1>
      {description && (
        <div className="bg-blue-50 p-6 rounded-lg shadow-sm border border-blue-100">
          <p className="text-gray-700">{description}</p>
        </div>
      )}
    </div>
  );
}; 