# 📦 Data Migration Guide

## Overview
This guide will help you upload your existing wardrobe data (images and JSON) to Cloudinary and Supabase.

## Current Data Status
- **Raw Images**: 27 files in `my_wardrobe/raw/`
- **Clean Images**: 27 files in `my_wardrobe/data/images/`
- **JSON Metadata**: 27 files in `my_wardrobe/data/json/`

## Step 1: Create a User Account (REQUIRED)

**You currently have 0 registered users. You need to create one first!**

### Option A: Create Account via Website (Recommended)
1. Make sure both servers are running:
   ```bash
   # Terminal 1 - Backend
   python backend/app.py
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. Open http://localhost:5173 in your browser

3. Click **"Sign In"** button in the header

4. Switch to **"Register"** tab

5. Fill in:
   - Full Name: Your Name
   - Email: your@email.com
   - Password: (minimum 6 characters)

6. Click **"Create Account"**

7. ✅ You'll see a success message (check email for confirmation if required)

### Option B: Get User ID from Existing Account
If you already have an account:

1. Sign in to http://localhost:5173

2. Open browser console (Press F12)

3. Get your user ID:
   ```javascript
   // In Console tab, paste this:
   const auth = JSON.parse(localStorage.getItem('sb-upfcstrawsynkrojorqk-auth-token'))
   console.log('User ID:', auth.user.id)
   console.log('Email:', auth.user.email)
   ```

4. Copy the User ID (it looks like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

## Step 2: Verify User Registration

Run this command to check registered users:

```bash
python backend/check_users.py
```

**Expected Output:**
```
📊 Total Users with Wardrobe Items: 0
```
(It will be 0 until you upload data)

OR to check auth users:
```bash
python backend/check_auth.py
```

## Step 3: Run Migration Script

### Option A: Automatic User Detection (Easier)

Simply run:
```bash
python backend/migrate_data.py
```

The script will:
- ✅ Automatically find your registered user
- ✅ Upload all 27 raw images to Cloudinary
- ✅ Upload all 27 clean images to Cloudinary
- ✅ Save all JSON metadata to Supabase
- ✅ Link everything to your user account

### Option B: Manual User ID (If needed)

1. Edit `backend/migrate_data.py`

2. Find these lines at the bottom (around line 200):
   ```python
   # OPTION 2: Specify user_id manually (uncomment below if needed)
   # print("Using manually specified user_id...")
   # USER_ID = "paste-your-user-id-here"  # Get this from website after signing in
   # migrate_data(user_id=USER_ID)
   ```

3. Uncomment and replace with your actual user ID:
   ```python
   # OPTION 2: Specify user_id manually (uncomment below if needed)
   print("Using manually specified user_id...")
   USER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"  # Your actual user ID
   migrate_data(user_id=USER_ID)
   ```

4. Comment out OPTION 1:
   ```python
   # OPTION 1: Let script find user automatically
   # print("Looking for existing users...")
   # migrate_data()
   ```

5. Run the script:
   ```bash
   python backend/migrate_data.py
   ```

## Step 4: Verify Upload

After migration completes, you should see:

```
🎉 Migration Complete!
   ✅ Successfully uploaded: 27 items
   ⚠️ Skipped: 0 items
   📦 Total processed: 27 files
```

Now check your wardrobe on the website:

1. Go to http://localhost:5173
2. Sign in with your account
3. Click **"Get Started - Build Your Closet"**
4. You should see all 27 items in their respective categories (Tops, Bottoms, Shoes)!

## Troubleshooting

### Issue: "No users found!"
**Solution**: Create an account first (Step 1)

### Issue: "Missing images"
**Solution**: Make sure raw and clean images have the same base filename as JSON files
- Example: `shirt1.json` should have `shirt1.jpg` (or .png) in both raw/ and clean/ folders

### Issue: "Cloudinary upload failed"
**Solution**: 
- Check `backend/.env` has correct Cloudinary credentials
- Make sure `CLOUDINARY_UPLOAD_PRESET` is set to `closet`

### Issue: "Supabase error"
**Solution**:
- Verify Supabase credentials in `backend/.env`
- Make sure `wardrobe_items` table exists (run SQL from SETUP_COMPLETE.md)

## What Gets Uploaded

For each item, the script uploads:
- ✅ **Raw Image** → Cloudinary folder: `wardrobe/raw`
- ✅ **Clean Image** → Cloudinary folder: `wardrobe/clean`
- ✅ **Metadata** → Supabase table: `wardrobe_items`

The Supabase record includes:
- `user_id` - Your user account ID
- `raw_image_url` - Cloudinary URL for original image
- `clean_image_url` - Cloudinary URL for background-removed image
- `category` - tops, bottoms, or shoes
- `attributes` - JSON with color, style, pattern, etc.
- `file_name` - Original filename

## After Migration

Once completed, you can:
1. ✅ View all items in Virtual Closet page
2. ✅ Delete items you don't want
3. ✅ Get AI outfit recommendations
4. ✅ Upload more items manually through the website

Your data is now in the cloud and accessible from anywhere! 🎉
