import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layout as AntLayout, Menu } from 'antd';
import {
  HomeOutlined,
  FileSearchOutlined,
  UserOutlined,
  RocketOutlined,
  TeamOutlined,
  FileTextOutlined,
  PlusOutlined,
  FormOutlined
} from '@ant-design/icons';

const { Header, Content } = AntLayout;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const isResearchActive = [
    '/interview-archive',
    '/advanced-search',
    '/create-interview',
    '/upload-interview',
    '/annotated-transcript',
    '/transcript',
    '/persona-generator',
    '/research-survey',
    '/survey-results',
    '/research-adventure'
  ].some(path => location.pathname.startsWith(path));

  // Refactored menu items array for Ant Design v5+
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link to="/">Home</Link>,
    },
    {
      key: 'research',
      icon: <FileSearchOutlined />,
      label: 'Research',
      className: isResearchActive ? 'ant-menu-item-selected' : '',
      children: [
        {
          key: '/interview-archive',
          icon: <FileTextOutlined />,
          label: <Link to="/interview-archive">Interview Archive</Link>,
        },
        {
          key: '/advanced-search',
          icon: <FileSearchOutlined />,
          label: <Link to="/advanced-search">Advanced Search</Link>,
        },
        {
          key: '/upload-transcript',
          icon: <FileTextOutlined />,
          label: <Link to="/upload-transcript">Upload Transcript</Link>,
        },
        {
          key: '/create-interview',
          icon: <PlusOutlined />,
          label: <Link to="/create-interview">Create Interview</Link>,
        },
        {
          key: '/research-survey',
          icon: <FormOutlined />,
          label: <Link to="/research-survey">Research Survey</Link>,
        },
      ],
    },
    {
      key: 'personas',
      icon: <TeamOutlined />,
      label: 'Personas',
      children: [
        {
          key: '/personas',
          label: <Link to="/personas">Persona Archive</Link>,
        },
        {
          key: '/persona-generator',
          label: <Link to="/persona-generator">Generate Persona</Link>,
        },
      ],
    },
    {
      key: 'journey-map',
      icon: <RocketOutlined />,
      label: 'Journey Map',
      children: [
        {
          key: '/journey-maps',
          label: <Link to="/journey-maps">Journey Map Archive</Link>,
        },
        {
          key: '/journey-map',
          label: <Link to="/journey-map">Generate Journey Map</Link>,
        },
      ],
    },
  ];

  return (
    <AntLayout className="min-h-screen bg-gray-50">
      <Header className="bg-white px-4 border-b border-gray-200 shadow-sm">
        <div className="flex items-center justify-between h-full">
          <Link to="/" className="flex items-center">
            <img src="/static/images/daria-logo.png" alt="Logo" className="w-8 h-8 mr-2 object-contain" />
            <span className="text-lg font-semibold text-blue-700">DARIA</span>
          </Link>
          {/* Use items prop instead of children */}
          <Menu mode="horizontal" selectedKeys={[location.pathname]} className="flex-1 justify-end border-0" items={menuItems} />
        </div>
      </Header>
      <Content className="p-6">
        <div className="max-w-7xl mx-auto bg-white rounded-lg shadow-sm p-6">
          {children}
        </div>
      </Content>
    </AntLayout>
  );
};

export default Layout; 