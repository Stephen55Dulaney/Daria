import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/shared/Layout';
import Sessions from './pages/Sessions';
import GuideSessions from './pages/guides/[guideId]/sessions';

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Layout>
        <Routes>
          <Route path="/" element={<div>Dashboard (Coming Soon)</div>} />
          
          {/* Sessions routes */}
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/sessions/:sessionId" element={<div>Individual Session View (Coming Soon)</div>} />
          
          {/* Guides routes */}
          <Route path="/guides" element={<div>Guides (Coming Soon)</div>} />
          <Route path="/guides/:guideId" element={<div>Guide Details (Coming Soon)</div>} />
          <Route path="/guides/:guideId/sessions" element={<GuideSessions />} />
          <Route path="/guides/:guideId/sessions/:sessionId" element={<div>Guide Session Details (Coming Soon)</div>} />
          
          {/* 404 route */}
          <Route path="*" element={<div>404 - Not Found</div>} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
