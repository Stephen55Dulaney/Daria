import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Dropdown from '../common/Dropdown'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate()
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)

  const researchMenuItems = [
    {
      label: 'Interview Archive',
      onClick: () => navigate('/interview-archive')
    },
    {
      label: 'Advanced Search',
      onClick: () => navigate('/advanced-search')
    },
    {
      label: 'Create New Interview',
      onClick: () => navigate('/create-interview')
    },
    {
      label: 'Upload Interview',
      onClick: () => navigate('/upload-interview')
    }
  ]

  const synthesisMenuItems = [
    {
      label: 'Personas',
      onClick: () => navigate('/personas')
    },
    {
      label: 'Journey Maps',
      onClick: () => navigate('/journey-maps')
    }
  ]

  const newItemOptions = [
    {
      label: 'New Interview',
      onClick: () => navigate('/create-interview')
    },
    {
      label: 'New Project',
      onClick: () => navigate('/create-project')
    },
    {
      label: 'New Persona',
      onClick: () => navigate('/create-persona')
    },
    {
      label: 'New Journey Map',
      onClick: () => navigate('/create-journey-map')
    }
  ]

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="text-xl font-bold text-gray-800">Daria</Link>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link to="/" className="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium h-16">
                  Home
                </Link>
                <Link to="/plan" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium h-16">
                  Plan
                </Link>
                <Dropdown
                  trigger={
                    <button className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium h-16">
                      Research
                    </button>
                  }
                  items={researchMenuItems}
                />
                <Dropdown
                  trigger={
                    <button className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium h-16">
                      Synthesis
                    </button>
                  }
                  items={synthesisMenuItems}
                />
              </div>
            </div>
            <div className="flex items-center">
              <Dropdown
                trigger={
                  <button className="ml-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700">
                    + New
                  </button>
                }
                items={newItemOptions}
              />
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}

export default Layout 