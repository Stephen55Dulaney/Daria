import React from 'react';

interface PainPoint {
  stage?: string;
  description: string;
  severity?: number;
  [key: string]: any;
}

interface PainPointListProps {
  painPoints: PainPoint[];
}

export const PainPointList: React.FC<PainPointListProps> = ({ painPoints }) => {
  if (!painPoints || painPoints.length === 0) return null;

  // Get severity color
  const getSeverityColor = (severity?: number) => {
    if (severity === undefined) return 'bg-gray-200';
    if (severity >= 4) return 'bg-red-500';
    if (severity >= 3) return 'bg-orange-400';
    if (severity >= 2) return 'bg-yellow-400';
    return 'bg-green-400';
  };

  // Get severity label
  const getSeverityLabel = (severity?: number) => {
    if (severity === undefined) return 'Unknown';
    if (severity >= 4) return 'Critical';
    if (severity >= 3) return 'High';
    if (severity >= 2) return 'Medium';
    return 'Low';
  };

  return (
    <div className="bg-red-50 p-6 rounded-lg shadow-md border border-red-100">
      <h2 className="text-xl font-bold text-red-800 mb-4">Pain Points</h2>
      
      <div className="space-y-4">
        {painPoints.map((painPoint, index) => (
          <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
            {painPoint.stage && (
              <div className="text-xs font-semibold text-red-600 mb-1">
                {painPoint.stage}
              </div>
            )}
            
            <div className="flex items-start">
              {painPoint.severity !== undefined && (
                <div className="flex-shrink-0 mr-3">
                  <div className={`w-3 h-3 rounded-full ${getSeverityColor(painPoint.severity)} mb-1`}></div>
                  <span className="text-xs text-gray-500 whitespace-nowrap">
                    {getSeverityLabel(painPoint.severity)}
                  </span>
                </div>
              )}
              <p className="text-gray-700 text-sm">{painPoint.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 