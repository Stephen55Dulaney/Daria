import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import AdvancedSearch from './pages/AdvancedSearch'
import AnnotatedTranscript from './pages/AnnotatedTranscript'

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/advanced-search" element={<AdvancedSearch />} />
          <Route path="annotated-transcript/:transcriptId" element={<AnnotatedTranscript />} />
          {/* Add more routes as we build them */}
        </Routes>
      </Layout>
    </Router>
  )
}

export default App 