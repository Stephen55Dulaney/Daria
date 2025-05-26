import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import Analysis from './pages/Analysis';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/analysis" element={<Analysis />} />
          {/* Add other routes here */}
        </Routes>
      </div>
    </Router>
  );
}

export default App; 