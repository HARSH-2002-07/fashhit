import React, { useState, useEffect } from 'react';
import { Home, Bell, User, Upload, Filter, SortAsc, Heart, MoreVertical, Loader2, Trash2, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const VirtualCloset = () => {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [selectedTab, setSelectedTab] = useState('All');
  const [uploadedItems, setUploadedItems] = useState([]);
  const [savedOutfits, setSavedOutfits] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [favorites, setFavorites] = useState(new Set());

  const tabs = ['All', 'Tops', 'Bottoms', 'Shoes', 'Outerwear', 'Accessories', 'Saved Outfits'];

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      navigate('/', { state: { openAuth: true } });
    }
  }, [user, navigate]);

  // Load items from backend API
  useEffect(() => {
    loadItems();
  }, [selectedTab]);

  const loadItems = async () => {
    try {
      if (selectedTab === 'Saved Outfits') {
        const response = await fetch(`${API_URL}/saved-outfits?user_id=${user?.id}`);
        const result = await response.json();
        
        if (result.success) {
          setSavedOutfits(result.data || []);
        }
      } else if (selectedTab === 'All') {
        // Load all items from all categories (including accessory and one_piece)
        const categories = ['tops', 'bottoms', 'shoes', 'outerwear', 'accessory', 'one_piece'];
        let allItems = [];
        
        for (const category of categories) {
          const response = await fetch(`${API_URL}/wardrobe/${category}?user_id=${user?.id}`);
          const result = await response.json();
          if (result.success) {
            allItems = [...allItems, ...(result.data || [])];
          }
        }
        
        setUploadedItems(allItems);
      } else {
        // Map tab name to API category (handle plural/singular)
        const categoryMap = {
          'accessories': 'accessory',
          'tops': 'tops',
          'bottoms': 'bottoms',
          'shoes': 'shoes',
          'outerwear': 'outerwear'
        };
        const apiCategory = categoryMap[selectedTab.toLowerCase()] || selectedTab.toLowerCase();
        
        const response = await fetch(`${API_URL}/wardrobe/${apiCategory}?user_id=${user?.id}`);
        const result = await response.json();
        
        if (result.success) {
          setUploadedItems(result.data || []);
        }
      }
    } catch (error) {
      console.error('Error loading items:', error);
      setUploadedItems([]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = async (files) => {
    setUploading(true);
    const fileArray = Array.from(files);
    
    try {
      for (let i = 0; i < fileArray.length; i++) {
        const file = fileArray[i];
        
        // Update progress
        setUploadProgress(prev => [...prev, { 
          name: file.name, 
          status: 'uploading',
          step: 'Uploading to server...'
        }]);
        
        // Create FormData
        const formData = new FormData();
        formData.append('image', file);
        
        // Map tab name to API category (handle plural/singular)
        const categoryMap = {
          'accessories': 'accessory',
          'tops': 'tops',
          'bottoms': 'bottoms',
          'shoes': 'shoes',
          'outerwear': 'outerwear',
          'all': 'tops', // Default to tops if uploading from All tab
          'saved outfits': 'tops' // Default to tops if somehow uploading from saved outfits
        };
        const uploadCategory = categoryMap[selectedTab.toLowerCase()] || 'tops';
        
        console.log(`📤 Uploading to category: ${uploadCategory} (from tab: ${selectedTab})`);
        
        formData.append('category', uploadCategory);
        formData.append('user_id', user?.id);
        
        // Send to backend API
        const response = await fetch(`${API_URL}/process-clothing`, {
          method: 'POST',
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
          throw new Error(result.error || 'Upload failed');
        }
        
        console.log('✅ Processed successfully:', result.data);
        
        // Update progress
        setUploadProgress(prev => 
          prev.map(p => 
            p.name === file.name ? { ...p, status: 'completed', step: 'Complete!' } : p
          )
        );
        
        // Add to local state
        const newItem = {
          id: result.data.id,
          clean_image_url: result.data.clean_url,
          raw_image_url: result.data.raw_url,
          category: selectedTab.toLowerCase(),
          file_name: file.name,
          attributes: result.data.attributes,
          style_tags: result.data.style_tags
        };
        
        setUploadedItems(prev => [newItem, ...prev]);
      }
      
      alert('Images processed successfully! Background removed and attributes extracted. ✅');
    } catch (error) {
      console.error('Error uploading files:', error);
      alert(`Failed to process images: ${error.message}. Make sure the backend server is running.`);
    } finally {
      setUploading(false);
      setUploadProgress([]);
    }
  };

  const handleDeleteItem = async (itemId) => {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
      const response = await fetch(`${API_URL}/wardrobe/${itemId}`, {
        method: 'DELETE',
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Remove from local state
        setUploadedItems(prev => prev.filter(item => item.id !== itemId));
        alert('Item deleted successfully! ✅');
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Error deleting item:', error);
      alert('Failed to delete item');
    }
  };

  const handleDeleteOutfit = async (outfitId) => {
    if (!confirm('Are you sure you want to delete this saved outfit?')) return;

    try {
      const response = await fetch(`${API_URL}/saved-outfits/${outfitId}`, {
        method: 'DELETE',
      });
      
      const result = await response.json();
      
      if (result.success) {
        setSavedOutfits(prev => prev.filter(outfit => outfit.id !== outfitId));
        alert('Outfit deleted successfully! ✅');
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Error deleting outfit:', error);
      alert('Failed to delete outfit');
    }
  };

  const toggleFavorite = (itemId) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(itemId)) {
        newFavorites.delete(itemId);
      } else {
        newFavorites.add(itemId);
      }
      return newFavorites;
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <button 
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-full transition"
            >
              <Home className="w-5 h-5 text-gray-700" />
            </button>
            
            <h1 className="text-xl font-semibold text-gray-900">My Digital Wardrobe</h1>
            
            <div className="flex items-center space-x-2">
              <button className="p-2 hover:bg-gray-100 rounded-full transition relative">
                <Bell className="w-5 h-5 text-gray-700" />
              </button>
              
              <div className="relative">
                <button 
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="p-2 hover:bg-gray-100 rounded-full transition"
                >
                  <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-gray-700" />
                  </div>
                </button>
                
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900">
                        {user?.user_metadata?.full_name || 'User'}
                      </p>
                      <p className="text-xs text-gray-500 truncate mt-1">{user?.email}</p>
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
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Upload Area */}
        {selectedTab !== 'Saved Outfits' && (
          <div
            className={`rounded-lg p-12 mb-6 transition relative ${
              dragActive 
                ? 'bg-blue-50 border-2 border-dashed border-blue-400' 
                : 'bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200'
            } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {uploading ? (
              <div className="flex flex-col items-center">
                <Loader2 className="w-10 h-10 text-amber-600 animate-spin mb-3" />
                <p className="text-sm font-medium text-gray-700">
                  Processing your items...
                </p>
                <div className="space-y-1 mt-2">
                  {uploadProgress.map((progress, index) => (
                    <p key={index} className="text-xs text-gray-600">
                      {progress.name} - {progress.step || progress.status}
                    </p>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 mb-3">
                  <Upload className="w-8 h-8 text-amber-700" />
                </div>
                <h3 className="text-base font-semibold text-gray-800 mb-1">
                  Add New Items
                </h3>
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleFileInput}
                  className="hidden"
                  id="file-upload"
                  disabled={uploading}
                />
                <label
                  htmlFor="file-upload"
                  className="inline-block cursor-pointer text-sm text-amber-700 hover:text-amber-800 font-medium"
                >
                  Click to upload or drag and drop
                </label>
              </div>
            )}
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition flex items-center space-x-2 ${
                  selectedTab === tab
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                {tab === 'All' && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                )}
                {tab === 'Saved Outfits' && (
                  <Heart className="w-4 h-4" />
                )}
                <span>{tab}</span>
              </button>
            ))}
          </div>
          
          <div className="flex items-center space-x-2">
            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <Filter className="w-5 h-5 text-gray-700" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <SortAsc className="w-5 h-5 text-gray-700" />
            </button>
          </div>
        </div>
        {/* Content */}
        {selectedTab === 'Saved Outfits' ? (
          /* Saved Outfits View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {savedOutfits.length === 0 ? (
              <div className="col-span-full text-center py-20 bg-white rounded-xl">
                <Heart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">No saved outfits yet</p>
                <p className="text-gray-400 text-sm mt-2">Create and save outfits from the recommendations page</p>
              </div>
            ) : (
              savedOutfits.map((outfit) => (
                <div key={outfit.id} className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold text-gray-900">{outfit.occasion}</h3>
                    <button
                      onClick={() => handleDeleteOutfit(outfit.id)}
                      className="p-1.5 hover:bg-red-50 rounded-lg transition"
                    >
                      <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3">
                    {/* Top */}
                    <div>
                      <div className="aspect-square rounded-lg overflow-hidden bg-gray-50">
                        {outfit.top ? (
                          <img 
                            src={outfit.top.clean_image_url} 
                            alt="Top"
                            className="w-full h-full object-contain p-2"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <p className="text-xs text-gray-400">No top</p>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1.5 text-center">Top</p>
                    </div>

                    {/* Bottom */}
                    <div>
                      <div className="aspect-square rounded-lg overflow-hidden bg-gray-50">
                        {outfit.bottom ? (
                          <img 
                            src={outfit.bottom.clean_image_url} 
                            alt="Bottom"
                            className="w-full h-full object-contain p-2"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <p className="text-xs text-gray-400">No bottom</p>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1.5 text-center">Bottom</p>
                    </div>

                    {/* Shoes */}
                    <div>
                      <div className="aspect-square rounded-lg overflow-hidden bg-gray-50">
                        {outfit.shoes ? (
                          <img 
                            src={outfit.shoes.clean_image_url} 
                            alt="Shoes"
                            className="w-full h-full object-contain p-2"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <p className="text-xs text-gray-400">No shoes</p>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1.5 text-center">Shoes</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Items Grid */
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {uploadedItems.length === 0 ? (
              <div className="col-span-full text-center py-16 bg-white rounded-xl">
                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <p className="text-gray-500 font-medium">No items yet</p>
                <p className="text-gray-400 text-sm mt-2">Upload some photos to get started!</p>
              </div>
            ) : (
              uploadedItems.map((item) => (
                <div key={item.id} className="group relative">
                  <div className="aspect-square bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition">
                    <img
                      src={item.clean_image_url || item.image_url}
                      alt={item.file_name || "Wardrobe item"}
                      className="w-full h-full object-contain p-4"
                    />
                  </div>
                  
                  {/* Action buttons */}
                  <div className="absolute top-2 right-2 flex space-x-1 opacity-0 group-hover:opacity-100 transition">
                    <button
                      onClick={() => toggleFavorite(item.id)}
                      className={`p-2 rounded-full backdrop-blur-sm transition ${
                        favorites.has(item.id)
                          ? 'bg-red-500 text-white'
                          : 'bg-white/90 text-gray-700 hover:bg-white'
                      }`}
                    >
                      <Heart className={`w-4 h-4 ${favorites.has(item.id) ? 'fill-current' : ''}`} />
                    </button>
                    <button
                      className="p-2 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition"
                    >
                      <MoreVertical className="w-4 h-4 text-gray-700" />
                    </button>
                  </div>
                  
                  {/* Delete button - shown on menu click or always visible on hover */}
                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    className="absolute bottom-2 right-2 p-2 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 hover:bg-red-600 transition shadow-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default VirtualCloset;
