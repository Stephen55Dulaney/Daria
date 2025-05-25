import React from 'react'
import { Typography, Card, Row, Col, Button } from 'antd'
import { Link } from 'react-router-dom'
import { 
  FileSearchOutlined, 
  TeamOutlined, 
  RocketOutlined,
  FormOutlined
} from '@ant-design/icons'

const { Title, Paragraph } = Typography

const Home: React.FC = () => {
  return (
    <div className="py-8">
      <div className="text-center mb-8">
        <div className="mb-4 flex justify-center">
          <img 
            src="/static/images/daria-logo.png" 
            alt="Daria Logo" 
            className="w-16 h-16 object-contain"
          />
        </div>
        <Title level={1}>Welcome to Daria Interview Tool</Title>
        <Paragraph className="text-lg">
          Your AI-powered research assistant for user interviews and insights
        </Paragraph>
      </div>

      <Row gutter={[24, 24]} className="mt-8">
        <Col xs={24} md={8}>
          <Card 
            hoverable 
            className="h-full"
            cover={<div className="py-6 flex justify-center text-blue-500"><FileSearchOutlined style={{ fontSize: '3rem' }} /></div>}
          >
            <Title level={4} className="text-center">Research</Title>
            <Paragraph className="text-center mb-4">
              Conduct interviews, manage transcripts, and analyze results
            </Paragraph>
            <div className="flex justify-center">
              <Link to="/interview-archive">
                <Button type="primary">View Archive</Button>
              </Link>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card 
            hoverable 
            className="h-full"
            cover={<div className="py-6 flex justify-center text-green-500"><TeamOutlined style={{ fontSize: '3rem' }} /></div>}
          >
            <Title level={4} className="text-center">Personas</Title>
            <Paragraph className="text-center mb-4">
              Create and manage user personas based on research
            </Paragraph>
            <div className="flex justify-center">
              <Link to="/personas">
                <Button type="primary">View Personas</Button>
              </Link>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card 
            hoverable 
            className="h-full"
            cover={<div className="py-6 flex justify-center text-purple-500"><RocketOutlined style={{ fontSize: '3rem' }} /></div>}
          >
            <Title level={4} className="text-center">Journey Maps</Title>
            <Paragraph className="text-center mb-4">
              Create visual journey maps from your research insights
            </Paragraph>
            <div className="flex justify-center">
              <Link to="/journey-map">
                <Button type="primary">Create Map</Button>
              </Link>
            </div>
          </Card>
        </Col>
      </Row>

      <div className="mt-8 bg-blue-50 p-6 rounded-lg">
        <Title level={3} className="text-center mb-4">Try Our New Features</Title>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Card className="h-full" hoverable>
              <div className="flex items-center mb-4">
                <FormOutlined className="text-blue-500 text-xl mr-2" />
                <Title level={4} className="m-0">Research Survey</Title>
              </div>
              <Paragraph>
                Take our interactive survey to create your personalized research plan
              </Paragraph>
              <Link to="/research-survey">
                <Button type="primary">Start Survey</Button>
              </Link>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card className="h-full" hoverable>
              <div className="flex items-center mb-4">
                <RocketOutlined className="text-purple-500 text-xl mr-2" />
                <Title level={4} className="m-0">Research Adventure</Title>
              </div>
              <Paragraph>
                Explore research methods through our interactive discovery game
              </Paragraph>
              <Link to="/research-adventure">
                <Button type="primary">Start Adventure</Button>
              </Link>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default Home 