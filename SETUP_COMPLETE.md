# Complete Setup Guide

## 1. Supabase Setup

### Create Database Table

Run this SQL in Supabase SQL Editor:

```sql
-- Create wardrobe_items table
CREATE TABLE wardrobe_items (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Image URLs
  raw_image_url TEXT NOT NULL,
  raw_cloudinary_id TEXT NOT NULL,
  clean_image_url TEXT NOT NULL,
  clean_cloudinary_id TEXT NOT NULL,
  
  -- Basic Info
  category TEXT NOT NULL CHECK (category IN ('tops', 'bottoms', 'shoes')),
  file_name TEXT,
  
  -- AI-extracted attributes (JSON)
  attributes JSONB,
  style_tags TEXT[],
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create indexes
CREATE INDEX idx_wardrobe_items_user_id ON wardrobe_items(user_id);
CREATE INDEX idx_wardrobe_items_category ON wardrobe_items(category);
CREATE INDEX idx_wardrobe_items_created_at ON wardrobe_items(created_at DESC);

-- Enable Row Level Security
ALTER TABLE wardrobe_items ENABLE ROW LEVEL SECURITY;

-- Create policies (temporary - allow all for testing)
CREATE POLICY "Allow all operations for testing" ON wardrobe_items
  FOR ALL USING (true) WITH CHECK (true);
```

### Get Supabase Credentials
1. Go to Project Settings > API
2. Copy **Project URL** → `SUPABASE_URL`
3. Copy **anon/public key** → `SUPABASE_KEY`

## 2. Cloudinary Setup

1. Go to https://cloudinary.com/console
2. Get **Cloud Name** → `CLOUDINARY_CLOUD_NAME`
3. Settings > Security > Access Keys
4. Get **API Key** → `CLOUDINARY_API_KEY`
5. Get **API Secret** → `CLOUDINARY_API_SECRET`
6. Settings > Upload > Upload Presets
7. Create unsigned preset → `CLOUDINARY_UPLOAD_PRESET`

## 3. Backend Setup

```bash
cd backend

# Create .env file
cp .env.example .env

# Edit .env with your credentials

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python app.py
```

Backend will run on `http://localhost:5000`

## 4. Frontend Setup

```bash
cd frontend

# Update .env with backend URL
# VITE_API_URL=http://localhost:5000/api

# Install dependencies (if not done already)
npm install

# Run frontend
npm run dev
```

Frontend will run on `http://localhost:5174` (or 5173)

## 5. Test the Complete Workflow

1. Open http://localhost:5174
2. Navigate to Virtual Closet
3. Upload a clothing image
4. Watch the magic:
   - ✅ Raw image uploaded to Cloudinary
   - ✅ Background removed automatically
   - ✅ Clean image uploaded to Cloudinary
   - ✅ AI extracts clothing attributes
   - ✅ Everything saved to Supabase

## Troubleshooting

### Backend not starting?
- Make sure Python venv is activated
- Check if all dependencies are installed
- Verify .env file has correct credentials

### Frontend can't connect?
- Make sure backend is running on port 5000
- Check VITE_API_URL in frontend/.env

### Images not processing?
- Check backend terminal for error messages
- Verify Gemini API key is correct
- Make sure Cloudinary credentials are valid

## File Structure

```
Fash-hit/
├── backend/
│   ├── app.py              ← Main Flask API
│   ├── bg_remove.py         ← Background removal
│   ├── json_from_clean.py   ← Attribute extraction
│   ├── requirements.txt     ← Python dependencies
│   └── .env                 ← Backend credentials
├── frontend/
│   ├── src/
│   │   └── components/
│   │       └── VirtualCloset.jsx  ← Updated component
│   └── .env                 ← Frontend config
└── my_wardrobe/             ← Old data (can delete after migration)
```
