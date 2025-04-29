import React from 'react';
import './JourneyStage.css';

export interface Quote {
  id: string;
  text: string;
  participant?: string;
}

export interface Action {
  id: string;
  text: string;
}

export interface Pain {
  id: string;
  text: string;
  severity?: number;
}

export interface Stage {
  id: string;
  title: string;
  description: string;
  quotes: Quote[];
  actions: Action[];
  pains: Pain[];
}

interface JourneyStageProps {
  stage: Stage;
}

const JourneyStage: React.FC<JourneyStageProps> = ({ stage }) => {
  return (
    <div className="journey-stage">
      <h3 className="stage-title">{stage.title}</h3>
      <p className="stage-description">{stage.description}</p>
      
      <div className="stage-content">
        {stage.quotes.length > 0 && (
          <div className="stage-section quotes-section">
            <h4>Quotes</h4>
            <ul className="quotes-list">
              {stage.quotes.map((quote) => (
                <li key={quote.id} className="quote-item">
                  <blockquote>
                    {quote.text}
                    {quote.participant && <cite> — {quote.participant}</cite>}
                  </blockquote>
                </li>
              ))}
            </ul>
          </div>
        )}

        {stage.actions.length > 0 && (
          <div className="stage-section actions-section">
            <h4>Actions</h4>
            <ul className="actions-list">
              {stage.actions.map((action) => (
                <li key={action.id} className="action-item">
                  {action.text}
                </li>
              ))}
            </ul>
          </div>
        )}

        {stage.pains.length > 0 && (
          <div className="stage-section pains-section">
            <h4>Pain Points</h4>
            <ul className="pains-list">
              {stage.pains.map((pain) => (
                <li key={pain.id} className="pain-item">
                  {pain.text}
                  {pain.severity !== undefined && (
                    <span className={`pain-severity severity-${pain.severity}`}>
                      (Severity: {pain.severity})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default JourneyStage; 