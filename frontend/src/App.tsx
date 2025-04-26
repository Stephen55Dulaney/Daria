import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import NewInterview from './pages/NewInterview'
import TestInterview from './pages/TestInterview'
import Archive from './pages/Archive'
import Persona from './pages/Persona'
import CreatePersonas from './pages/CreatePersonas'
import JourneyMap from './pages/JourneyMap'
import AnnotatedTranscript from './pages/AnnotatedTranscript'
import PersonaGenerator from './pages/PersonaGenerator'
import AdvancedSearch from './pages/AdvancedSearch'

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new-interview" element={<NewInterview />} />
          <Route path="/test-interview" element={<TestInterview />} />
          <Route path="/archive" element={<Archive />} />
          <Route path="/interview-archive" element={<Archive />} />
          <Route path="/persona" element={<Persona />} />
          <Route path="/create-personas" element={<CreatePersonas />} />
          <Route path="/journey-map" element={<JourneyMap />} />
          <Route path="/annotated-transcript/:transcriptId" element={<AnnotatedTranscript />} />
          <Route path="/persona-generator" element={<PersonaGenerator />} />
          <Route path="/advanced-search" element={<AdvancedSearch />} />
          {/* Add more routes as we build them */}
        </Routes>
      </Layout>
    </Router>
  )
}

export default App 