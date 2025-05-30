import React, { useState, useEffect } from 'react';
import { Input, Button, Select, Card, Tag, Spin, Alert, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;
const { Option } = Select;

interface SearchResult {
  content: string;
  metadata?: {
    session_id: string;
    themes?: string[];
    insight_tags?: string[];
    emotion?: string;
    emotion_intensity?: number;
    sentiment_score?: number;
  };
  score?: number;
}

interface Session {
  id: string;
  name: string;
}

const SuperSemanticSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await axios.get('/api/sessions');
        setSessions(response.data.map((session: any) => ({
          id: session.id,
          name: session.name || `Session ${session.id.slice(0, 8)}`
        })));
      } catch (err) {
        console.error('Error fetching sessions:', err);
      }
    };
    fetchSessions();
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/semantic_search', { 
        query,
        session_id: selectedSession || undefined
      });
      setResults(response.data.results || []);
    } catch (err) {
      setError('Failed to perform search. Please try again.');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getEmotionColor = (emotion?: string) => {
    if (!emotion) return 'default';
    const colors: { [key: string]: string } = {
      positive: 'success',
      negative: 'error',
      neutral: 'default',
      frustration: 'warning'
    };
    return colors[emotion] || 'default';
  };

  return (
    <div className="space-y-6">
      <div>
        <Title level={2}>Super Semantic Search</Title>
        <Text type="secondary">
          Search across all interview transcripts using semantic understanding. Find relevant content based on meaning, not just keywords.
        </Text>
      </div>

      <div className="flex gap-4">
        <Input
          size="large"
          placeholder="Search across all transcripts..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined />}
          style={{ flex: 1 }}
        />
        <Select
          size="large"
          style={{ width: 200 }}
          placeholder="Filter by session"
          allowClear
          onChange={(value) => setSelectedSession(value)}
        >
          {sessions.map(session => (
            <Option key={session.id} value={session.id}>
              {session.name}
            </Option>
          ))}
        </Select>
        <Button
          type="primary"
          size="large"
          onClick={handleSearch}
          loading={isLoading}
        >
          Search
        </Button>
      </div>

      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
        />
      )}

      <div className="space-y-4">
        {results.length === 0 && !isLoading && !error ? (
          <div className="text-center py-8 text-gray-500">
            No results found. Try a different search term.
          </div>
        ) : (
          results.map((result, index) => (
            <Card key={index} className="shadow-sm">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div className="font-mono whitespace-pre-line">{result.content}</div>
                  {result.metadata?.session_id && (
                    <Tag color="blue">
                      {sessions.find(s => s.id === result.metadata?.session_id)?.name || 'Unknown Session'}
                    </Tag>
                  )}
                </div>
                
                <div className="flex flex-wrap gap-2">
                  {result.metadata?.themes?.map((theme, i) => (
                    <Tag key={`theme-${i}`} color="blue">
                      {theme}
                    </Tag>
                  ))}
                  {result.metadata?.insight_tags?.map((tag, i) => (
                    <Tag key={`insight-${i}`} color="purple">
                      {tag}
                    </Tag>
                  ))}
                </div>

                <div className="flex items-center gap-4 text-sm">
                  {result.metadata?.emotion && (
                    <Tag color={getEmotionColor(result.metadata.emotion)}>
                      {result.metadata.emotion}
                    </Tag>
                  )}
                  {result.score !== undefined && (
                    <Text type="secondary">Relevance: {(result.score * 100).toFixed(1)}%</Text>
                  )}
                  {result.metadata?.sentiment_score !== undefined && (
                    <Text type="secondary">Sentiment: {(result.metadata.sentiment_score * 100).toFixed(1)}%</Text>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default SuperSemanticSearch; 