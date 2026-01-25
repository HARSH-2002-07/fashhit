# Environment Setup Guide

## Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Once created, go to Project Settings > API
3. Copy the following:
   - Project URL → `VITE_SUPABASE_URL`
   - anon/public key → `VITE_SUPABASE_ANON_KEY`

4. Create the database table by running this SQL in the SQL Editor:

```sql
-- Create wardrobe_items table
CREATE TABLE wardrobe_items (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  cloudinary_public_id TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('tops', 'bottoms', 'shoes')),
  file_name TEXT,
  width INTEGER,
  height INTEGER,
  format TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create index for faster queries
CREATE INDEX idx_wardrobe_items_user_id ON wardrobe_items(user_id);
CREATE INDEX idx_wardrobe_items_category ON wardrobe_items(category);

-- Enable Row Level Security
ALTER TABLE wardrobe_items ENABLE ROW LEVEL SECURITY;

-- Create policies (for now, allow all operations without auth for testing)
CREATE POLICY "Allow all operations for testing" ON wardrobe_items
  FOR ALL USING (true) WITH CHECK (true);

-- When you add authentication, replace the above policy with:
-- CREATE POLICY "Users can view their own items" ON wardrobe_items
--   FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert their own items" ON wardrobe_items
--   FOR INSERT WITH CHECK (auth.uid() = user_id);
-- CREATE POLICY "Users can update their own items" ON wardrobe_items
--   FOR UPDATE USING (auth.uid() = user_id);
-- CREATE POLICY "Users can delete their own items" ON wardrobe_items
--   FOR DELETE USING (auth.uid() = user_id);
```

## Cloudinary Setup

1. Go to [cloudinary.com](https://cloudinary.com) and create a free account
2. Go to Dashboard
3. Copy your Cloud Name → `VITE_CLOUDINARY_CLOUD_NAME`
4. Go to Settings > Upload
5. Scroll to "Upload presets"
6. Click "Add upload preset"
7. Set:
   - Signing Mode: `Unsigned`
   - Folder: `wardrobe` (optional)
8. Save and copy the preset name → `VITE_CLOUDINARY_UPLOAD_PRESET`

## Environment Variables

Create a `.env` file in the `frontend` directory:

```bash
cp .env.example .env
```

Then fill in your actual values in the `.env` file.

## Install Dependencies

```bash
npm install
```

## Run the Application

```bash
npm run dev
```
