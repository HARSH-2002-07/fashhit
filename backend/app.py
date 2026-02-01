import os
import json
import tempfile
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from PIL import Image
import numpy as np

# Import updated processing modules
try:
    from bg_remove import ImageProcessor
    has_bg_remove = True
except ImportError:
    has_bg_remove = False
    print("⚠️ bg_remove module not available")

try:
    from json_from_clean import get_tags_with_retry, process_image_batch, init_gemini, init_fashion_clip
    has_json_processor = True
except ImportError:
    has_json_processor = False
    print("⚠️ json_from_clean module not available")

try:
    from planner import ProPlannerV7
    from store import WardrobeStore
    has_planner = True
except ImportError:
    has_planner = False
    print("⚠️ planner module not available")

try:
    from update_json import classify_attribute, ATTRIBUTES
    has_update_json = True
except ImportError:
    has_update_json = False
    print("⚠️ update_json module not available")

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

# Global instances for image processing
image_processor = None
gemini_model = None
fashion_clip = None

if has_bg_remove:
    image_processor = ImageProcessor()

if has_json_processor:
    try:
        gemini_model = init_gemini()
        fashion_clip = init_fashion_clip()
        
        # CRITICAL: Set the global variables in json_from_clean module
        # The get_tags_with_retry and process_image_batch functions use these globals
        import json_from_clean
        json_from_clean.model = gemini_model
        json_from_clean.fclip = fashion_clip
        
        print(f"✅ Gemini model initialized: {gemini_model is not None}")
        print(f"✅ FashionCLIP initialized: {fashion_clip is not None}")
    except Exception as e:
        print(f"⚠️ Failed to initialize AI models: {e}")
        import traceback
        traceback.print_exc()

# Load essentials.json (global fashion items - no user_id required)
ESSENTIALS_DATA = []
# Path relative to backend directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ESSENTIALS_FILE = os.path.join(os.path.dirname(BACKEND_DIR), 'my_wardrobe', 'data', 'essentials.json')

if os.path.exists(ESSENTIALS_FILE):
    try:
        with open(ESSENTIALS_FILE, 'r') as f:
            ESSENTIALS_DATA = json.load(f)
        print(f"🛍️ Loaded {len(ESSENTIALS_DATA)} essential fashion items")
    except Exception as e:
        print(f"⚠️ Failed to load essentials.json: {e}")
else:
    print(f"⚠️ Essentials file not found at {ESSENTIALS_FILE}")

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
            
            # Step 2: Remove background using new ImageProcessor
            print("🎨 Removing background...")
            clean_image_path = os.path.join(temp_dir, 'clean_image.png')
            pil_image = Image.open(raw_image_path)
            
            if has_bg_remove and image_processor:
                from pathlib import Path
                # Save to temp path and process
                temp_raw_path = Path(raw_image_path)
                clean_pil = image_processor.process_image(temp_raw_path)
                if clean_pil is None:
                    raise Exception("Background removal failed")
            else:
                # Fallback: just use the original image
                print("⚠️ Using original image (bg_remove not available)")
                clean_pil = pil_image
            
            clean_pil.save(clean_image_path, 'PNG')
            
            # Step 3: Upload clean image to Cloudinary
            print("☁️  Uploading clean image to Cloudinary...")
            clean_cloudinary = upload_to_cloudinary(clean_image_path, 'wardrobe/clean')
            clean_url = clean_cloudinary['url']
            clean_public_id = clean_cloudinary['public_id']
            
            # Step 4: Extract attributes with Gemini & FashionCLIP
            print("🤖 Extracting clothing attributes...")
            clean_pil_for_analysis = Image.open(clean_image_path)
            
            # Get Gemini tags using new function
            gemini_attributes = {}
            if has_json_processor and gemini_model:
                try:
                    gemini_attributes = get_tags_with_retry(clean_pil_for_analysis)
                except Exception as e:
                    print(f"⚠️ Gemini tagging failed: {e}")
                    # Provide default attributes matching ClothingMetadata structure
                    gemini_attributes = {
                        'category': category.capitalize(),
                        'sub_category': 'Unknown',
                        'primary_color': 'Black',
                        'secondary_color': None,
                        'pattern': 'Solid',
                        'material': 'Cotton',
                        'seasonality': ['All-Season'],
                        'formality': 'Casual',
                        'fit': 'Regular',
                        'occasion': ['Everyday'],
                        'style_tags': ['Classic'],
                        'layer_role': 'Base',
                        'silhouette_volume': 'Regular',
                        'pairing_bias': 0.5,
                        'length_profile': 'Standard'
                    }
            
            # Generate FashionCLIP embedding (512 dimensions)
            embedding = []
            if has_json_processor and fashion_clip:
                try:
                    from pathlib import Path
                    embeddings = process_image_batch([Path(clean_image_path)])
                    if embeddings and len(embeddings) > 0:
                        embedding = embeddings[0]
                        print(f"✅ Generated {len(embedding)}-dim embedding")
                except Exception as e:
                    print(f"⚠️ Embedding generation failed: {e}")
            
            # Step 4.5: Enhance attributes with FashionCLIP visual analysis
            if has_update_json and has_json_processor and fashion_clip:
                try:
                    print("🔍 Enhancing attributes with visual analysis...")
                    
                    # Detect Fit
                    fit = classify_attribute(fashion_clip, clean_image_path, ATTRIBUTES["fit"])
                    if gemini_attributes.get('fit') in [None, 'Regular']:
                        gemini_attributes['fit'] = fit
                    
                    # Detect Cut/Length (for relevant categories)
                    if gemini_attributes.get('category') in ['Top', 'Bottom', 'Outerwear']:
                        cut = classify_attribute(fashion_clip, clean_image_path, ATTRIBUTES["cut"])
                        # Normalize cut
                        if cut == "Ankle":
                            cut = "Cropped"
                        gemini_attributes['length_profile'] = cut
                        gemini_attributes['cut'] = cut
                    
                    # Detect Occasion
                    occasion = classify_attribute(fashion_clip, clean_image_path, ATTRIBUTES["occasion"])
                    if occasion and occasion not in gemini_attributes.get('occasion', []):
                        if 'occasion' not in gemini_attributes or not isinstance(gemini_attributes['occasion'], list):
                            gemini_attributes['occasion'] = []
                        gemini_attributes['occasion'].append(occasion)
                    
                    print(f"✅ Enhanced: fit={fit}, cut={gemini_attributes.get('cut', 'N/A')}, occasion={occasion}")
                except Exception as e:
                    print(f"⚠️ Attribute enhancement failed: {e}")
            
            # Close PIL images to release file handles
            pil_image.close()
            clean_pil.close()
            clean_pil_for_analysis.close()
            
            # Step 5: Save to Supabase with embedding
            print("💾 Saving to Supabase...")
            user_id = request.form.get('user_id')  # Get user_id from form data
            
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User ID required'
                }), 400
            
            # Debug: Print category value
            print(f"🔍 DEBUG - Category from form: '{category}' (type: {type(category).__name__})")
            print(f"🔍 DEBUG - Allowed categories: ['tops', 'bottoms', 'shoes', 'outerwear', 'one_piece', 'accessory']")
            
            wardrobe_data = {
                'user_id': user_id,
                'raw_image_url': raw_url,
                'raw_cloudinary_id': raw_public_id,
                'clean_image_url': clean_url,
                'clean_cloudinary_id': clean_public_id,
                'category': category,
                'file_name': image_file.filename,
                'attributes': gemini_attributes,
                'embedding': embedding if embedding else None
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
                    'embedding_dimensions': len(embedding) if embedding else 0
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
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID required'
            }), 400
        
        query = supabase.table('wardrobe_items').select('*').eq('category', category).eq('user_id', user_id)
        
        result = query.order('created_at', desc=True).execute()
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

@app.route('/api/essentials', methods=['GET'])
def get_essentials():
    """Get global essential fashion items (no user_id required)"""
    return jsonify({
        'success': True,
        'data': ESSENTIALS_DATA,
        'count': len(ESSENTIALS_DATA)
    }), 200

@app.route('/api/wardrobe/<item_id>', methods=['DELETE'])
def delete_wardrobe_item(item_id):
    """Delete a wardrobe item from database and Cloudinary"""
    try:
        # First, get the item to retrieve Cloudinary IDs
        item_result = supabase.table('wardrobe_items').select('*').eq('id', item_id).execute()
        
        if not item_result.data:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        item = item_result.data[0]
        
        # Delete from Cloudinary (both raw and clean images)
        deleted_images = []
        if item.get('raw_cloudinary_id'):
            try:
                url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/destroy"
                data = {
                    'public_id': item['raw_cloudinary_id'],
                    'api_key': CLOUDINARY_API_KEY,
                    'api_secret': CLOUDINARY_API_SECRET
                }
                response = requests.post(url, data=data)
                if response.status_code == 200:
                    deleted_images.append('raw')
            except Exception as e:
                print(f"⚠️ Failed to delete raw image from Cloudinary: {e}")
        
        if item.get('clean_cloudinary_id'):
            try:
                url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/destroy"
                data = {
                    'public_id': item['clean_cloudinary_id'],
                    'api_key': CLOUDINARY_API_KEY,
                    'api_secret': CLOUDINARY_API_SECRET
                }
                response = requests.post(url, data=data)
                if response.status_code == 200:
                    deleted_images.append('clean')
            except Exception as e:
                print(f"⚠️ Failed to delete clean image from Cloudinary: {e}")
        
        # Delete from Supabase
        result = supabase.table('wardrobe_items').delete().eq('id', item_id).execute()
        
        print(f"🗑️ Deleted item {item_id} (Cloudinary: {deleted_images})")
        
        return jsonify({
            'success': True,
            'message': 'Item deleted successfully from database and Cloudinary',
            'deleted_images': deleted_images
        }), 200
    except Exception as e:
        print(f"❌ Error deleting item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-outfit', methods=['POST'])
def save_outfit():
    """Save a complete outfit with occasion to database"""
    try:
        data = request.json
        user_id = data.get('user_id')
        outfit = data.get('outfit', {})
        occasion = data.get('occasion', 'Casual')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID required'
            }), 400
        
        # Prepare outfit data with all 6 categories
        outfit_data = {
            'user_id': user_id,
            'occasion': occasion,
            'top_id': outfit.get('tops', {}).get('id') if outfit.get('tops') else None,
            'bottom_id': outfit.get('bottoms', {}).get('id') if outfit.get('bottoms') else None,
            'shoes_id': outfit.get('shoes', {}).get('id') if outfit.get('shoes') else None,
            'outerwear_id': outfit.get('outerwear', {}).get('id') if outfit.get('outerwear') else None,
            'one_piece_id': outfit.get('one_piece', {}).get('id') if outfit.get('one_piece') else None,
            'accessory_id': outfit.get('accessory', {}).get('id') if outfit.get('accessory') else None,
            'created_at': data.get('created_at')
        }
        
        # Save to saved_outfits table
        result = supabase.table('saved_outfits').insert(outfit_data).execute()
        
        print(f"✅ Outfit saved for user {user_id}: {occasion}")
        
        return jsonify({
            'success': True,
            'message': 'Outfit saved successfully',
            'data': result.data
        }), 200
        
    except Exception as e:
        print(f"❌ Error saving outfit: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/saved-outfits', methods=['GET'])
def get_saved_outfits():
    """Get all saved outfits for a user with full wardrobe item details"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID required'
            }), 400
        
        # Get saved outfits
        outfits_result = supabase.table('saved_outfits').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        
        # Enrich with wardrobe item details for all 6 categories
        enriched_outfits = []
        for outfit in outfits_result.data:
            enriched = {
                'id': outfit['id'],
                'occasion': outfit['occasion'],
                'created_at': outfit['created_at'],
                'top': None,
                'bottom': None,
                'shoes': None,
                'outerwear': None,
                'one_piece': None,
                'accessory': None
            }
            
            # Fetch top details
            if outfit.get('top_id'):
                top_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['top_id']).execute()
                if top_result.data:
                    enriched['top'] = top_result.data[0]
            
            # Fetch bottom details
            if outfit.get('bottom_id'):
                bottom_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['bottom_id']).execute()
                if bottom_result.data:
                    enriched['bottom'] = bottom_result.data[0]
            
            # Fetch shoes details
            if outfit.get('shoes_id'):
                shoes_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['shoes_id']).execute()
                if shoes_result.data:
                    enriched['shoes'] = shoes_result.data[0]
            
            # Fetch outerwear details
            if outfit.get('outerwear_id'):
                outerwear_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['outerwear_id']).execute()
                if outerwear_result.data:
                    enriched['outerwear'] = outerwear_result.data[0]
            
            # Fetch one_piece details
            if outfit.get('one_piece_id'):
                one_piece_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['one_piece_id']).execute()
                if one_piece_result.data:
                    enriched['one_piece'] = one_piece_result.data[0]
            
            # Fetch accessory details
            if outfit.get('accessory_id'):
                accessory_result = supabase.table('wardrobe_items').select('*').eq('id', outfit['accessory_id']).execute()
                if accessory_result.data:
                    enriched['accessory'] = accessory_result.data[0]
            
            enriched_outfits.append(enriched)
        
        print(f"📋 Found {len(enriched_outfits)} saved outfits for user {user_id}")
        
        return jsonify({
            'success': True,
            'data': enriched_outfits
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching saved outfits: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/saved-outfits/<outfit_id>', methods=['DELETE'])
def delete_saved_outfit(outfit_id):
    """Delete a saved outfit"""
    try:
        result = supabase.table('saved_outfits').delete().eq('id', outfit_id).execute()
        
        print(f"🗑️ Deleted saved outfit: {outfit_id}")
        
        return jsonify({
            'success': True,
            'message': 'Saved outfit deleted successfully'
        }), 200
    except Exception as e:
        print(f"❌ Error deleting saved outfit: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/recommend-outfit', methods=['POST'])
def recommend_outfit():
    """
    Generate outfit recommendation using ProPlannerV7 with shopping recommendations
    Expects: { "query": "casual office meeting", "user_id": "uuid" }
    Returns: { "outfit": {...}, "shopping_tip": "..." }
    """
    try:
        data = request.json
        user_query = data.get('query', 'casual everyday outfit')
        user_id = data.get('user_id')  # Optional: filter by user
        manual_weather = data.get('weather')  # Optional: override weather
        
        print(f"🎨 Generating outfit recommendation for: '{user_query}'")
        
        # Fetch user's wardrobe items from Supabase
        query_builder = supabase.table('wardrobe_items').select('*')
        if user_id:
            query_builder = query_builder.eq('user_id', user_id)
        
        wardrobe_result = query_builder.execute()
        wardrobe_items = wardrobe_result.data
        
        if not wardrobe_items or len(wardrobe_items) == 0:
            return jsonify({
                'success': False,
                'error': 'No items found in wardrobe. Please upload some clothes first.'
            }), 400
        
        print(f"📦 Found {len(wardrobe_items)} items in wardrobe")
        
        # Try to use ProPlannerV7 with shopping engine
        if has_planner:
            try:
                import tempfile
                import shutil
                
                print("🧠 Initializing ProPlannerV7 with shopping engine...")
                
                # Create a temporary data directory structure for the planner
                temp_dir = tempfile.mkdtemp()
                json_dir = os.path.join(temp_dir, "json")
                os.makedirs(json_dir, exist_ok=True)
                
                # Copy essentials.json to temp directory for ShoppingEngine
                essentials_path = os.path.join(temp_dir, "essentials.json")
                if ESSENTIALS_DATA:
                    with open(essentials_path, 'w') as f:
                        json.dump(ESSENTIALS_DATA, f)
                
                # Convert Supabase data to the format expected by WardrobeStore
                # Map database categories to ontology categories
                category_map = {
                    'tops': 'Top',
                    'bottoms': 'Bottom',
                    'shoes': 'Footwear',
                    'outerwear': 'Outerwear',
                    'one_piece': 'One-Piece',
                    'accessory': 'Accessory'
                }
                
                has_embeddings = False
                for item in wardrobe_items:
                    # Determine actual category (check if it's outerwear in attributes)
                    item_category = item['category']
                    attributes = item.get('attributes', {})
                    
                    # If category in attributes is Outerwear, use that instead
                    if attributes.get('category', '').lower() == 'outerwear':
                        item_category = 'outerwear'
                    
                    # Transform database format to planner format with all new fields
                    planner_item = {
                        'id': item['id'],
                        'meta': {
                            'category': category_map.get(item_category, 'Top'),
                            'sub_category': attributes.get('sub_category', 'Unknown'),
                            'primary_color': attributes.get('primary_color', 'Black'),
                            'secondary_color': attributes.get('secondary_color'),
                            'formality': attributes.get('formality', 'Casual'),
                            'pattern': attributes.get('pattern', 'Solid'),
                            'fit': attributes.get('fit', 'Regular'),
                            'material': attributes.get('material', 'Cotton'),
                            'seasonality': attributes.get('seasonality', ['All-Season']),
                            'occasion': attributes.get('occasion', ['Everyday']),
                            'style_tags': attributes.get('style_tags', []),
                            'layer_role': attributes.get('layer_role', 'Base'),
                            'silhouette_volume': attributes.get('silhouette_volume', 'Regular'),
                            'pairing_bias': attributes.get('pairing_bias', 0.5),
                            'length_profile': attributes.get('length_profile', 'Standard')
                        },
                        'paths': {
                            'raw': item['raw_image_url'],
                            'clean': item['clean_image_url']
                        }
                    }
                    
                    # Check if we have embeddings (vector data)
                    if 'embedding' in item and item['embedding'] and len(item['embedding']) > 0:
                        planner_item['embedding'] = item['embedding']
                        has_embeddings = True
                    else:
                        planner_item['embedding'] = []
                    
                    # Save to temporary JSON file
                    json_path = os.path.join(json_dir, f"{item['id']}.json")
                    with open(json_path, 'w') as f:
                        json.dump(planner_item, f)
                
                if not has_embeddings:
                    print("⚠️ No embeddings found in wardrobe items. ProPlanner requires embeddings.")
                    raise Exception("Embeddings not available - using fallback method")
                
                # Initialize store and ProPlannerV7
                store = WardrobeStore(data_dir=temp_dir)
                planner = ProPlannerV7(store=store)
                
                # Generate outfit using neuro-symbolic reasoning with shopping
                planner_result = planner.plan(user_query=user_query, manual_weather=manual_weather)
                
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Extract result (handle both old dict format and new metadata format)
                if isinstance(planner_result, dict) and 'outfit' in planner_result:
                    outfit_plan = planner_result['outfit']
                    confidence_data = planner_result.get('confidence', {})
                    weather_info = planner_result.get('weather', {})
                    shopping_tip = planner_result.get('shopping_tip')
                    template_used = planner_result.get('template', 'unknown')
                else:
                    # Old format - just outfit dict
                    outfit_plan = planner_result
                    confidence_data = {}
                    weather_info = {}
                    shopping_tip = None
                    template_used = 'unknown'
                
                if not outfit_plan:
                    raise Exception("Planner could not generate a valid outfit combination")
                
                # Convert outfit plan back to API format
                reverse_category_map = {
                    'Top': 'tops',
                    'Bottom': 'bottoms',
                    'Footwear': 'shoes',
                    'Outerwear': 'outerwear',
                    'One-Piece': 'one_piece',
                    'Accessory': 'accessory'
                }
                
                outfit_response = {}
                for category, item in outfit_plan.items():
                    api_category = reverse_category_map.get(category, category.lower())
                    
                    # Find the original database item to include all fields
                    db_item = next((db_i for db_i in wardrobe_items if db_i['id'] == item['id']), None)
                    if db_item:
                        outfit_response[api_category] = db_item
                    else:
                        outfit_response[api_category] = None
                
                # Debug: Print what we're sending to frontend
                print(f"🔍 DEBUG - Outfit Response Categories:")
                for cat, item in outfit_response.items():
                    if item:
                        attrs = item.get('attributes', {})
                        print(f"  {cat}: {attrs.get('sub_category', 'N/A')} (ID: {item['id'][:8]}...)")
                
                print(f"✅ Outfit generated using ProPlannerV7 with shopping engine")
                
                # If weather_info is empty, get it from LiveWeather
                if not weather_info:
                    from planner import LiveWeather
                    weather_info = LiveWeather.get_weather()
                    if manual_weather:
                        weather_info['condition'] = manual_weather
                
                # Extract confidence score
                confidence_score = confidence_data.get('score', 0.0)
                confidence_percentage = int(confidence_score * 100)
                
                return jsonify({
                    'success': True,
                    'outfit': outfit_response,
                    'query': user_query,
                    'method': 'ProPlannerV7',
                    'shopping_tip': shopping_tip,
                    'weather': weather_info,
                    'confidence': {
                        'score': confidence_score,
                        'percentage': confidence_percentage,
                        'breakdown': confidence_data.get('breakdown', {})
                    },
                    'template': template_used
                }), 200
                
            except Exception as planner_error:
                print(f"⚠️ ProPlannerV7 failed: {str(planner_error)}")
                import traceback
                traceback.print_exc()
        
        # Fallback to simple rule-based method
        print("⚠️ Using rule-based fallback method")
        
        # Enhanced Fallback: Use color matching
        def simple_color_score(color_a: str, color_b: str) -> float:
            """Simple color matching without HSV calculations"""
            neutral_colors = ['black', 'white', 'grey', 'gray', 'beige', 'brown', 'navy', 'khaki']
            
            # Both neutral = good match
            if any(c in str(color_a).lower() for c in neutral_colors) and \
               any(c in str(color_b).lower() for c in neutral_colors):
                return 0.8
            
            # One neutral = safe match
            if any(c in str(color_a).lower() for c in neutral_colors) or \
               any(c in str(color_b).lower() for c in neutral_colors):
                return 0.6
            
            # Same color = good match
            if str(color_a).lower() == str(color_b).lower():
                return 0.7
            
            # Default
            return 0.3
        
        try:
            outfit = {}
            selected_items = {}
            
            # Step 1: Select top (most formal or first available)
            tops = [item for item in wardrobe_items if item['category'] == 'tops']
            if tops:
                # Sort by formality: Formal > Smart Casual > Casual
                formality_order = {'Formal': 3, 'Smart Casual': 2, 'Smart-Casual': 2, 'Casual': 1, 'Lounge': 0}
                tops_sorted = sorted(tops, 
                    key=lambda x: formality_order.get(x.get('attributes', {}).get('formality', 'Casual'), 1), 
                    reverse=True)
                outfit['tops'] = tops_sorted[0]
                selected_items['top'] = tops_sorted[0]
            else:
                outfit['tops'] = None
            
            # Step 2: Select bottom that matches the top
            bottoms = [item for item in wardrobe_items if item['category'] == 'bottoms']
            if bottoms and 'top' in selected_items:
                top = selected_items['top']
                # Score each bottom based on color harmony
                scored_bottoms = []
                for bottom in bottoms:
                    top_color = top.get('attributes', {}).get('primary_color', 'black')
                    bottom_color = bottom.get('attributes', {}).get('primary_color', 'black')
                    color_score = simple_color_score(top_color, bottom_color)
                    scored_bottoms.append((bottom, color_score))
                
                # Pick best color match
                scored_bottoms.sort(key=lambda x: x[1], reverse=True)
                outfit['bottoms'] = scored_bottoms[0][0] if scored_bottoms else bottoms[0]
                selected_items['bottom'] = outfit['bottoms']
            elif bottoms:
                outfit['bottoms'] = bottoms[0]
            else:
                outfit['bottoms'] = None
            
            # Step 3: Select shoes (prefer neutral colors)
            shoes = [item for item in wardrobe_items if item['category'] == 'shoes']
            if shoes:
                # Prefer neutral shoes (black, white, brown)
                neutral_colors_list = ['black', 'white', 'brown', 'grey', 'gray', 'beige']
                neutral_shoes = [s for s in shoes 
                               if s.get('attributes', {}).get('primary_color', '').lower() in neutral_colors_list]
                outfit['shoes'] = neutral_shoes[0] if neutral_shoes else shoes[0]
            else:
                outfit['shoes'] = None
            
            print(f"✅ Outfit generated using rule-based color matching")
            
            return jsonify({
                'success': True,
                'outfit': outfit,
                'query': user_query,
                'method': 'rule-based-fallback'
            }), 200
            
        except Exception as fallback_error:
            print(f"⚠️ Rule-based fallback also failed: {str(fallback_error)}")
            
            # Simple random selection as last resort
            import random
            outfit = {}
            for category_name in ['tops', 'bottoms', 'shoes']:
                category_items = [item for item in wardrobe_items if item['category'] == category_name]
                if category_items:
                    outfit[category_name] = random.choice(category_items)
                else:
                    outfit[category_name] = None
            
            return jsonify({
                'success': True,
                'outfit': outfit,
                'query': user_query,
                'method': 'random-fallback',
                'note': 'Using simple selection (All advanced methods failed)'
            }), 200
    except Exception as e:
        print(f"❌ Error generating outfit: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/swap-item', methods=['POST'])
def swap_item():
    """Swap a single item in an existing outfit while keeping others locked."""
    try:
        data = request.json
        user_id = data.get('user_id')
        slot_to_swap = data.get('slot')  # e.g., "shoes", "tops", "bottoms"
        current_outfit = data.get('current_outfit', {})
        
        if not user_id or not slot_to_swap:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        print(f"🔄 Swapping {slot_to_swap} for user {user_id}")
        
        # Get user's wardrobe items for the slot category
        response = supabase.table('wardrobe_items')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('category', slot_to_swap)\
            .execute()
        
        available_items = response.data
        
        if not available_items:
            return jsonify({
                'success': False,
                'error': f'No {slot_to_swap} items found in wardrobe'
            }), 404
        
        # Filter out the current item from the slot
        current_item_id = current_outfit.get(slot_to_swap, {}).get('id')
        if current_item_id:
            available_items = [item for item in available_items if item['id'] != current_item_id]
        
        if not available_items:
            return jsonify({
                'success': False,
                'error': f'No alternative {slot_to_swap} items available'
            }), 404
        
        # Simple selection: pick a random alternative
        import random
        new_item = random.choice(available_items)
        
        # Update the outfit
        current_outfit[slot_to_swap] = new_item
        
        print(f"✅ Swapped {slot_to_swap}: {new_item.get('sub_category', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'outfit': current_outfit,
            'swapped_slot': slot_to_swap,
            'new_item': new_item
        }), 200
            
    except Exception as e:
        print(f"❌ Error swapping item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/feedback', methods=['POST'])
def save_feedback():
    """Save user feedback on outfit recommendations for reinforcement learning."""
    try:
        data = request.json
        user_id = data.get('user_id')
        rating = data.get('rating')  # 'like' or 'dislike'
        outfit_items = data.get('outfit_items', {})
        scenario = data.get('scenario', '')
        
        if not user_id or not rating:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Create outfit_id from item IDs for tracking
        item_ids = sorted([str(item.get('id', '')) for item in outfit_items.values() if item])
        outfit_id = '-'.join(item_ids)
        
        # Save to Supabase
        feedback_data = {
            'user_id': user_id,
            'outfit_id': outfit_id,
            'rating': rating,
            'outfit_items': outfit_items,
            'scenario': scenario,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('outfit_feedback').insert(feedback_data).execute()
        
        print(f"📊 Feedback saved: {rating} for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback saved successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Error saving feedback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Fashion AI Backend Server...")
    print(f"📍 Server will run on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
