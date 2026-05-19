import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environmental variables from root .env file
load_dotenv()

# --- MODE FLAG ---
# Set to False to run live integrations against the real Gemini API
MOCK_DEV_MODE = True

# --- SYSTEM DIRECTORY PATH RESOLUTIONS ---
# Resolves cross-platform root absolute references cleanly
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_INPUT_DIR = BASE_DIR / "RawVideos"
OPTIMIZED_DIR = BASE_DIR / "OptimizedVideos"
OUTPUT_DIR = BASE_DIR

# --- EXTERNAL SERVICE INITIALIZATION ---
if not MOCK_DEV_MODE:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- SANIDBOX MOCK REPOSITORIES ---
# Fallback assets used during developer isolation validation passes
MOCK_CLIPS_DATA = [
    {
        "new_filename": "sizzling_shrimp.mp4",
        "description": "Close-up shot of garlic slices bubbling in melted butter with crisp audio sizzle.",
        "length_seconds": 15
    },
    {
        "new_filename": "dicing_onions.mp4",
        "description": "Rapid rhythm chef knife cuts reducing a whole red onion on a wood block.",
        "length_seconds": 22
    },
    {
        "new_filename": "skyline_sunset.mp4",
        "description": "Cinematic wide panning shot of the city skyline during a deep golden sunset.",
        "length_seconds": 45
    }
]

MOCK_STRATEGIC_BLUEPRINT = (
    "# MOCK EDITING STRATEGY\n\n"
    "## 1. HOOK\n"
    "Start with sizzling_shrimp.mp4 immediately to grab acoustic attention.\n\n"
    "## 2. BODY\n"
    "Cut to dicing_onions.mp4 matching cut pacing with the knife impacts.\n\n"
    "## 3. OUTRO\n"
    "Fade out over the wide canvas of skyline_sunset.mp4 with ambient underlying tracks."
)