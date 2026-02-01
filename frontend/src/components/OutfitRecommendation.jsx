import React, { useState } from 'react';
import { 
  Home, User, RefreshCw, Sparkles, Loader2, Heart, LogOut, 
  CloudRain, ShoppingBag, ArrowRight, Shirt, Zap, MapPin, ThumbsUp, ThumbsDown 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/weather-animations.css';

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
  const [isSaved, setIsSaved] = useState(false);
  const [savedOutfitId, setSavedOutfitId] = useState(null);
  const [shoppingTip, setShoppingTip] = useState(null);
  const [weather, setWeather] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [confidence, setConfidence] = useState(null);
  const [template, setTemplate] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'paperdoll'
  const [swappingSlot, setSwappingSlot] = useState(null); // Track which item is being swapped
  const [userFeedback, setUserFeedback] = useState(null); // 'like' | 'dislike' | null

  // --- Weather Background Gradient ---
  const getWeatherBackground = () => {
    if (!weather?.condition) return 'bg-gradient-to-br from-slate-50 to-slate-100';
    
    const condition = weather.condition.toLowerCase();
    
    if (condition.includes('rain') || condition.includes('storm') || condition.includes('drizzle')) {
      return 'bg-gradient-to-br from-blue-900 via-slate-700 to-blue-800';
    } else if (condition.includes('cloud') || condition.includes('overcast')) {
      return 'bg-gradient-to-br from-slate-400 via-gray-300 to-slate-500';
    } else if (condition.includes('sun') || condition.includes('clear') || condition.includes('bright')) {
      return 'bg-gradient-to-br from-amber-300 via-orange-200 to-yellow-300';
    } else if (condition.includes('snow') || condition.includes('blizzard')) {
      return 'bg-gradient-to-br from-blue-50 via-slate-100 to-blue-100';
    } else if (condition.includes('fog') || condition.includes('mist') || condition.includes('haze')) {
      return 'bg-gradient-to-br from-slate-300 via-gray-200 to-slate-400';
    } else if (condition.includes('wind')) {
      return 'bg-gradient-to-br from-cyan-200 via-sky-100 to-blue-200';
    } else if (condition.includes('night')) {
      return 'bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900';
    }
    
    return 'bg-gradient-to-br from-slate-50 to-slate-100';
  };

  const getWeatherEffect = () => {
    if (!weather?.condition) return 'weather-breathe';
    
    const condition = weather.condition.toLowerCase();
    
    if (condition.includes('rain') || condition.includes('storm') || condition.includes('drizzle')) {
      return 'rain-effect weather-breathe';
    } else if (condition.includes('cloud') || condition.includes('overcast')) {
      return 'cloud-effect weather-breathe';
    } else if (condition.includes('sun') || condition.includes('clear') || condition.includes('bright')) {
      return 'sun-effect weather-breathe';
    } else if (condition.includes('snow') || condition.includes('blizzard')) {
      return 'snow-effect weather-breathe';
    }
    
    return 'weather-breathe';
  };

  // --- Logic Handlers ---
  const handleRecommend = async () => {
    if (!scenario.trim()) return;
    setLoading(true);
    setError(null);
    setUserFeedback(null);
    setIsSaved(false);
    setSavedOutfitId(null);
    
    try {
      const response = await fetch(`${API_URL}/recommend-outfit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scenario, user_id: user?.id })
      });

      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || 'Failed to generate');

      console.log('API Response:', result); // Debug
      setCurrentOutfit(result.outfit);
      setShoppingTip(result.shopping_tip);
      setWeather(result.weather);
      setConfidence(result.confidence);
      setTemplate(result.template);
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
      if (isSaved && savedOutfitId) {
        // Unsave: delete from database
        const response = await fetch(`${API_URL}/saved-outfits/${savedOutfitId}`, {
          method: 'DELETE'
        });

        const result = await response.json();
        if (!response.ok || !result.success) throw new Error('Failed to unsave');

        setIsSaved(false);
        setSavedOutfitId(null);
        console.log('Outfit unsaved successfully');
      } else {
        // Save: add to database
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

        setIsSaved(true);
        setSavedOutfitId(result.data[0].id);
        console.log('Outfit saved successfully');
      }
    } catch (error) {
      setError(error.message);
      console.error('Error toggling save:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSwapItem = async (slot) => {
    setSwappingSlot(slot);
    try {
      const response = await fetch(`${API_URL}/swap-item`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user?.id,
          slot: slot,
          current_outfit: currentOutfit,
          query: scenario
        })
      });

      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || 'Failed to swap item');

      setCurrentOutfit(result.outfit);
      console.log(`✅ Swapped ${slot}`);
    } catch (error) {
      console.error('Error swapping item:', error);
      setError(error.message);
    } finally {
      setSwappingSlot(null);
    }
  };

  const handleFeedback = async (rating) => {
    try {
      const response = await fetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user?.id,
          rating: rating, // 'like' or 'dislike'
          outfit_items: currentOutfit,
          scenario: scenario
        })
      });

      const result = await response.json();
      if (!response.ok || !result.success) throw new Error('Failed to save feedback');

      setUserFeedback(rating);
      console.log(`📊 Feedback: ${rating}`);
    } catch (error) {
      console.error('Error sending feedback:', error);
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
                {/* Feedback Buttons */}
                <button 
                  onClick={() => handleFeedback('like')}
                  className={`p-3 border rounded-xl transition-all group ${
                    userFeedback === 'like'
                      ? 'bg-green-500 text-white border-green-600 shadow-lg shadow-green-200'
                      : 'bg-white border-slate-200 text-slate-500 hover:text-green-600 hover:border-green-300'
                  }`}
                  title="I like this outfit"
                >
                  <ThumbsUp className={`w-5 h-5 ${
                    userFeedback === 'like' ? 'fill-current' : 'group-hover:fill-green-100'
                  }`} />
                </button>
                <button 
                  onClick={() => handleFeedback('dislike')}
                  className={`p-3 border rounded-xl transition-all group ${
                    userFeedback === 'dislike'
                      ? 'bg-red-500 text-white border-red-600 shadow-lg shadow-red-200'
                      : 'bg-white border-slate-200 text-slate-500 hover:text-red-600 hover:border-red-300'
                  }`}
                  title="I don't like this outfit"
                >
                  <ThumbsDown className={`w-5 h-5 ${
                    userFeedback === 'dislike' ? 'fill-current' : 'group-hover:fill-red-100'
                  }`} />
                </button>
                
                {/* View Mode Toggle */}
                <button 
                  onClick={() => setViewMode(viewMode === 'grid' ? 'paperdoll' : 'grid')} 
                  className="px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:text-indigo-600 hover:border-indigo-300 transition-all flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  {viewMode === 'grid' ? 'Paper Doll' : 'Grid View'}
                </button>
                
                {/* Save Button */}
                <button 
                  onClick={handleSaveOutfit}
                  className={`px-6 py-3 rounded-xl font-medium flex items-center gap-2 transition-all ${
                    isSaved 
                      ? 'bg-green-500 text-white shadow-lg shadow-green-200' 
                      : 'bg-white border border-slate-200 text-slate-700 hover:border-indigo-300 hover:text-indigo-600 hover:shadow-md'
                  }`}
                >
                  <Heart className={`w-5 h-5 ${isSaved ? 'fill-current' : ''}`} />
                  {isSaved ? 'Saved!' : 'Save Look'}
                </button>
                
                {/* Regenerate Button */}
                <button 
                  onClick={handleRecommend} 
                  className="p-3 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-indigo-600 hover:border-indigo-300 transition-all"
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Conditional Layout: Paper Doll or Grid */}
            {viewMode === 'paperdoll' ? (
              /* Paper Doll Overlay View */
              <div className={`relative min-h-[700px] rounded-3xl overflow-hidden ${getWeatherBackground()} ${getWeatherEffect()} transition-all duration-700`}>
                {/* Weather indicator overlay */}
                {weather?.condition && (
                  <div className="absolute top-6 right-6 px-4 py-2 bg-white/90 backdrop-blur-md rounded-full text-sm font-medium text-slate-700 shadow-lg z-50">
                    <CloudRain className="w-4 h-4 inline mr-2" />
                    {weather.condition} • {weather.temp}°C
                  </div>
                )}
                
                {/* Layered items - Paper Doll style with fixed canvas */}
                <div className="flex items-center justify-center min-h-[700px] p-8">
                  <div className="relative" style={{ width: '400px', height: '600px' }}>
                    
                    {/* Outerwear (Jacket) - Widest layer to contain torso */}
                    {currentOutfit?.outerwear && (
                      <img 
                        src={currentOutfit.outerwear.clean_image_url} 
                        alt="Outerwear"
                        style={{
                          position: 'absolute',
                          width: '55%',
                          top: '5%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 3,
                          height: 'auto',
                          filter: 'drop-shadow(0px 10px 15px rgba(0,0,0,0.3))'
                        }}
                        className="object-contain animate-in fade-in zoom-in duration-1000"
                      />
                    )}
                    
                    {/* Top (Shirt) - Slightly smaller, peeks through outerwear */}
                    {currentOutfit?.tops && (
                      <img 
                        src={currentOutfit.tops.clean_image_url} 
                        alt="Top"
                        style={{
                          position: 'absolute',
                          width: '48%',
                          top: '8%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 2,
                          height: 'auto',
                          filter: 'drop-shadow(0px 10px 15px rgba(0,0,0,0.3))'
                        }}
                        className="object-contain animate-in fade-in zoom-in duration-700"
                      />
                    )}
                    
                    {/* Bottoms (Pants) - Narrower than shoulders to simulate waist */}
                    {currentOutfit?.bottoms && (
                      <img 
                        src={currentOutfit.bottoms.clean_image_url} 
                        alt="Bottoms"
                        style={{
                          position: 'absolute',
                          width: '42%',
                          top: '40%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 1,
                          height: 'auto',
                          filter: 'drop-shadow(0px 10px 15px rgba(0,0,0,0.3))'
                        }}
                        className="object-contain animate-in fade-in zoom-in duration-500"
                      />
                    )}
                    
                    {/* Footwear - Stable bottom position */}
                    {currentOutfit?.shoes && (
                      <img 
                        src={currentOutfit.shoes.clean_image_url} 
                        alt="Footwear"
                        style={{
                          position: 'absolute',
                          width: '35%',
                          bottom: '8%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 4,
                          height: 'auto',
                          filter: 'drop-shadow(0px 10px 15px rgba(0,0,0,0.3))'
                        }}
                        className="object-contain animate-in fade-in slide-in-from-bottom-4 duration-700"
                      />
                    )}
                    
                    {/* One-Piece (if exists, replaces top + bottom) */}
                    {currentOutfit?.one_piece && (
                      <img 
                        src={currentOutfit.one_piece.clean_image_url} 
                        alt="One-Piece"
                        style={{
                          position: 'absolute',
                          width: '50%',
                          top: '8%',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 2,
                          height: 'auto',
                          filter: 'drop-shadow(0px 10px 15px rgba(0,0,0,0.3))'
                        }}
                        className="object-contain animate-in fade-in zoom-in duration-700"
                      />
                    )}
                    
                    {/* Accessory - Floating top-right */}
                    {currentOutfit?.accessory && (
                      <img 
                        src={currentOutfit.accessory.clean_image_url} 
                        alt="Accessory"
                        style={{
                          position: 'absolute',
                          top: '5%',
                          right: '8%',
                          zIndex: 5,
                          width: '20%',
                          height: 'auto',
                          filter: 'drop-shadow(0px 8px 12px rgba(0,0,0,0.25))'
                        }}
                        className="object-contain animate-in fade-in slide-in-from-right-4 duration-700"
                      />
                    )}
                  </div>
                </div>
                
                {/* Confidence Badge */}
                <div className="absolute bottom-6 left-6 bg-white/95 backdrop-blur-xl p-6 rounded-2xl shadow-lg border border-slate-100 z-50">
                  <p className="text-xs uppercase tracking-widest font-bold mb-1 text-slate-500">Confidence</p>
                  <p className="text-4xl font-bold text-indigo-600">
                    {confidence?.percentage || 0}%
                  </p>
                  <p className="text-xs mt-2 text-slate-600">
                    {confidence?.percentage >= 85 ? 'Perfect Match' : 
                     confidence?.percentage >= 70 ? 'Great Look' : 
                     confidence?.percentage >= 55 ? 'Good Pairing' : 'Basic'}
                  </p>
                </div>
                
                {/* Shopping Tip */}
                {shoppingTip && (
                  <div className="absolute bottom-6 right-6 max-w-sm bg-amber-50/95 backdrop-blur-xl p-4 rounded-2xl shadow-lg border border-amber-200 z-50">
                    <div className="flex items-start gap-3">
                      <ShoppingBag className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-bold text-amber-900 uppercase tracking-wide mb-1">Shopping Tip</p>
                        <p className="text-sm text-amber-800">{shoppingTip}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Original Bento Grid Layout */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 min-h-[600px]">
              
              {/* Check if one-piece outfit */}
              {currentOutfit?.one_piece ? (
                /* One-Piece Layout */
                <>
                  {/* Col 1-2: One-Piece (Hero) */}
                  <div className="lg:col-span-2 h-full min-h-[600px]">
                    <ItemCard 
                      item={currentOutfit?.one_piece} 
                      label="One-Piece" 
                      fallbackIcon={<Shirt />}
                      className="h-full"
                      isHero={true}
                      onSwap={handleSwapItem}
                      slotKey="one_piece"
                      isSwapping={swappingSlot === 'one_piece'}
                    />
                  </div>

                  {/* Col 3: Footwear & Accessory */}
                  <div className="lg:col-span-1 flex flex-col gap-6 h-full min-h-[600px]">
                    <ItemCard 
                      item={currentOutfit?.shoes} 
                      label="Footwear" 
                      fallbackIcon={<ShoppingBag />}
                      className="flex-1"
                      onSwap={handleSwapItem}
                      slotKey="shoes"
                      isSwapping={swappingSlot === 'shoes'}
                    />
                    {currentOutfit?.accessory && (
                      <ItemCard 
                        item={currentOutfit?.accessory} 
                        label="Accessory" 
                        fallbackIcon={<Sparkles />}
                        className="flex-1"
                        onSwap={handleSwapItem}
                        slotKey="accessory"
                        isSwapping={swappingSlot === 'accessory'}
                      />
                    )}
                  </div>

                  {/* Col 4: Info Block */}
                  <div className="lg:col-span-1 flex flex-col gap-6 h-full min-h-[600px]">
                    {/* Confidence & Info Block - moved here */}
                    <div className="flex-1 bg-slate-900 rounded-3xl p-6 flex flex-col justify-between text-slate-300">
                      <Sparkles className="w-8 h-8 text-yellow-400" />
                      <div>
                        <p className="text-xs uppercase tracking-widest font-bold mb-1 opacity-50">Confidence Score</p>
                        <p className="text-3xl font-bold text-white">
                          {confidence?.percentage || 0}%
                        </p>
                        <p className="text-xs mt-2 text-slate-400">
                          {confidence?.percentage >= 85 ? 'Perfectly matched' : 
                           confidence?.percentage >= 70 ? 'Great combination' : 
                           confidence?.percentage >= 55 ? 'Good pairing' : 'Basic match'}
                          {template && ` • ${template} style`}
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                /* Standard Layout */
                <>
                  {/* Col 1: Outerwear/Accessory & Top (Stacked) */}
                  <div className="lg:col-span-1 flex flex-col gap-6 h-full min-h-[600px]">
                    {/* Show Outerwear or Accessory */}
                    {currentOutfit?.outerwear ? (
                      <ItemCard 
                        item={currentOutfit?.outerwear} 
                        label="Outerwear" 
                        fallbackIcon={<Shirt />}
                        className="flex-1"
                        onSwap={handleSwapItem}
                        slotKey="outerwear"
                        isSwapping={swappingSlot === 'outerwear'}
                      />
                    ) : currentOutfit?.accessory ? (
                      <ItemCard 
                        item={currentOutfit?.accessory} 
                        label="Accessory" 
                        fallbackIcon={<Sparkles />}
                        className="flex-1"
                        onSwap={handleSwapItem}
                        slotKey="accessory"
                        isSwapping={swappingSlot === 'accessory'}
                      />
                    ) : (
                      <div className="flex-1 bg-white/50 rounded-3xl border border-dashed border-slate-200 flex items-center justify-center text-slate-300">
                        <Shirt className="w-8 h-8" />
                      </div>
                    )}
                    {/* Top */}
                    <ItemCard 
                      item={currentOutfit?.tops} 
                      label="Top" 
                      fallbackIcon={<Shirt />}
                      className="flex-1"
                      onSwap={handleSwapItem}
                      slotKey="tops"
                      isSwapping={swappingSlot === 'tops'}
                    />
                  </div>

                  {/* Col 2-3: Bottoms (Tall Hero) */}
                  <div className="lg:col-span-2 h-full min-h-[600px]">
                    <ItemCard 
                      item={currentOutfit?.bottoms} 
                      label="Bottoms" 
                      fallbackIcon={<Shirt />}
                      className="h-full"
                      isHero={true}
                      onSwap={handleSwapItem}
                      slotKey="bottoms"
                      isSwapping={swappingSlot === 'bottoms'}
                    />
                  </div>

                  {/* Col 4: Shoes & Info */}
                  <div className="lg:col-span-1 flex flex-col gap-6 h-full min-h-[600px]">
                    <ItemCard 
                      item={currentOutfit?.shoes} 
                      label="Footwear" 
                      fallbackIcon={<ShoppingBag />}
                      className="h-1/2"
                      onSwap={handleSwapItem}
                      slotKey="shoes"
                      isSwapping={swappingSlot === 'shoes'}
                    />
                    
                    {/* Confidence & Info Block */}
                    <div className="h-1/2 bg-slate-900 rounded-3xl p-6 flex flex-col justify-between text-slate-300">
                      <Sparkles className="w-8 h-8 text-yellow-400" />
                      <div>
                        <p className="text-xs uppercase tracking-widest font-bold mb-1 opacity-50">Confidence Score</p>
                        <p className="text-3xl font-bold text-white">
                          {confidence?.percentage || 0}%
                        </p>
                        <p className="text-xs mt-2 text-slate-400">
                          {confidence?.percentage >= 85 ? 'Perfectly matched' : 
                           confidence?.percentage >= 70 ? 'Great combination' : 
                           confidence?.percentage >= 55 ? 'Good pairing' : 'Basic match'}
                          {template && ` • ${template} style`}
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

// --- Helper Component: Individual Item Card ---
const ItemCard = ({ item, label, fallbackIcon, className, isHero, onSwap, slotKey, isSwapping }) => {
  return (
    <div className={`relative group bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500 ${className}`}>
      {/* Background Gradient for depth */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white opacity-50"></div>
      
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
        <span className="px-3 py-1 bg-white/90 backdrop-blur-md rounded-full text-xs font-bold text-slate-500 uppercase tracking-wider border border-slate-100">
          {label}
        </span>
      </div>

      {/* Swap Button */}
      {item && onSwap && (
        <button
          onClick={() => onSwap(slotKey)}
          disabled={isSwapping}
          className="absolute top-4 right-4 z-10 p-2 bg-white/90 backdrop-blur-md rounded-full text-slate-600 hover:text-indigo-600 hover:bg-white transition-all border border-slate-100 hover:border-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Swap this item"
        >
          <RefreshCw className={`w-4 h-4 ${isSwapping ? 'animate-spin' : ''}`} />
        </button>
      )}

      <div className="absolute inset-0 flex items-center justify-center p-6">
        {item ? (
          <img 
            src={item.clean_image_url} 
            alt={label} 
            className={`w-full h-full object-contain mix-blend-multiply drop-shadow-lg group-hover:scale-110 transition-transform duration-500 ${isHero ? 'p-4' : ''} ${isSwapping ? 'opacity-50' : ''}`}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-300">
            {React.cloneElement(fallbackIcon, { className: "w-12 h-12 mb-2 opacity-50" })}
            <span className="text-sm font-medium">None Selected</span>
          </div>
        )}
      </div>

      {/* Hover Details (Glassmorphism) - Enhanced with new metadata fields */}
      {item && (
        <div className="absolute inset-x-4 bottom-4 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
          <div className="bg-white/95 backdrop-blur-xl p-4 rounded-2xl shadow-lg border border-slate-100 space-y-2">
            <h4 className="font-bold text-slate-900 truncate">{item.attributes?.sub_category || label}</h4>
            
            {/* Primary Info */}
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              {item.attributes?.primary_color}
              {item.attributes?.secondary_color && (
                <>
                  <span className="mx-1">+</span>
                  {item.attributes?.secondary_color}
                </>
              )}
              <span className="mx-1">•</span>
              {item.attributes?.formality}
            </div>

            {/* Additional Metadata */}
            <div className="flex flex-wrap gap-1 mt-2">
              {item.attributes?.pattern && item.attributes.pattern !== 'Solid' && (
                <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">
                  {item.attributes.pattern}
                </span>
              )}
              {item.attributes?.material && (
                <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                  {item.attributes.material}
                </span>
              )}
              {item.attributes?.fit && (
                <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                  {item.attributes.fit}
                </span>
              )}
            </div>

            {/* Style Tags */}
            {item.attributes?.style_tags && item.attributes.style_tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {item.attributes.style_tags.slice(0, 3).map((tag, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full text-xs">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Occasion Tags */}
            {item.attributes?.occasion && item.attributes.occasion.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {item.attributes.occasion.slice(0, 2).map((occ, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-green-50 text-green-700 rounded-full text-xs">
                    {occ}
                  </span>
                ))}
              </div>
            )}

            {/* Advanced Metadata (layer_role, silhouette, etc.) */}
            {(item.attributes?.layer_role || item.attributes?.silhouette_volume) && (
              <div className="text-xs text-slate-400 mt-2 pt-2 border-t border-slate-100">
                {item.attributes?.layer_role && item.attributes.layer_role !== 'None' && (
                  <span>{item.attributes.layer_role} Layer</span>
                )}
                {item.attributes?.silhouette_volume && item.attributes?.layer_role && (
                  <span className="mx-1">•</span>
                )}
                {item.attributes?.silhouette_volume && (
                  <span>{item.attributes.silhouette_volume} Fit</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default OutfitRecommendation;
