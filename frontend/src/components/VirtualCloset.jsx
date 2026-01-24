import React, { useState } from 'react';
import { Home, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const VirtualCloset = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState('Tops');
  const [uploadedItems, setUploadedItems] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  const tabs = ['Tops', 'Bottoms', 'Shoes'];

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

  const handleFiles = (files) => {
    const fileArray = Array.from(files).map(file => ({
      file,
      preview: URL.createObjectURL(file),
      id: Math.random().toString(36).substr(2, 9)
    }));
    setUploadedItems(prev => [...prev, ...fileArray]);
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
          
          <button className="p-2 hover:bg-gray-100 rounded-lg transition">
            <User className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Upload Area */}
        <div
          className={`border-2 border-dashed rounded-xl p-12 text-center mb-8 transition ${
            dragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 bg-white'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
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
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer text-blue-500 hover:text-blue-600 text-sm font-medium"
            >
              Browse Files
            </label>
          </div>
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
            <>
              {/* Default placeholder items */}
              <div className="aspect-square bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                  </svg>
                  <p className="text-xs text-gray-500 mt-2">Blue T-Shirt</p>
                </div>
              </div>
              
              <div className="aspect-square bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                  </svg>
                  <p className="text-xs text-gray-500 mt-2">Gray Jeans</p>
                </div>
              </div>

              <div className="aspect-square bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto text-indigo-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z"/>
                  </svg>
                  <p className="text-xs text-gray-500 mt-2">Blue Jeans</p>
                </div>
              </div>

              <div className="aspect-square bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M22 7h-7V1H9v6H2l10 9 10-9zM3.5 17l-.5 4h18l-.5-4H3.5z"/>
                  </svg>
                  <p className="text-xs text-gray-500 mt-2">White Shoes</p>
                </div>
              </div>

              <div className="aspect-square bg-gray-200 rounded-lg border border-gray-300 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <div className="w-12 h-12 mx-auto mb-2 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400"></div>
                  </div>
                  <p className="text-xs">Processing...</p>
                </div>
              </div>
            </>
          ) : (
            uploadedItems.map((item) => (
              <div key={item.id} className="aspect-square bg-white rounded-lg border border-gray-200 overflow-hidden">
                <img
                  src={item.preview}
                  alt="Uploaded item"
                  className="w-full h-full object-cover"
                />
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
};

export default VirtualCloset;
