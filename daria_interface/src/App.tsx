import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import Analysis from './pages/Analysis';
import Gallery from './pages/Gallery';
import Sessions from './pages/Sessions';
import GuideSessions from './pages/guides/[guideId]/sessions';
import SessionDetailPage from './pages/SessionDetailPage';
import SuperSemanticSearch from './pages/SuperSemanticSearch';
import CharacterDetail from './components/shared/CharacterDetail';

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <ToastContainer position="top-right" autoClose={3000} />
        <nav className="bg-white shadow-sm">
          <div className="max-w-[1920px] mx-auto px-12">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <span className="text-xl font-bold text-blue-600">DARIA</span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/sessions"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Sessions
                  </Link>
                  <Link
                    to="/guides"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Guides
                  </Link>
                  <Link
                    to="/analysis"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Analysis
                  </Link>
                  <Link
                    to="/super-search"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Super Search
                  </Link>
                  <Link
                    to="/gallery"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Gallery
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-[1920px] mx-auto px-12">
          <Routes>
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/guides" element={<div>Guides (Coming Soon)</div>} />
            <Route path="/guides/:guideId" element={<div>Guide Details (Coming Soon)</div>} />
            <Route path="/guides/:guideId/sessions" element={<GuideSessions />} />
            <Route path="/guides/:guideId/sessions/:sessionId" element={<div>Guide Session Details (Coming Soon)</div>} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/super-search" element={<SuperSemanticSearch />} />
            <Route path="/gallery" element={<Gallery />} />
            <Route path="/gallery/:characterName" element={<CharacterDetail />} />
            <Route path="/" element={<Analysis />} />
            <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
