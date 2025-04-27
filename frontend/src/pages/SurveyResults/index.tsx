import React, { useEffect, useState } from 'react';
import { Typography, Card, Button, Spin, notification, Avatar, Row, Col, Divider } from 'antd';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { BarChartOutlined, TeamOutlined, FileSearchOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

interface SurveyResponse {
  primary_objective: string;
  research_type: string;
  timeline: string;
  budget: string;
  methods: string;
  avatar_path: string;
  recommendations?: {
    primary_method: string;
    secondary_method: string;
    innovative_approach: string;
  };
}

const SurveyResults: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [surveyResponses, setSurveyResponses] = useState<SurveyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await axios.get('/api/survey-results');
        if (response.data.success) {
          setSurveyResponses(response.data.survey_responses);
        } else {
          setError('No survey responses found. Please take the survey first.');
          setTimeout(() => {
            navigate('/research-survey');
          }, 3000);
        }
      } catch (err) {
        console.error('Error fetching survey results:', err);
        setError('Error fetching your survey results.');
        notification.error({
          message: 'Error',
          description: 'Could not load your survey results. Please try again.',
        });
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" tip="Loading your research plan..." />
      </div>
    );
  }

  if (error || !surveyResponses) {
    return (
      <div className="text-center p-8">
        <Title level={3} className="text-red-500">{error || 'Survey data not found'}</Title>
        <Paragraph>Redirecting you to the survey...</Paragraph>
      </div>
    );
  }

  // Map the survey responses to more user-friendly text
  const getObjectiveText = (objective: string) => {
    return objective === 'user_needs' ? 'Understanding User Needs' : 'Market Validation';
  };

  const getResearchTypeText = (type: string) => {
    return type === 'qualitative' ? 'Qualitative Research' : 'Quantitative Research';
  };

  const getTimelineText = (timeline: string) => {
    return timeline === 'urgent' ? 'Urgent (1-2 weeks)' : 'Standard (1-2 months)';
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Title level={2} className="text-center mb-8">Your Personalized Research Plan</Title>

      <Row gutter={24}>
        <Col span={8}>
          <Card className="text-center mb-6 h-full">
            <Avatar 
              src={surveyResponses.avatar_path || "/static/images/default-researcher.png"} 
              size={120} 
              className="mb-4"
            />
            <Title level={4}>Researcher Profile</Title>
            <Divider />
            <div className="text-left">
              <Paragraph><strong>Primary Objective:</strong> {getObjectiveText(surveyResponses.primary_objective)}</Paragraph>
              <Paragraph><strong>Research Type:</strong> {getResearchTypeText(surveyResponses.research_type)}</Paragraph>
              <Paragraph><strong>Timeline:</strong> {getTimelineText(surveyResponses.timeline)}</Paragraph>
              <Paragraph><strong>Budget:</strong> {surveyResponses.budget === 'limited' ? 'Limited' : 'Flexible'}</Paragraph>
              <Paragraph><strong>Preferred Method:</strong> {surveyResponses.methods === 'interviews' ? 'User Interviews' : 'Surveys & Analytics'}</Paragraph>
            </div>
          </Card>
        </Col>
        
        <Col span={16}>
          <Card className="mb-6">
            <Title level={4} className="flex items-center">
              <BarChartOutlined className="mr-2" /> Recommended Research Methods
            </Title>
            <div className="p-4 bg-blue-50 rounded-lg mb-4">
              <Title level={5}>Primary Method</Title>
              <Paragraph>
                {surveyResponses.recommendations?.primary_method || 'User interviews with key stakeholders'}
              </Paragraph>
            </div>
            <div className="p-4 bg-green-50 rounded-lg mb-4">
              <Title level={5}>Secondary Method</Title>
              <Paragraph>
                {surveyResponses.recommendations?.secondary_method || 'Contextual inquiry with target users'}
              </Paragraph>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <Title level={5}>Innovative Approach</Title>
              <Paragraph>
                {surveyResponses.recommendations?.innovative_approach || 'Co-creation workshops with mixed stakeholder groups'}
              </Paragraph>
            </div>
          </Card>

          <Card>
            <Title level={4} className="flex items-center">
              <FileSearchOutlined className="mr-2" /> Next Steps
            </Title>
            <Paragraph>
              Based on your responses, we recommend beginning with the primary research method, followed by 
              validation using the secondary method. The innovative approach can provide unique insights
              that traditional methods might miss.
            </Paragraph>
            <div className="flex justify-between mt-6">
              <Button type="primary" onClick={() => navigate('/research-adventure')}>
                Start Research Adventure
              </Button>
              <Button onClick={() => navigate('/create-interview')}>
                Create Interview Guide
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SurveyResults; 