import React from 'react';

interface Opportunity {
  stage?: string;
  description: string;
  impact?: 'low' | 'medium' | 'high' | string;
  effort?: 'low' | 'medium' | 'high' | string;
  [key: string]: any;
}

interface OpportunityListProps {
  opportunities: Opportunity[];
}

export const OpportunityList: React.FC<OpportunityListProps> = ({ opportunities }) => {
  if (!opportunities || opportunities.length === 0) return null;

  // Get impact/effort badge color
  const getBadgeColor = (value?: string) => {
    if (!value) return 'bg-gray-100 text-gray-500';
    switch (value.toLowerCase()) {
      case 'high':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-500';
    }
  };

  return (
    <div className="bg-green-50 p-6 rounded-lg shadow-md border border-green-100">
      <h2 className="text-xl font-bold text-green-800 mb-4">Opportunities</h2>
      
      <div className="space-y-4">
        {opportunities.map((opportunity, index) => (
          <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
            {opportunity.stage && (
              <div className="text-xs font-semibold text-green-600 mb-1">
                {opportunity.stage}
              </div>
            )}
            
            <p className="text-gray-700 text-sm mb-2">{opportunity.description}</p>
            
            <div className="flex flex-wrap gap-2 mt-1">
              {opportunity.impact && (
                <span className={`text-xs px-2 py-1 rounded ${getBadgeColor(opportunity.impact)}`}>
                  Impact: {opportunity.impact}
                </span>
              )}
              
              {opportunity.effort && (
                <span className={`text-xs px-2 py-1 rounded ${getBadgeColor(opportunity.effort)}`}>
                  Effort: {opportunity.effort}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 