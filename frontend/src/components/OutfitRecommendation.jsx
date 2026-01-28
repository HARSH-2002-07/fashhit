import React, { useState } from 'react';
import { 
  Home, User, RefreshCw, Sparkles, Loader2, Heart, LogOut, 
  CloudRain, ShoppingBag, ArrowRight, Shirt, Zap, MapPin 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const OutfitRecommendation = () => {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  
  // --- State Management ---
  const [hasOutfit, setHasOutfit] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentOutfit, setCurrentOutfit] = useState(null);
  const [scenario, setScenario] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [shoppingTip, setShoppingTip] = useState(null);
  const [weather, setWeather] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // --- Logic Handlers ---
  const handleRecommend = async () => {
    if (!scenario.trim()) return;
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/recommend-outfit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scenario, user_id: user?.id })
      });

      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || 'Failed to generate');

      setCurrentOutfit(result.outfit);
      setShoppingTip(result.shopping_tip);
      setWeather(result.weather);
      setHasOutfit(true);
    } catch (error) {
      console.error('Error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveOutfit = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/save-outfit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user?.id,
          outfit: currentOutfit,
          occasion: scenario,
          created_at: new Date().toISOString()
        })
      });

      const result = await response.json();
      if (!response.ok || !result.success) throw new Error('Failed to save');

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#F8F9FB] overflow-hidden font-sans text-slate-800">
      
      {/* --- SIDEBAR: CONTROLS & CONTEXT --- */}
      <aside className="w-[400px] bg-white border-r border-slate-200 flex flex-col z-20 shadow-xl relative">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">W</div>
            <span className="font-bold text-xl tracking-tight text-slate-900">Wardrobe<span className="text-indigo-600">AI</span></span>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Input Section */}
          <div className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Curate your look</h2>
              <p className="text-slate-500 text-sm">Where are you headed today?</p>
            </div>
            
            <div className="relative group">
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="e.g. A rooftop dinner date in Tokyo..."
                className="w-full h-32 p-4 bg-slate-50 border border-slate-200 rounded-2xl resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-slate-700 placeholder:text-slate-400"
              />
              <div className="absolute bottom-3 right-3">
                <Sparkles className={`w-5 h-5 ${scenario ? 'text-indigo-500' : 'text-slate-300'}`} />
              </div>
            </div>

            <button
              onClick={handleRecommend}
              disabled={loading || !scenario.trim()}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white py-4 rounded-xl font-semibold shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 group"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Zap className="w-5 h-5 fill-current" />
                  <span>Generate Outfit</span>
                </>
              )}
            </button>
            
            {error && (
              <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 flex gap-2">
                <span className="font-bold">Error:</span> {error}
              </div>
            )}
          </div>

          {/* Context Widgets (Visible only after generation) */}
          {hasOutfit && !loading && (
            <div className="space-y-4 animate-in slide-in-from-left-4 duration-500">
              
              {/* Weather Widget */}
              {weather && (
                <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Conditions</span>
                    <div className="flex items-center gap-2 mt-1">
                      <MapPin className="w-4 h-4 text-indigo-500" />
                      <span className="font-semibold text-slate-900">{weather.city}</span>
                    </div>
                    <div className="text-2xl font-bold text-slate-800 mt-1">
                      {weather.temp}°C <span className="text-base font-normal text-slate-500">{weather.condition}</span>
                    </div>
                  </div>
                  <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-blue-500">
                    <CloudRain className="w-6 h-6" />
                  </div>
                </div>
              )}

              {/* Shopping Insight */}
              {shoppingTip && (
                <div className="relative overflow-hidden bg-gradient-to-br from-violet-600 to-indigo-700 p-5 rounded-2xl text-white shadow-lg">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full -mr-8 -mt-8 blur-xl"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-2 mb-2 text-indigo-100">
                      <ShoppingBag className="w-4 h-4" />
                      <span className="text-xs font-bold uppercase tracking-wider">Stylist Tip</span>
                    </div>
                    <p className="font-medium leading-snug">{shoppingTip}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold border border-indigo-200">
                {user?.email?.[0].toUpperCase() || 'U'}
              </div>
              <div className="text-sm">
                <p className="font-semibold text-slate-900 truncate max-w-[120px]">
                  {user?.user_metadata?.full_name || 'User'}
                </p>
                <button onClick={signOut} className="text-slate-500 hover:text-red-600 text-xs flex items-center gap-1 transition-colors">
                  <LogOut className="w-3 h-3" /> Sign Out
                </button>
              </div>
            </div>
            <button onClick={() => navigate('/closet')} className="p-2 hover:bg-white rounded-lg text-slate-500 hover:text-indigo-600 transition-colors">
              <Shirt className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* --- MAIN CANVAS: OUTFIT DISPLAY --- */}
      <main className="flex-1 relative overflow-y-auto bg-slate-50/50 p-8 lg:p-12 flex flex-col">
        
        {!hasOutfit ? (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
            <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-slate-300" />
            </div>
            <h3 className="text-xl font-semibold text-slate-700">No outfit generated yet</h3>
            <p className="text-slate-500 max-w-xs mt-2">Use the sidebar to describe your occasion and get AI recommendations.</p>
          </div>
        ) : (
          /* The Outfit Grid */
          <div className="max-w-5xl mx-auto w-full animate-in fade-in zoom-in duration-500">
            
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-3xl font-bold text-slate-900">Your Generated Look</h1>
                <p className="text-slate-500 mt-1">Curated for: <span className="font-medium text-indigo-600">"{scenario}"</span></p>
              </div>
              
              <div className="flex gap-3">
                <button 
                  onClick={handleSaveOutfit}
                  className={`px-6 py-3 rounded-xl font-medium flex items-center gap-2 transition-all ${
                    saveSuccess 
                      ? 'bg-green-500 text-white shadow-lg shadow-green-200' 
                      : 'bg-white border border-slate-200 text-slate-700 hover:border-indigo-300 hover:text-indigo-600 hover:shadow-md'
                  }`}
                >
                  <Heart className={`w-5 h-5 ${saveSuccess ? 'fill-current' : ''}`} />
                  {saveSuccess ? 'Saved!' : 'Save Look'}
                </button>
                <button 
                  onClick={handleRecommend} 
                  className="p-3 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-indigo-600 hover:border-indigo-300 transition-all"
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Bento Grid Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 h-[600px]">
              
              {/* Col 1: Outerwear & Top (Stacked) */}
              <div className="lg:col-span-1 flex flex-col gap-6 h-full">
                {/* Outerwear */}
                <ItemCard 
                  item={currentOutfit?.outerwear} 
                  label="Outerwear" 
                  fallbackIcon={<Shirt />}
                  className="flex-1"
                />
                {/* Top */}
                <ItemCard 
                  item={currentOutfit?.tops} 
                  label="Top" 
                  fallbackIcon={<Shirt />}
                  className="flex-1"
                />
              </div>

              {/* Col 2: Bottoms (Tall Hero) */}
              <div className="lg:col-span-2 h-full">
                <ItemCard 
                  item={currentOutfit?.bottoms} 
                  label="Bottoms" 
                  fallbackIcon={<Shirt />}
                  className="h-full"
                  isHero={true}
                />
              </div>

              {/* Col 3: Shoes (Standard) */}
              <div className="lg:col-span-1 flex flex-col gap-6 h-full">
                <ItemCard 
                  item={currentOutfit?.shoes} 
                  label="Footwear" 
                  fallbackIcon={<ShoppingBag />}
                  className="h-1/2"
                />
                
                {/* Decorative / Info Block */}
                <div className="h-1/2 bg-slate-900 rounded-3xl p-6 flex flex-col justify-between text-slate-300">
                  <Sparkles className="w-8 h-8 text-yellow-400" />
                  <div>
                    <p className="text-xs uppercase tracking-widest font-bold mb-1 opacity-50">Confidence Score</p>
                    <p className="text-3xl font-bold text-white">98%</p>
                    <p className="text-xs mt-2 text-slate-400">Perfectly matched for weather & style.</p>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// --- Helper Component: Individual Item Card ---
const ItemCard = ({ item, label, fallbackIcon, className, isHero }) => {
  return (
    <div className={`relative group bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500 ${className}`}>
      {/* Background Gradient for depth */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white opacity-50"></div>
      
      <div className="absolute top-4 left-4 z-10">
        <span className="px-3 py-1 bg-white/90 backdrop-blur-md rounded-full text-xs font-bold text-slate-500 uppercase tracking-wider border border-slate-100">
          {label}
        </span>
      </div>

      <div className="absolute inset-0 flex items-center justify-center p-6">
        {item ? (
          <img 
            src={item.clean_image_url} 
            alt={label} 
            className={`w-full h-full object-contain mix-blend-multiply drop-shadow-lg group-hover:scale-110 transition-transform duration-500 ${isHero ? 'p-4' : ''}`}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-300">
            {React.cloneElement(fallbackIcon, { className: "w-12 h-12 mb-2 opacity-50" })}
            <span className="text-sm font-medium">None Selected</span>
          </div>
        )}
      </div>

      {/* Hover Details (Glassmorphism) */}
      {item && (
        <div className="absolute inset-x-4 bottom-4 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
          <div className="bg-white/95 backdrop-blur-xl p-4 rounded-2xl shadow-lg border border-slate-100">
            <h4 className="font-bold text-slate-900 truncate">{item.attributes?.sub_category || label}</h4>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              {item.attributes?.primary_color}
              <span className="mx-1">•</span>
              {item.attributes?.formality}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OutfitRecommendation;
