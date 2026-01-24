import React, { useState } from 'react';
import { Home, User, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const OutfitRecommendation = () => {
  const navigate = useNavigate();
  const [currentOutfit, setCurrentOutfit] = useState(1);

  const handleGenerateAnother = () => {
    // Logic to generate another outfit
    setCurrentOutfit(prev => prev + 1);
  };

  const handleSaveOutfit = () => {
    // Logic to save outfit
    alert('Outfit saved successfully!');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <button 
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <Home className="w-5 h-5 text-gray-600" />
          </button>
          
          <div className="absolute left-1/2 transform -translate-x-1/2">
            <h1 className="text-xl font-semibold text-gray-800">Your AI-Recommended Outfit</h1>
          </div>
          
          <button className="p-2 hover:bg-gray-100 rounded-lg transition">
            <User className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Your AI-Recommended Outfit
          </h2>
          <p className="text-gray-600">
            Based on your closet and current trends
          </p>
        </div>

        {/* Outfit Display */}
        <div className="bg-white rounded-2xl shadow-lg p-12 mb-8">
          <div className="flex flex-col items-center justify-center space-y-6">
            {/* Top */}
            <div className="w-48 h-48 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden">
              <div className="w-full h-full flex items-center justify-center">
                <svg className="w-32 h-32 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                </svg>
              </div>
            </div>

            {/* Grid with Shoes and Pants */}
            <div className="grid grid-cols-2 gap-6">
              {/* Shoes */}
              <div className="w-40 h-40 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden">
                <svg className="w-24 h-24 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M22 7h-7V1H9v6H2l10 9 10-9zM3.5 17l-.5 4h18l-.5-4H3.5z"/>
                </svg>
              </div>

              {/* Pants */}
              <div className="w-40 h-40 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden">
                <svg className="w-24 h-24 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-center space-x-4">
          <button
            onClick={handleSaveOutfit}
            className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-3 rounded-full font-medium transition shadow-lg hover:shadow-xl"
          >
            Save Outfit
          </button>
          
          <button
            onClick={handleGenerateAnother}
            className="bg-white hover:bg-gray-50 text-gray-700 px-8 py-3 rounded-full font-medium transition border border-gray-300 shadow-md hover:shadow-lg flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Generate Another Look</span>
          </button>
        </div>
      </main>
    </div>
  );
};

export default OutfitRecommendation;
