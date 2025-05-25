import { useState, useEffect } from 'react'
import axios, { AxiosResponse, AxiosError } from 'axios'

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
    axios.get<ServicesResponse>('http://127.0.0.1:5025/api/check_services')
      .then((response: AxiosResponse<ServicesResponse>) => setServices(response.data))
      .catch((err: AxiosError) => setError(err.message))
  }, [])

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '24px', marginBottom: '20px' }}>DARIA Services Monitor</h1>
      
      <div style={{ 
        padding: '15px',
        border: '1px solid #ccc',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <h2 style={{ fontSize: '18px', marginBottom: '10px' }}>API Health</h2>
        <p style={{ 
          color: health === 'API is healthy' ? 'green' : 'red',
          fontWeight: 'bold'
        }}>
          {health}
        </p>
      </div>

      <div style={{ 
        padding: '15px',
        border: '1px solid #ccc',
        borderRadius: '8px'
      }}>
        <h2 style={{ fontSize: '18px', marginBottom: '10px' }}>Services Status</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {Object.entries(services).map(([service, status]) => (
          <div key={service} style={{ marginBottom: '10px' }}>
            <strong>{service}:</strong>{' '}
            <span style={{ color: status.running ? 'green' : 'red' }}>
              {status.running ? 'Running' : 'Stopped'}
              {status.uptime && ` (Uptime: ${status.uptime})`}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App 