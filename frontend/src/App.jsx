import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './components/HomePage';
import VirtualCloset from './components/VirtualCloset';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/closet" element={<VirtualCloset />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
