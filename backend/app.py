import os
import json
import tempfile
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from bg_remove import clean_image_robust, session
from json_from_clean import extract_tags_gemini
try:
    from json_from_clean import generate_style_tags
except ImportError:
    generate_style_tags = None
from PIL import Image

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_UPLOAD_PRESET = os.getenv('CLOUDINARY_UPLOAD_PRESET')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

def upload_to_cloudinary(image_path, folder):
    """Upload image to Cloudinary and return the URL"""
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    
    with open(image_path, 'rb') as image_file:
        files = {'file': image_file}
        data = {
            'upload_preset': CLOUDINARY_UPLOAD_PRESET,
            'folder': folder
        }
        
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'url': result['secure_url'],
                'public_id': result['public_id']
            }
        else:
            raise Exception(f"Cloudinary upload failed: {response.text}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Backend API is running'})

@app.route('/api/process-clothing', methods=['POST'])
def process_clothing():
    """
    Main endpoint to process clothing images
    Workflow:
    1. Receive image from frontend
    2. Upload raw image to Cloudinary (wardrobe/raw)
    3. Run bg_remove.py to clean the image
    4. Upload clean image to Cloudinary (wardrobe/clean)
    5. Run json_from_clean.py to extract attributes
    6. Save everything to Supabase
    """
    try:
        # Check if image is in request
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        category = request.form.get('category', 'tops').lower()
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded image temporarily
            raw_image_path = os.path.join(temp_dir, 'raw_image.jpg')
            image_file.save(raw_image_path)
            
            print(f"📥 Processing image: {image_file.filename}")
            
            # Step 1: Upload raw image to Cloudinary
            print("☁️  Uploading raw image to Cloudinary...")
            raw_cloudinary = upload_to_cloudinary(raw_image_path, 'wardrobe/raw')
            raw_url = raw_cloudinary['url']
            raw_public_id = raw_cloudinary['public_id']
            
            # Step 2: Remove background
            print("🎨 Removing background...")
            clean_image_path = os.path.join(temp_dir, 'clean_image.png')
            pil_image = Image.open(raw_image_path)
            clean_pil = clean_image_robust(pil_image)
            clean_pil.save(clean_image_path, 'PNG')
            
            # Step 3: Upload clean image to Cloudinary
            print("☁️  Uploading clean image to Cloudinary...")
            clean_cloudinary = upload_to_cloudinary(clean_image_path, 'wardrobe/clean')
            clean_url = clean_cloudinary['url']
            clean_public_id = clean_cloudinary['public_id']
            
            # Step 4: Extract attributes with Gemini & FashionCLIP
            print("🤖 Extracting clothing attributes...")
            clean_pil_for_analysis = Image.open(clean_image_path)
            
            # Get Gemini tags
            gemini_attributes = extract_tags_gemini(clean_pil_for_analysis)
            
            # Get style tags (if function is available)
            style_tags = []
            if generate_style_tags:
                try:
                    style_tags = generate_style_tags(clean_pil_for_analysis)
                except Exception as e:
                    print(f"Style tags generation failed: {e}")
                    style_tags = []
            
            # Close PIL images to release file handles
            pil_image.close()
            clean_pil.close()
            clean_pil_for_analysis.close()
            
            # Step 5: Save to Supabase
            print("💾 Saving to Supabase...")
            wardrobe_data = {
                'raw_image_url': raw_url,
                'raw_cloudinary_id': raw_public_id,
                'clean_image_url': clean_url,
                'clean_cloudinary_id': clean_public_id,
                'category': category,
                'file_name': image_file.filename,
                'attributes': gemini_attributes,
                'style_tags': style_tags
            }
            
            # Insert into Supabase
            result = supabase.table('wardrobe_items').insert(wardrobe_data).execute()
            
            print("✅ Processing complete!")
            
            return jsonify({
                'success': True,
                'message': 'Image processed successfully',
                'data': {
                    'id': result.data[0]['id'],
                    'raw_url': raw_url,
                    'clean_url': clean_url,
                    'attributes': gemini_attributes,
                    'style_tags': style_tags
                }
            }), 200
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wardrobe/<category>', methods=['GET'])
def get_wardrobe_items(category):
    """Get all wardrobe items by category"""
    try:
        result = supabase.table('wardrobe_items').select('*').eq('category', category).order('created_at', desc=True).execute()
        return jsonify({
            'success': True,
            'data': result.data
        }), 200
    except Exception as e:
        print(f"❌ Database Error: {str(e)}")
        # If table doesn't exist or error, return empty array
        return jsonify({
            'success': True,
            'data': [],
            'message': f'Database error: {str(e)}'
        }), 200

@app.route('/api/wardrobe/<item_id>', methods=['DELETE'])
def delete_wardrobe_item(item_id):
    """Delete a wardrobe item"""
    try:
        result = supabase.table('wardrobe_items').delete().eq('id', item_id).execute()
        return jsonify({
            'success': True,
            'message': 'Item deleted successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Fashion AI Backend Server...")
    print(f"📍 Server will run on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
