import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, Trash2, AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const FeedbackHistory = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [feedbackList, setFeedbackList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchFeedback = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/feedback/${user.id}`);
      const result = await response.json();
      
      if (result.success) {
        setFeedbackList(result.data || []);
      } else {
        setError('Failed to load feedback history');
      }
    } catch (err) {
      setError('Error loading feedback: ' + err.message);
      console.error('Error fetching feedback:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (feedbackId) => {
    if (!window.confirm('Are you sure you want to delete this feedback?')) return;
    
    setDeletingId(feedbackId);
    
    try {
      const response = await fetch(`${API_URL}/feedback/${feedbackId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        setFeedbackList(prev => prev.filter(f => f.id !== feedbackId));
      } else {
        alert('Failed to delete feedback');
      }
    } catch (err) {
      alert('Error deleting feedback: ' + err.message);
      console.error('Error deleting feedback:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('⚠️ Are you sure you want to delete ALL your feedback? This cannot be undone!')) return;
    
    setLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/feedback/clear/${user.id}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        setFeedbackList([]);
        alert('All feedback cleared successfully!');
      } else {
        alert('Failed to clear feedback');
      }
    } catch (err) {
      alert('Error clearing feedback: ' + err.message);
      console.error('Error clearing feedback:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, [user?.id]);

  const getItemNames = (outfitItems) => {
    if (!outfitItems || typeof outfitItems !== 'object') return [];
    
    return Object.values(outfitItems)
      .filter(item => item && item.meta)
      .map(item => item.meta.sub_category || 'Unknown Item');
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/outfit')} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Feedback History</h1>
              <p className="text-sm text-slate-600">{feedbackList.length} feedback {feedbackList.length === 1 ? 'entry' : 'entries'}</p>
            </div>
          </div>
          
          <div className="flex gap-3">
            <button onClick={fetchFeedback} disabled={loading} className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            
            {feedbackList.length > 0 && (
              <button onClick={handleClearAll} disabled={loading} className="px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-red-700 hover:bg-red-100 transition-colors flex items-center gap-2">
                <Trash2 className="w-4 h-4" />
                Clear All
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6">
        {loading && feedbackList.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 mr-2" />
            <span className="text-slate-600">Loading feedback...</span>
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <span className="text-red-700">{error}</span>
              </div>
            )}

            {feedbackList.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                <ThumbsUp className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">No feedback yet</h3>
                <p className="text-slate-600 mb-6">Start giving feedback on outfits to help personalize your recommendations!</p>
                <button onClick={() => navigate('/outfit')} className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">Generate Outfit</button>
              </div>
            ) : (
              <div className="space-y-4">
                {feedbackList.map((feedback) => {
                  const itemNames = getItemNames(feedback.outfit_items);
                  const isLike = feedback.rating === 'like';
                  
                  return (
                    <div key={feedback.id} className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <div className={`p-2 rounded-lg ${isLike ? 'bg-green-100' : 'bg-red-100'}`}>
                              {isLike ? <ThumbsUp className="w-5 h-5 text-green-600" /> : <ThumbsDown className="w-5 h-5 text-red-600" />}
                            </div>
                            
                            <div>
                              <span className={`text-sm font-semibold ${isLike ? 'text-green-700' : 'text-red-700'}`}>{isLike ? 'LIKED' : 'DISLIKED'}</span>
                              <p className="text-xs text-slate-500">{new Date(feedback.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</p>
                            </div>
                          </div>

                          {feedback.scenario && (
                            <p className="text-sm text-slate-600 mb-2"><span className="font-medium">Scenario:</span> {feedback.scenario}</p>
                          )}

                          {itemNames.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-slate-700 mb-1">Items in outfit:</p>
                              <div className="flex flex-wrap gap-2">
                                {itemNames.map((name, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded-md">{name}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <button onClick={() => handleDelete(feedback.id)} disabled={deletingId === feedback.id} className="ml-4 p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete feedback">
                          {deletingId === feedback.id ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Trash2 className="w-5 h-5" />}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default FeedbackHistory;
