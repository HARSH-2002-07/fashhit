import React, { useState, useEffect } from 'react';
import { Search, ShoppingBag, User, Upload, Cloud, CloudRain } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AuthModal from './AuthModal';

const HomePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [weather, setWeather] = useState({ temp: '18', condition: 'Cloudy', location: 'London' });
  
  // Open auth modal if redirected from protected route
  useEffect(() => {
    if (location.state?.openAuth) {
      setIsAuthModalOpen(true);
    }
  }, [location]);

  const handleGetStarted = () => {
    if (user) {
      navigate('/closet');
    } else {
      setIsAuthModalOpen(true);
    }
  };

  const handleWatchDemo = () => {
    // Placeholder for demo functionality
    console.log('Watch Demo clicked');
  };

  // Mock outfit of the day
  const outfitOfDay = [
    { id: 1, name: 'Black Blazer', image: '/images/outfit/blazer.png' },
    { id: 2, name: 'Black Vest', image: '/images/outfit/vest.png' },
    { id: 3, name: 'Black Pants', image: '/images/outfit/pants.png' }
  ];

  // Mock shopping upgrades
  const shoppingUpgrades = [
    { id: 1, name: 'Navy Blazer', price: '$38.00', description: 'Matches your Navy Blazer', image: '/images/shop/navy-blazer.png' },
    { id: 2, name: 'Complete Look', price: '$79.00', description: 'Completes your look', image: '/images/shop/complete-1.png' },
    { id: 3, name: 'Complete Look', price: '$43.00', description: 'Completes your look', image: '/images/shop/complete-2.png' },
    { id: 4, name: 'Complete Look', price: '$58.00', description: 'Completes your look', image: '/images/shop/complete-3.png' },
    { id: 5, name: 'Navy Sweater', price: '$36.00', description: 'Matches your Navy Sweater', image: '/images/shop/navy-sweater.png' }
  ];

  const weekDays = [
    { day: 'Mon', date: '26', high: '18°', low: '12°' },
    { day: 'Tue', date: '27', high: '19°', low: '13°' },
    { day: 'Wed', date: '28', high: '18°', low: '12°' },
    { day: 'Thu', date: '29', high: '18°', low: '13°' },
    { day: 'Fri', date: '30', high: '19°', low: '13°' }
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Header with Hero */}
      <div className="relative bg-gradient-to-br from-gray-400 via-gray-500 to-gray-600 overflow-hidden">
        {/* Navigation */}
        <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
          <div className="flex items-center space-x-2">
            <span className="text-2xl font-light text-white tracking-wider">FASHION AI</span>
          </div>
          
          <div className="hidden md:flex items-center space-x-8">
            <a href="#home" className="text-white hover:text-gray-200 transition">
              Home
            </a>
            <a href="#wardrobe" className="text-white hover:text-gray-200 transition" onClick={(e) => { e.preventDefault(); navigate('/closet'); }}>
              Wardrobe
            </a>
            <a href="#planner" className="text-white hover:text-gray-200 transition" onClick={(e) => { e.preventDefault(); navigate('/outfit'); }}>
              Planner
            </a>
            <a href="#shop" className="text-white hover:text-gray-200 transition">
              Shop
            </a>
          </div>

          <div className="flex items-center space-x-6">
            <button className="text-white hover:text-gray-200 transition">
              <Search className="w-5 h-5" />
            </button>
            <button className="text-white hover:text-gray-200 transition">
              <ShoppingBag className="w-5 h-5" />
            </button>
            {user ? (
              <button 
                onClick={() => navigate('/closet')}
                className="text-white hover:text-gray-200 transition"
              >
                <User className="w-5 h-5" />
              </button>
            ) : (
              <button 
                onClick={() => setIsAuthModalOpen(true)}
                className="text-white hover:text-gray-200 transition"
              >
                <User className="w-5 h-5" />
              </button>
            )}
            <button 
              onClick={handleGetStarted}
              className="bg-white text-gray-800 px-4 py-2 rounded hover:bg-gray-100 transition"
            >
              Upload
            </button>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative z-10 max-w-7xl mx-auto px-8 py-20 md:py-32">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight mb-6">
                YOUR DIGITAL CLOSET,<br />ELEVATED BY AI
              </h1>
              <p className="text-xl text-gray-100 mb-8">
                Curate, plan, and discover your perfect look instantly.
              </p>
              <div className="flex space-x-4">
                <button 
                  onClick={handleGetStarted}
                  className="bg-white text-gray-800 px-8 py-3 rounded font-medium hover:bg-gray-100 transition"
                >
                  GET STARTED
                </button>
                <button 
                  onClick={handleWatchDemo}
                  className="bg-gray-700 text-white px-8 py-3 rounded font-medium hover:bg-gray-600 transition"
                >
                  WATCH DEMO
                </button>
              </div>
            </div>
            
            {/* Hero Images Grid - Diverse models */}
            <div className="hidden md:grid grid-cols-3 gap-2">
              <div className="space-y-2">
                <div className="bg-gray-700 rounded-lg h-48 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
                <div className="bg-gray-700 rounded-lg h-32 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="bg-gray-700 rounded-lg h-32 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
                <div className="bg-gray-700 rounded-lg h-48 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="bg-gray-700 rounded-lg h-48 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
                <div className="bg-gray-700 rounded-lg h-32 overflow-hidden">
                  <div className="w-full h-full bg-gradient-to-b from-gray-600 to-gray-700"></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-8 py-12 bg-white">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* AI Outfit of the Day */}
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">AI OUTFIT OF THE DAY</h2>
            
            {/* Weather Widget */}
            <div className="bg-gray-100 rounded-lg p-6 mb-6">
              <div className="flex items-center space-x-2 mb-4">
                <Cloud className="w-5 h-5 text-gray-600" />
                <span className="text-base font-medium text-gray-700">{weather.location}, {weather.temp}°C</span>
              </div>
              <div className="text-sm text-gray-600 mb-4">{weather.condition}</div>
              
              {/* Week Forecast */}
              <div className="grid grid-cols-5 gap-3 text-center text-sm">
                {weekDays.map((day, idx) => (
                  <div key={idx}>
                    <div className="text-gray-700 font-medium mb-1">{day.day}</div>
                    <div className="text-gray-500 text-xs mb-2">{day.date}</div>
                    <Cloud className="w-5 h-5 mx-auto mb-2 text-gray-400" />
                    <div className="text-gray-900 font-semibold">{day.high}</div>
                    <div className="text-gray-500 text-xs">{day.low}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Outfit Items */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              {outfitOfDay.map((item) => (
                <div key={item.id} className="bg-gray-100 rounded-lg p-6 aspect-[3/4] flex items-center justify-center">
                  <span className="text-gray-500 text-sm text-center">{item.name}</span>
                </div>
              ))}
            </div>

            <button className="w-full bg-gray-900 text-white py-4 rounded-lg font-semibold text-base hover:bg-gray-800 transition">
              Wear This
            </button>
          </div>

          {/* Smart Shopping Upgrades */}
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">SMART SHOPPING UPGRADES</h2>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              {shoppingUpgrades.slice(0, 4).map((item) => (
                <div key={item.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition">
                  <div className="aspect-[3/4] bg-gray-100 flex items-center justify-center">
                    <span className="text-gray-400 text-sm">{item.name}</span>
                  </div>
                  <div className="p-4">
                    <p className="text-sm text-gray-600 mb-2">{item.description}</p>
                    <p className="text-xl font-bold text-gray-900">{item.price}</p>
                  </div>
                </div>
              ))}
            </div>

            {shoppingUpgrades.length > 4 && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition">
                <div className="flex gap-4 p-4">
                  <div className="w-32 h-40 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-gray-400 text-sm text-center">{shoppingUpgrades[4].name}</span>
                  </div>
                  <div className="flex flex-col justify-center">
                    <p className="text-sm text-gray-600 mb-2">{shoppingUpgrades[4].description}</p>
                    <p className="text-xl font-bold text-gray-900">{shoppingUpgrades[4].price}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* How it Works Section */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-8">
          <h2 className="text-4xl font-bold text-center text-gray-900 mb-16">
            How it Works
          </h2>
          
          <div className="grid md:grid-cols-3 gap-12">
            {/* Step 1 */}
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-md mb-6">
                <Upload className="w-8 h-8 text-gray-700" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                1. Upload Your Wardrobe
              </h3>
              <p className="text-gray-600">
                Snap photos of your clothes. Our AI automatically categorizes them.
              </p>
            </div>

            {/* Step 2 */}
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-md mb-6">
                <svg className="w-8 h-8 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                2. Get Daily Recommendations
              </h3>
              <p className="text-gray-600">
                Receive personalized outfit ideas based on the weather, occasion, and your style.
              </p>
            </div>

            {/* Step 3 */}
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-md mb-6">
                <svg className="w-8 h-8 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                3. Plan Your Looks
              </h3>
              <p className="text-gray-600">
                Save your favorite outfits and plan your week in advance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Why Choose Us Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-8">
          <h2 className="text-4xl font-bold text-center text-gray-900 mb-16">
            Why Choose Us
          </h2>
          
          <div className="grid md:grid-cols-3 gap-12 max-w-5xl mx-auto">
            <div className="text-center">
              <div className="flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Save Time Every Morning
              </h3>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Discover New Combinations
              </h3>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Always Look Your Best
              </h3>
            </div>
          </div>
        </div>
      </section>

      {/* Auth Modal */}
      <AuthModal 
        isOpen={isAuthModalOpen} 
        onClose={() => setIsAuthModalOpen(false)} 
      />
    </div>
  );
};

export default HomePage;
