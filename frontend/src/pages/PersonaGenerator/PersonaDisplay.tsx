import React from 'react';
import { Card, Badge, Typography, Divider, Tag } from 'antd';

const { Title, Text, Paragraph } = Typography;

interface Persona {
  name: string;
  summary?: string;
  image_prompt?: string;
  demographics?: {
    age_range?: string;
    gender?: string;
    occupation?: string;
    location?: string;
    education?: string;
  };
  background?: string;
  personality_traits?: string[];
  daily_routine?: {
    morning?: string;
    afternoon?: string;
    evening?: string;
  };
  goals?: Array<{
    goal: string;
    motivation?: string;
    supporting_quotes?: string[];
  }>;
  pain_points?: Array<{
    pain_point: string;
    impact?: string;
    priority?: string;
    supporting_quotes?: string[];
  }>;
}

interface PersonaDisplayProps {
  persona: Persona;
}

const PersonaDisplay: React.FC<PersonaDisplayProps> = ({ persona }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: 32, marginTop: 32 }}>
      {/* Left Column */}
      <div>
        <Card bordered style={{ marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 8 }}>{persona.name || 'Persona Name'}</Title>
          <div style={{ background: '#f3f4f6', borderRadius: 8, minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16, padding: 12 }}>
            <div style={{ textAlign: 'center' }}>
              <Text type="secondary">AI Image will be generated here</Text>
              {persona.image_prompt && (
                <Paragraph style={{ fontSize: 12, marginTop: 8 }}>
                  <b>Prompt:</b> {persona.image_prompt}
                </Paragraph>
              )}
            </div>
          </div>
          {persona.summary && <Paragraph>{persona.summary}</Paragraph>}
        </Card>
        <Card bordered style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 0 }}>About</Title>
          <Paragraph style={{ marginBottom: 0 }}>{persona.background || 'No background information provided.'}</Paragraph>
        </Card>
        <Card bordered>
          <Title level={5} style={{ marginBottom: 8 }}>Demographics</Title>
          <div style={{ lineHeight: 2 }}>
            <div><b>Age:</b> {persona.demographics?.age_range || '—'}</div>
            <div><b>Gender:</b> {persona.demographics?.gender || '—'}</div>
            <div><b>Occupation:</b> {persona.demographics?.occupation || '—'}</div>
            <div><b>Location:</b> {persona.demographics?.location || '—'}</div>
            <div><b>Education:</b> {persona.demographics?.education || '—'}</div>
          </div>
        </Card>
      </div>

      {/* Right Column */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Personality Traits */}
        {persona.personality_traits && persona.personality_traits.length > 0 && (
          <Card bordered>
            <Title level={5}>Personality Traits</Title>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {persona.personality_traits.map((trait, idx) => (
                <Tag color="purple" key={idx}>{trait}</Tag>
              ))}
            </div>
          </Card>
        )}
        {/* Daily Routine */}
        {persona.daily_routine && (
          <Card bordered>
            <Title level={5}>Daily Routine</Title>
            <div style={{ display: 'flex', gap: 24 }}>
              <div><b>Morning</b><br />{persona.daily_routine.morning || '—'}</div>
              <div><b>Afternoon</b><br />{persona.daily_routine.afternoon || '—'}</div>
              <div><b>Evening</b><br />{persona.daily_routine.evening || '—'}</div>
            </div>
          </Card>
        )}
        {/* Goals & Motivations */}
        {persona.goals && persona.goals.length > 0 && (
          <Card bordered>
            <Title level={5}>Goals & Motivations</Title>
            {persona.goals.map((goal, idx) => (
              <div key={idx} style={{ marginBottom: 16 }}>
                <b>{goal.goal}</b>
                {goal.motivation && <div style={{ color: '#555', fontSize: 13 }}>{goal.motivation}</div>}
                {goal.supporting_quotes && goal.supporting_quotes.length > 0 && (
                  <div style={{ marginTop: 6, marginLeft: 8 }}>
                    {goal.supporting_quotes.map((q, qidx) => (
                      <blockquote key={qidx} style={{ margin: 0, fontStyle: 'italic', color: '#888', borderLeft: '3px solid #eee', paddingLeft: 8 }}>{q}</blockquote>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </Card>
        )}
        {/* Pain Points & Needs */}
        {persona.pain_points && persona.pain_points.length > 0 && (
          <Card bordered>
            <Title level={5}>Pain Points & Needs</Title>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {persona.pain_points.map((point, idx) => (
                <div key={idx} style={{ background: '#fff', borderRadius: 8, padding: 12, boxShadow: '0 1px 4px #f0f1f2' }}>
                  <b>{point.pain_point}</b>
                  {point.priority && <Badge color={point.priority === 'High' ? 'red' : point.priority === 'Medium' ? 'gold' : 'blue'} text={point.priority} style={{ marginLeft: 8 }} />}
                  {point.impact && <div style={{ color: '#555', fontSize: 13, marginTop: 2 }}>Impact: {point.impact}</div>}
                  {point.supporting_quotes && point.supporting_quotes.length > 0 && (
                    <div style={{ marginTop: 6, marginLeft: 8 }}>
                      {point.supporting_quotes.map((q, qidx) => (
                        <blockquote key={qidx} style={{ margin: 0, fontStyle: 'italic', color: '#888', borderLeft: '3px solid #eee', paddingLeft: 8 }}>{q}</blockquote>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default PersonaDisplay; 