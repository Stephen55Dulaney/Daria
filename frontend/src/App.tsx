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
import PersonasGallery from './pages/PersonasGallery'
import JourneyMapsGallery from './pages/JourneyMapsGallery'
import AnnotatedTranscript from './pages/AnnotatedTranscript'
import PersonaGenerator from './pages/PersonaGenerator'
import AdvancedSearch from './pages/AdvancedSearch'
import UploadTranscript from './pages/UploadTranscript'
import CreateInterview from './pages/CreateInterview'
import ResearchSurvey from './pages/ResearchSurvey'
import SurveyResults from './pages/SurveyResults'
import ResearchAdventure from './pages/ResearchAdventure'
import ViewPersona from './pages/Persona/ViewPersona'
import ViewJourneyMap from './pages/JourneyMap/ViewJourneyMap'

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
          <Route path="/personas" element={<PersonasGallery />} />
          <Route path="/journey-maps" element={<JourneyMapsGallery />} />
          <Route path="/annotated-transcript/:transcriptId" element={<AnnotatedTranscript />} />
          <Route path="/persona-generator" element={<PersonaGenerator />} />
          <Route path="/advanced-search" element={<AdvancedSearch />} />
          <Route path="/upload-transcript" element={<UploadTranscript />} />
          <Route path="/create-interview" element={<CreateInterview />} />
          <Route path="/research-survey" element={<ResearchSurvey />} />
          <Route path="/survey-results" element={<SurveyResults />} />
          <Route path="/research-adventure" element={<ResearchAdventure />} />
          <Route path="/view-persona/:id" element={<ViewPersona />} />
          <Route path="/view-journey-map/:id" element={<ViewJourneyMap />} />
          {/* Add more routes as we build them */}
        </Routes>
      </Layout>
    </Router>
  )
}

export default App 