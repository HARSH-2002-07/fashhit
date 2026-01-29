import os
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, List
import concurrent.futures
from PIL import Image
import google.generativeai as genai
from fashion_clip.fashion_clip import FashionCLIP
from tqdm import tqdm
import hashlib
import logging
from dataclasses import dataclass, asdict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from threading import Lock
import google.api_core.exceptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix Windows Unicode console issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # ⚠️ REPLACE ME
CLEAN_IMAGES_DIR = Path("Ideal Wardrobe/data/images")
JSON_OUTPUT_DIR = Path("Ideal Wardrobe/data/json")

# Model selection - gemini-2.5-flash-lite is BEST for free tier (10 RPM vs 5 RPM)
# ┌────────────────────────┬──────┬─────────────────────┐
# │ Model                  │ RPM  │ Processing Time     │
# ├────────────────────────┼──────┼─────────────────────┤
# │ gemini-2.5-flash-lite  │  10  │ ~3.7 min (34 items) │ ← RECOMMENDED
# │ gemini-2.5-flash       │   5  │ ~7.4 min (34 items) │
# │ gemini-3-flash         │   5  │ ~7.4 min (34 items) │
# └────────────────────────┴──────┴─────────────────────┘
GEMINI_MODEL = "gemini-2.5-flash"
REQUESTS_PER_MINUTE = 10

MAX_WORKERS = 3  # Optimal for 10 RPM
BATCH_SIZE = 16
RATE_LIMIT_DELAY = 6.5  # Seconds between requests (60s / 10 requests = 6s, +0.5s buffer)

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wardrobe_tagging.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- DATACLASS FOR TYPE SAFETY ---
@dataclass
class ClothingMetadata:
    """Structured metadata for clothing items."""
    category: str
    sub_category: str
    primary_color: str
    secondary_color: Optional[str]
    pattern: str
    material: Optional[str]
    seasonality: List[str]
    formality: str
    fit: Optional[str]
    occasion: List[str]
    style_tags: List[str]
    layer_role: str
    silhouette_volume: str
    pairing_bias: float
    length_profile: str


@dataclass
class WardrobeItem:
    """Complete wardrobe item record."""
    id: str
    timestamp: float
    image_hash: str
    meta: ClothingMetadata
    embedding: List[float]
    paths: Dict[str, str]
    processing_version: str = "2.0"

# --- INITIALIZATION ---
def init_gemini():
    """Initialize Gemini with error handling."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY must be set!")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    generation_config = {
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
        "response_mime_type": "application/json",
    }
    
    logger.info(f"Using model: {GEMINI_MODEL} (Rate limit: {REQUESTS_PER_MINUTE} RPM)")
    
    return genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config=generation_config
    )

def init_fashion_clip():
    """Initialize FashionCLIP with logging."""
    logger.info("Loading FashionCLIP model...")
    return FashionCLIP('fashion-clip')

# Global instances
model = None
fclip = None
api_lock = Lock()  # Thread-safe API access
last_api_call_time = 0

def get_image_hash(image_path: Path) -> str:
    """Generate hash of image for change detection."""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def rate_limited_api_call():
    """Enforce rate limiting between API calls."""
    global last_api_call_time
    
    with api_lock:
        current_time = time.time()
        time_since_last_call = current_time - last_api_call_time
        
        if time_since_last_call < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last_call
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        last_api_call_time = time.time()

@retry(
    stop=stop_after_attempt(5),  # Increased attempts
    wait=wait_exponential(multiplier=2, min=4, max=60),  # Longer backoff
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def get_tags_with_retry(pil_image: Image.Image) -> Dict:
    """
    Enhanced tagging with retry logic and comprehensive schema.
    """
    prompt = """
You are a professional fashion analyst AI. Analyze this clothing item with precision.

Return ONLY a JSON object (no markdown, no explanation) using this EXACT schema:

{
  "category": "<Top|Bottom|Footwear|Outerwear|Accessory|Dress|Suit>",
  "sub_category": "<specific type like 'Hoodie', 'Cargo Pants', 'Sneakers', 'Bomber Jacket'>",
  "primary_color": "<standardized color: Black|White|Navy|Grey|Beige|Brown|Red|Blue|Green|Yellow|Orange|Pink|Purple|Maroon|Olive|Cream|Tan>",
  "secondary_color": "<secondary color if exists, else null>",
  "pattern": "<Solid|Striped|Plaid|Checkered|Logo|Graphic|Camo|Floral|Polka Dot|Abstract|Tie-Dye>",
  "material": "<Cotton|Polyester|Denim|Leather|Wool|Silk|Linen|Synthetic|Blend>",
  "seasonality": "<Summer|Winter|Spring|Fall|All-Season>",
  "formality": "<Casual|Smart Casual|Business Casual|Formal|Athletic|Lounge>",
  "fit": "<Slim|Regular|Loose|Oversized|Relaxed|Athletic>",
  "occasion": ["<Everyday|Work|Sport|Party|Outdoor|Formal Event|Date|Travel>"],
  "style_tags": ["<Streetwear|Minimalist|Vintage|Athletic|Preppy|Urban|Bohemian|Classic|Modern|Techwear>",
  ]
}

CRITICAL RULES:
1. Use ONLY the exact values listed in brackets for each field
2. If unsure between two colors, choose the more dominant one
3. occasion and style_tags are arrays - provide 1-3 relevant items
4. Set secondary_color to null if item is single-color
5. Be specific with sub_category (not just "shirt" but "Oxford Shirt", "Graphic Tee", etc.)
6. Consider the actual use case, not just appearance for formality/occasion
"""
    
    try:
        # Rate limit before making API call
        rate_limited_api_call()
        
        response = model.generate_content([prompt, pil_image])
        parsed = json.loads(response.text)
        
        # Validate required fields
        required_fields = ['category', 'sub_category', 'primary_color', 'pattern', 'seasonality', 'formality']
        if not all(field in parsed for field in required_fields):
            raise ValueError(f"Missing required fields in response: {parsed}")
        
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"Raw response: {response.text[:200]}")
        raise
    except google.api_core.exceptions.ResourceExhausted as e:
        logger.warning(f"Rate limit hit, will retry with backoff: {e}")
        raise
    except Exception as e:
        logger.error(f"Tagging error: {e}")
        raise

def process_image_batch(image_paths: List[Path]) -> List[List[float]]:
    """
    Process multiple images through FashionCLIP in a single batch.
    """
    try:
        # Convert Path objects to strings, ensure they're absolute paths
        str_paths = [str(p.resolve()) for p in image_paths]
        
        embeddings = fclip.encode_images(
            str_paths,
            batch_size=BATCH_SIZE
        )
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        raise

def needs_reprocessing(json_path: Path, image_path: Path) -> bool:
    """Check if item needs reprocessing."""
    if not json_path.exists():
        return True
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        
        # Check version
        if existing.get('processing_version') != '2.0':
            return True
        
        # Check image hash
        current_hash = get_image_hash(image_path)
        if existing.get('image_hash') != current_hash:
            return True
        
        return False
        
    except Exception:
        return True

def process_single_item(args: tuple) -> Optional[Dict]:
    """
    Worker function for parallel processing.
    Returns dict with status info.
    """
    file_path, skip_existing, embeddings_cache = args
    
    try:
        # Ensure file_path is a Path object and resolve it
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        # Get absolute path to avoid doubling
        image_path = file_path.resolve()
        
        # Create output path
        base_name = image_path.stem.replace("_clean", "")
        json_path = JSON_OUTPUT_DIR / f"{base_name}.json"
        
        # Skip if already processed
        if skip_existing and json_path.exists() and not needs_reprocessing(json_path, image_path):
            return {"status": "skipped", "id": base_name}
        
        # Load image
        pil_img = Image.open(image_path).convert('RGB')
        
        # Get AI tags with retry logic
        tags_dict = get_tags_with_retry(pil_img)
        
        # Convert to structured metadata
        metadata = ClothingMetadata(
    category=normalize_category(tags_dict['category']),
    sub_category=tags_dict['sub_category'],
    primary_color=tags_dict['primary_color'],
    secondary_color=tags_dict.get('secondary_color'),
    pattern=tags_dict['pattern'],
    material=tags_dict.get('material'),
    seasonality=normalize_season(tags_dict['seasonality']),
    formality=normalize_formality(tags_dict['formality']),
    fit=tags_dict.get('fit'),
    occasion=tags_dict.get('occasion', []),
    style_tags=tags_dict.get('style_tags', []),

    # 👇 ADD THESE THREE LINES
    length_profile="Standard",
    layer_role=infer_layer_role(
        normalize_category(tags_dict['category']),
        tags_dict['sub_category']
    ),
    silhouette_volume=map_volume(tags_dict.get('fit')),
    pairing_bias=pairing_bias({
        "primary_color": tags_dict['primary_color'],
        "pattern": tags_dict['pattern'],
        "formality": normalize_formality(tags_dict['formality'])
    })
)

        
        # Get embedding from cache or compute
        if base_name in embeddings_cache:
            embedding = embeddings_cache[base_name]
        else:
            # Fallback to individual computation
            embedding = fclip.encode_images([str(image_path)], batch_size=1)[0].tolist()
        
        # Get image hash
        image_hash = get_image_hash(image_path)
        
        # Create record
        record = WardrobeItem(
            id=base_name,
            timestamp=time.time(),
            image_hash=image_hash,
            meta=metadata,
            embedding=embedding,
            paths={"clean": str(image_path)}
        )
        
        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(record), f, indent=2)
        
        logger.debug(f"Processed: {base_name}")
        return {"status": "success", "id": base_name}
        
    except Exception as e:
        logger.error(f"Failed {file_path.name if hasattr(file_path, 'name') else file_path}: {e}")
        return {"status": "failed", "id": str(file_path), "error": str(e)}

def batch_process_embeddings(files_to_process: List[Path]) -> Dict[str, List[float]]:
    """Pre-compute all embeddings in optimized batches."""
    logger.info(f"Computing embeddings for {len(files_to_process)} images in batches...")
    
    embeddings_map = {}
    
    # Process in batches
    for i in range(0, len(files_to_process), BATCH_SIZE):
        batch = files_to_process[i:i + BATCH_SIZE]
        
        try:
            batch_embeddings = process_image_batch(batch)
            
            for path, embedding in zip(batch, batch_embeddings):
                base_name = path.stem.replace("_clean", "")
                embeddings_map[base_name] = embedding
            
            logger.debug(f"Processed batch {i//BATCH_SIZE + 1}/{(len(files_to_process)-1)//BATCH_SIZE + 1}")
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Fallback to individual processing
            for path in batch:
                try:
                    abs_path = path.resolve()
                    emb = fclip.encode_images([str(abs_path)], batch_size=1)[0].tolist()
                    base_name = path.stem.replace("_clean", "")
                    embeddings_map[base_name] = emb
                except Exception as e2:
                    logger.error(f"Failed individual embedding for {path.name}: {e2}")
    
    return embeddings_map

def normalize_category(raw: str) -> str:
    mapping = {
        "Dress": "One-Piece",
        "Suit": "One-Piece",
        "Top": "Top",
        "Bottom": "Bottom",
        "Footwear": "Footwear",
        "Outerwear": "Outerwear",
        "Accessory": "Accessory"
    }
    return mapping.get(raw, "Top")  # Safe fallback

def normalize_formality(raw: str) -> str:
    if raw in ["Business Casual", "Smart Casual"]:
        return "Smart Casual"
    if raw in ["Athletic", "Lounge"]:
        return "Lounge"
    return raw

def normalize_season(raw: str) -> List[str]:
    if raw == "All-Season":
        return ["Summer", "Spring", "Fall", "Winter"]
    return [raw]

def infer_layer_role(category, sub_category):
    sc = sub_category.lower()
    if category == "Outerwear":
        return "Outer"
    if any(x in sc for x in ["hoodie", "sweater", "cardigan"]):
        return "Mid"
    if category == "Top":
        return "Base"
    return "None"

def map_volume(fit):
    if fit in ["Oversized", "Relaxed", "Loose"]:
        return "Wide"
    if fit in ["Slim", "Skinny"]:
        return "Narrow"
    return "Regular"

def pairing_bias(meta):
    score = 0.0
    if meta['primary_color'] in ["Black", "White", "Navy", "Grey"]:
        score += 0.2
    if meta.get('pattern') == "Solid":
        score += 0.2
    if meta.get('formality') == "Formal":
        score -= 0.1  # Less flexible
    return score


def generate_wardrobe_summary(json_dir: Path) -> Dict:
    """Generate analytics summary of the wardrobe."""
    json_files = list(json_dir.glob("*.json"))
    
    # Exclude summary files
    json_files = [f for f in json_files if not f.name.startswith("_")]
    
    if not json_files:
        return {}
    
    categories = {}
    colors = {}
    patterns = {}
    formality = {}
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                item = json.load(f)
            
            meta = item.get('meta', {})
            
            cat = meta.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
            color = meta.get('primary_color', 'Unknown')
            colors[color] = colors.get(color, 0) + 1
            
            pattern = meta.get('pattern', 'Unknown')
            patterns[pattern] = patterns.get(pattern, 0) + 1
            
            form = meta.get('formality', 'Unknown')
            formality[form] = formality.get(form, 0) + 1
            
        except Exception as e:
            logger.error(f"Error reading {json_file.name}: {e}")
    
    return {
        "total_items": len(json_files),
        "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
        "colors": dict(sorted(colors.items(), key=lambda x: x[1], reverse=True)),
        "patterns": dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)),
        "formality": dict(sorted(formality.items(), key=lambda x: x[1], reverse=True))
    }

def main(force_reprocess: bool = False):
    """Main processing pipeline with optimized batching and parallel processing."""
    global model, fclip, last_api_call_time
    
    # Initialize
    JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    model = init_gemini()
    fclip = init_fashion_clip()
    
    # Reset rate limiter
    last_api_call_time = 0
    
    # Discover files - use resolve() to get absolute paths
    valid_exts = {'.png', '.webp'}
    all_files = [
        f.resolve() for f in CLEAN_IMAGES_DIR.iterdir()
        if f.suffix.lower() in valid_exts and f.is_file()
    ]
    
    if not all_files:
        logger.error(f"No images found in {CLEAN_IMAGES_DIR.resolve()}")
        return
    
    logger.info(f"Found {len(all_files)} images")
    
    # Filter files that need processing
    files_to_process = []
    for f in all_files:
        base_name = f.stem.replace("_clean", "")
        json_path = JSON_OUTPUT_DIR / f"{base_name}.json"
        
        if force_reprocess or needs_reprocessing(json_path, f):
            files_to_process.append(f)
    
    logger.info(f"Processing {len(files_to_process)} items (skipping {len(all_files) - len(files_to_process)} existing)")
    
    if not files_to_process:
        logger.info("All items already processed!")
        summary = generate_wardrobe_summary(JSON_OUTPUT_DIR)
        logger.info(f"\nWardrobe Summary:\n{json.dumps(summary, indent=2)}")
        return
    
    # Estimate processing time for free tier
    estimated_minutes = (len(files_to_process) * RATE_LIMIT_DELAY) / 60
    logger.info(f"Estimated processing time: {estimated_minutes:.1f} minutes ({GEMINI_MODEL} @ {REQUESTS_PER_MINUTE} RPM)")
    
    # Pre-compute embeddings in batches
    embeddings_cache = batch_process_embeddings(files_to_process)
    
    # Process tags in parallel (but rate-limited)
    logger.info("Generating AI tags with rate limiting...")
    logger.info(f"Using {MAX_WORKERS} workers with {RATE_LIMIT_DELAY}s delay between API calls")
    
    results = {"success": [], "failed": [], "skipped": []}
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        args = [(f, not force_reprocess, embeddings_cache) for f in files_to_process]
        
        with tqdm(total=len(files_to_process), desc="Processing", unit="item") as pbar:
            futures = {executor.submit(process_single_item, arg): arg for arg in args}
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    status = result.get("status", "failed")
                    results[status].append(result.get("id", "unknown"))
                
                completed += 1
                
                # Update progress bar with current stats
                pbar.set_postfix({
                    'success': len(results['success']),
                    'failed': len(results['failed'])
                })
                pbar.update(1)
                
                # Save progress every 5 items
                if completed % 5 == 0:
                    progress_file = JSON_OUTPUT_DIR / "_progress.json"
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'completed': completed,
                            'total': len(files_to_process),
                            'success': len(results['success']),
                            'failed': len(results['failed']),
                            'timestamp': time.time()
                        }, f, indent=2)
    
    # Generate summary
    elapsed_time = time.time() - start_time
    logger.info(f"\nCompleted in {elapsed_time/60:.1f} minutes")
    logger.info(f"Successfully processed {len(results['success'])} items")
    if results['failed']:
        logger.warning(f"Failed: {len(results['failed'])} items")
        logger.warning("Failed items can be retried by running the script again")
    
    summary = generate_wardrobe_summary(JSON_OUTPUT_DIR)
    logger.info(f"\nWardrobe Summary:\n{json.dumps(summary, indent=2)}")
    
    # Save summary
    with open(JSON_OUTPUT_DIR / "_wardrobe_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    # Clean up progress file
    progress_file = JSON_OUTPUT_DIR / "_progress.json"
    if progress_file.exists():
        progress_file.unlink()

if __name__ == "__main__":
    force = "--force" in sys.argv
    main(force_reprocess=force)