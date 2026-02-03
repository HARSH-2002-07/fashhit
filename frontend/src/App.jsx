import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import HomePage from './components/HomePage';
import VirtualCloset from './components/VirtualCloset';
import OutfitRecommendation from './components/OutfitRecommendation';
import FeedbackHistory from './components/FeedbackHistory';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/closet" element={<VirtualCloset />} />
            <Route path="/outfit" element={<OutfitRecommendation />} />
            <Route path="/feedback-history" element={<FeedbackHistory />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
