import React from 'react';

interface Touchpoint {
  stage?: string;
  channel?: string;
  description: string;
  [key: string]: any;
}

interface TouchpointListProps {
  touchpoints: Touchpoint[];
}

export const TouchpointList: React.FC<TouchpointListProps> = ({ touchpoints }) => {
  if (!touchpoints || touchpoints.length === 0) return null;

  return (
    <div className="bg-teal-50 p-6 rounded-lg shadow-md border border-teal-100">
      <h2 className="text-xl font-bold text-teal-800 mb-4">Key Touchpoints</h2>
      
      <div className="space-y-4">
        {touchpoints.map((touchpoint, index) => (
          <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
            {touchpoint.stage && (
              <div className="text-xs font-semibold text-teal-600 mb-1">
                {touchpoint.stage}
              </div>
            )}
            
            <div className="flex items-start">
              {touchpoint.channel && (
                <span className="inline-block bg-teal-100 text-teal-800 text-xs px-2 py-1 rounded mr-2">
                  {touchpoint.channel}
                </span>
              )}
              <p className="text-gray-700 text-sm">{touchpoint.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 