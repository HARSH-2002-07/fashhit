import React, { useState } from 'react';
import { Home, User, RefreshCw, Sparkles, Loader2, Heart, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const OutfitRecommendation = () => {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [hasOutfit, setHasOutfit] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentOutfit, setCurrentOutfit] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleRecommend = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/recommend-outfit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: 'casual everyday outfit',
          user_id: user?.id
        })
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || 'Failed to generate outfit');
      }

      setCurrentOutfit(result.outfit);
      setHasOutfit(true);
    } catch (error) {
      console.error('Error generating outfit:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAnother = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/recommend-outfit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: 'casual everyday outfit',
          user_id: user?.id
        })
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || 'Failed to generate outfit');
      }

      setCurrentOutfit(result.outfit);
    } catch (error) {
      console.error('Error generating outfit:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveOutfit = () => {
    // Logic to save outfit to database
    alert('Outfit saved to your collection! ✅');
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
          
          {/* User Menu */}
          <div className="relative">
            <button 
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <User className="w-5 h-5 text-gray-600" />
              {user && (
                <span className="text-sm text-gray-600 hidden sm:inline">
                  {user.email?.split('@')[0]}
                </span>
              )}
            </button>
            
            {/* Dropdown Menu */}
            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                <div className="px-4 py-2 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-700">
                    {user?.user_metadata?.full_name || 'User'}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                </div>
                <button
                  onClick={async () => {
                    await signOut();
                    navigate('/');
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        {!hasOutfit ? (
          /* Initial State - Show Recommend Button */
          <div className="flex flex-col items-center justify-center min-h-[60vh]">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mb-6">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Ready for Your Perfect Look?
              </h2>
              <p className="text-lg text-gray-600 max-w-md mx-auto">
                Our AI will analyze your wardrobe and create the perfect outfit combination based on style, weather, and trends.
              </p>
            </div>

            <button
              onClick={handleRecommend}
              disabled={loading}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed text-white px-12 py-4 rounded-full text-lg font-semibold transition shadow-xl hover:shadow-2xl transform hover:scale-105 flex items-center space-x-3"
            >
              {loading ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <span>Creating Your Outfit...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  <span>Recommend Outfit</span>
                </>
              )}
            </button>

            {error && (
              <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm max-w-md">
                <p className="font-medium">⚠️ {error}</p>
                {error.includes('No items') && (
                  <button
                    onClick={() => navigate('/closet')}
                    className="mt-2 text-blue-600 hover:text-blue-700 underline"
                  >
                    Go to Virtual Closet to add items
                  </button>
                )}
              </div>
            )}

            <p className="text-sm text-gray-500 mt-6">
              Make sure you have items in your closet first
            </p>
          </div>
        ) : (
          /* Show Outfit Recommendation */
          <>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                Your AI-Recommended Outfit
              </h2>
              <p className="text-gray-600">
                Based on your closet and current trends
              </p>
            </div>

            {/* Outfit Display */}
            <div className="bg-white rounded-2xl shadow-lg p-12 mb-8 relative">
              {loading && (
                <div className="absolute inset-0 bg-white bg-opacity-90 rounded-2xl flex items-center justify-center z-10">
                  <div className="flex flex-col items-center">
                    <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                    <p className="text-gray-600 font-medium">Generating new look...</p>
                  </div>
                </div>
              )}
              
              <div className="flex flex-col items-center justify-center space-y-6">
                {/* Top */}
                <div className="w-64 h-64 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg flex items-center justify-center overflow-hidden border-2 border-blue-200">
                  {currentOutfit?.tops ? (
                    <img 
                      src={currentOutfit.tops.clean_image_url} 
                      alt="Top" 
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="text-center">
                      <svg className="w-32 h-32 text-blue-300 mx-auto" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                      </svg>
                      <p className="text-sm text-gray-500 mt-2">No top available</p>
                    </div>
                  )}
                </div>

                {/* Grid with Bottoms and Shoes */}
                <div className="grid grid-cols-2 gap-6">
                  {/* Bottoms */}
                  <div className="w-48 h-48 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg flex items-center justify-center overflow-hidden border-2 border-purple-200">
                    {currentOutfit?.bottoms ? (
                      <img 
                        src={currentOutfit.bottoms.clean_image_url} 
                        alt="Bottom" 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center">
                        <svg className="w-24 h-24 text-purple-300 mx-auto" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                        </svg>
                        <p className="text-xs text-gray-500 mt-2">No bottoms</p>
                      </div>
                    )}
                  </div>

                  {/* Shoes */}
                  <div className="w-48 h-48 bg-gradient-to-br from-pink-50 to-red-50 rounded-lg flex items-center justify-center overflow-hidden border-2 border-pink-200">
                    {currentOutfit?.shoes ? (
                      <img 
                        src={currentOutfit.shoes.clean_image_url} 
                        alt="Shoes" 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center">
                        <svg className="w-24 h-24 text-pink-300 mx-auto" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M22 7h-7V1H9v6H2l10 9 10-9zM3.5 17l-.5 4h18l-.5-4H3.5z"/>
                        </svg>
                        <p className="text-xs text-gray-500 mt-2">No shoes</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-center space-x-4">
              <button
                onClick={handleSaveOutfit}
                disabled={loading}
                className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed text-white px-8 py-3 rounded-full font-medium transition shadow-lg hover:shadow-xl transform hover:scale-105 flex items-center space-x-2"
              >
                <Heart className="w-5 h-5" />
                <span>Save Outfit</span>
              </button>
              
              <button
                onClick={handleGenerateAnother}
                disabled={loading}
                className="bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-700 px-8 py-3 rounded-full font-medium transition border-2 border-gray-300 shadow-md hover:shadow-lg transform hover:scale-105 flex items-center space-x-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                <span>Try Another Look</span>
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default OutfitRecommendation;
