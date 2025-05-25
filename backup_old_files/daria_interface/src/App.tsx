import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import axios from 'axios'
import './App.css'
import SessionsList from './components/SessionsList'
import TranscriptView from './components/TranscriptView'
import DiscussionGuidesList from './components/DiscussionGuidesList'

interface ServiceStatus {
  running: boolean
  uptime?: string
}

interface ServicesResponse {
  [key: string]: ServiceStatus
}

function App() {
  const [health, setHealth] = useState<string>('Checking...')
  const [services, setServices] = useState<ServicesResponse>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check API health
    axios.get('http://127.0.0.1:5025/api/health')
      .then(() => setHealth('API is healthy'))
      .catch(() => setHealth('API is down'))

    // Check services status
    axios.get<ServicesResponse>('http://127.0.0.1:5025/api/services')
      .then(response => setServices(response.data))
      .catch(err => setError(err.message))
  }, [])

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-6 py-3">
            <div className="flex justify-between items-center">
              <Link to="/" className="text-xl font-bold text-gray-800">
                DARIA Monitor
              </Link>
              <div className="flex items-center space-x-4">
                <Link to="/" className="text-gray-600 hover:text-gray-800">
                  Services
                </Link>
                <Link to="/sessions" className="text-gray-600 hover:text-gray-800">
                  Sessions
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="container mx-auto py-6">
          <Routes>
            <Route path="/" element={
              <>
                <div className="mb-8">
                  <h2 className="text-xl font-bold mb-4">Services Status</h2>
                  {error ? (
                    <p className="text-red-600">Error: {error}</p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(services).map(([name, status]) => (
                        <div key={name} className="p-4 bg-white rounded-lg shadow-sm">
                          <h3 className="font-medium">{name}</h3>
                          <div className="flex items-center mt-2">
                            <span className={`w-2 h-2 rounded-full mr-2 ${status.running ? 'bg-green-500' : 'bg-red-500'}`} />
                            <span className="text-sm text-gray-600">
                              {status.running ? 'Running' : 'Stopped'}
                              {status.uptime && ` - Uptime: ${status.uptime}`}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <DiscussionGuidesList />
              </>
            } />
            <Route path="/sessions" element={<SessionsList />} />
            <Route path="/transcript/:id" element={<TranscriptView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
