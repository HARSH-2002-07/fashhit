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

@app.route('/api/recommend-outfit', methods=['POST'])
def recommend_outfit():
    """
    Generate outfit recommendation using AI planner with neuro-symbolic reasoning
    Expects: { "query": "casual office meeting", "user_id": "uuid" }
    Returns: { "outfit": { "Top": {...}, "Bottom": {...}, "Footwear": {...} } }
    """
    try:
        data = request.json
        user_query = data.get('query', 'casual everyday outfit')
        user_id = data.get('user_id')  # Optional: filter by user
        
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
        
        # Try to use the sophisticated ProPlanner with neuro-symbolic reasoning
        try:
            from planner import ProPlanner
            from store import WardrobeStore
            import tempfile
            import shutil
            
            print("🧠 Initializing neuro-symbolic planner...")
            
            # Create a temporary data directory structure for the planner
            temp_dir = tempfile.mkdtemp()
            json_dir = os.path.join(temp_dir, "json")
            os.makedirs(json_dir, exist_ok=True)
            
            # Convert Supabase data to the format expected by WardrobeStore
            # Map database categories to ontology categories
            category_map = {
                'tops': 'Top',
                'bottoms': 'Bottom',
                'shoes': 'Footwear'
            }
            
            has_embeddings = False
            for item in wardrobe_items:
                # Transform database format to planner format
                planner_item = {
                    'id': item['id'],
                    'meta': {
                        'category': category_map.get(item['category'], item['category']),
                        'sub_category': item.get('attributes', {}).get('sub_category', 'Unknown'),
                        'primary_color': item.get('attributes', {}).get('primary_color', 'black'),
                        'primary_color_hex': item.get('attributes', {}).get('primary_color_hex', '#000000'),
                        'formality': item.get('attributes', {}).get('formality', 'Casual'),
                        'pattern': item.get('attributes', {}).get('pattern', 'Solid'),
                        'season': item.get('attributes', {}).get('seasonality', 'All-Season'),
                    },
                    'raw_image_url': item['raw_image_url'],
                    'clean_image_url': item['clean_image_url'],
                }
                
                # Check if we have embeddings (vector data)
                # Embeddings should be stored in a separate column or we need to generate them
                # For now, check if the item has valid vector data
                if 'embedding' in item and item['embedding'] and len(item['embedding']) > 0:
                    planner_item['embedding'] = item['embedding']
                    has_embeddings = True
                else:
                    # No embedding available - planner won't be able to do vector search
                    planner_item['embedding'] = []
                
                # Save to temporary JSON file
                json_path = os.path.join(json_dir, f"{item['id']}.json")
                with open(json_path, 'w') as f:
                    json.dump(planner_item, f)
            
            if not has_embeddings:
                print("⚠️ No embeddings found in wardrobe items. ProPlanner requires embeddings.")
                raise Exception("Embeddings not available - using fallback method")
            
            # Initialize store and planner
            store = WardrobeStore(data_dir=temp_dir)
            planner = ProPlanner(store=store)
            
            # Generate outfit using neuro-symbolic reasoning
            outfit_plan = planner.plan(user_query=user_query, template_name="basic")
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if not outfit_plan:
                raise Exception("Planner could not generate a valid outfit combination")
            
            # Convert outfit plan back to API format
            # Map Category enum values back to database format for frontend
            reverse_category_map = {
                'Top': 'tops',
                'Bottom': 'bottoms',
                'Footwear': 'shoes'
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
            
            print(f"✅ Outfit generated successfully using neuro-symbolic reasoning")
            
            return jsonify({
                'success': True,
                'outfit': outfit_response,
                'query': user_query,
                'method': 'neuro-symbolic'
            }), 200
            
        except Exception as planner_error:
            print(f"⚠️ ProPlanner failed: {str(planner_error)}")
            print("⚠️ Falling back to rule-based selection with color matching")
            
            # Enhanced Fallback: Use color matching without importing planner
            # Define color matching function locally to avoid PyTorch import
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
                    neutral_colors = ['black', 'white', 'brown', 'grey', 'gray', 'beige']
                    neutral_shoes = [s for s in shoes 
                                   if s.get('attributes', {}).get('primary_color', '').lower() in neutral_colors]
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
                    'note': f'Using simple selection (All advanced methods failed)'
                }), 200
            
    except Exception as e:
        print(f"❌ Error generating outfit: {str(e)}")
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
