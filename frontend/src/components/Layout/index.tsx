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
  PlusOutlined
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
    '/persona-generator'
  ].some(path => location.pathname.startsWith(path));

  return (
    <AntLayout className="min-h-screen">
      <Header className="bg-white px-4 border-b border-gray-200">
        <div className="flex items-center justify-between h-full">
          <Link to="/" className="flex items-center">
            <img src="/static/images/daria-logo.png" alt="Logo" className="h-8 mr-2" />
            <span className="text-lg font-semibold">DARIA</span>
          </Link>
          
          <Menu mode="horizontal" selectedKeys={[location.pathname]} className="flex-1 justify-end border-0">
            <Menu.Item key="/" icon={<HomeOutlined />}>
              <Link to="/">Home</Link>
            </Menu.Item>
            
            <Menu.SubMenu 
              key="research" 
              icon={<FileSearchOutlined />}
              title="Research"
              className={isResearchActive ? 'ant-menu-item-selected' : ''}
            >
              <Menu.Item key="/interview-archive" icon={<FileTextOutlined />}>
                <Link to="/interview-archive">Interview Archive</Link>
              </Menu.Item>
              <Menu.Item key="/advanced-search" icon={<FileSearchOutlined />}>
                <Link to="/advanced-search">Advanced Search</Link>
              </Menu.Item>
              <Menu.Item key="/upload-transcript" icon={<FileTextOutlined />}>
                <Link to="/upload-transcript">Upload Transcript</Link>
              </Menu.Item>
              <Menu.Item key="/create-interview" icon={<PlusOutlined />}>
                <Link to="/create-interview">Create Interview</Link>
              </Menu.Item>
            </Menu.SubMenu>
            
            <Menu.SubMenu key="personas" icon={<TeamOutlined />} title="Personas">
              <Menu.Item key="/personas">
                <Link to="/personas">Personas</Link>
              </Menu.Item>
              <Menu.Item key="/persona-generator">
                <Link to="/persona-generator">Generate Persona</Link>
              </Menu.Item>
            </Menu.SubMenu>
            
            <Menu.Item key="/journey-map" icon={<RocketOutlined />}>
              <Link to="/journey-map">Journey Map</Link>
            </Menu.Item>
          </Menu>
        </div>
      </Header>
      
      <Content className="p-6">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </Content>
    </AntLayout>
  );
};

export default Layout; 