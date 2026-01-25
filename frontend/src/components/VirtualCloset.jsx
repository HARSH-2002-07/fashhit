import React, { useState, useEffect } from 'react';
import { Home, User, Sparkles, Loader2, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const VirtualCloset = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState('Tops');
  const [uploadedItems, setUploadedItems] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState([]);

  const tabs = ['Tops', 'Bottoms', 'Shoes'];

  // Load items from backend API
  useEffect(() => {
    loadItems();
  }, [selectedTab]);

  const loadItems = async () => {
    try {
      const response = await fetch(`${API_URL}/wardrobe/${selectedTab.toLowerCase()}`);
      const result = await response.json();
      
      if (result.success) {
        setUploadedItems(result.data || []);
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
        formData.append('category', selectedTab.toLowerCase());
        
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
          
          <h1 className="text-xl font-semibold text-gray-800">Virtual Closet</h1>
          
          <div className="flex items-center space-x-2">
            <button 
              onClick={() => navigate('/outfit')}
              className="p-2 hover:bg-blue-50 rounded-lg transition group"
              title="Get Outfit Recommendations"
            >
              <Sparkles className="w-5 h-5 text-blue-500 group-hover:text-blue-600" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <User className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Upload Area */}
        <div
          className={`border-2 border-dashed rounded-xl p-12 text-center mb-8 transition relative ${
            dragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 bg-white'
          } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {uploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <h3 className="text-lg font-medium text-gray-700 mb-2">
                Processing Image...
              </h3>
              <div className="space-y-1">
                {uploadProgress.map((progress, index) => (
                  <p key={index} className="text-sm text-gray-600">
                    {progress.name} - {progress.step || progress.status}
                  </p>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-4">
                Removing background & extracting attributes...
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 mb-4 flex items-center justify-center">
                <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-700 mb-2">
                Drag & Drop Photos Here
              </h3>
              <p className="text-sm text-gray-500 mb-4">or Click to Upload</p>
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
                className="cursor-pointer bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-full text-sm font-medium transition"
              >
                Browse Files
              </label>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mb-6 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab)}
              className={`px-6 py-3 text-sm font-medium transition border-b-2 ${
                selectedTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Items Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {uploadedItems.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p className="text-gray-500">No items in your {selectedTab.toLowerCase()} yet.</p>
              <p className="text-gray-400 text-sm mt-2">Upload some photos to get started!</p>
            </div>
          ) : (
            uploadedItems.map((item) => (
              <div key={item.id} className="aspect-square bg-white rounded-lg border border-gray-200 overflow-hidden relative group">
                <img
                  src={item.clean_image_url || item.image_url}
                  alt={item.file_name || "Wardrobe item"}
                  className="w-full h-full object-cover"
                />
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
};

export default VirtualCloset;
