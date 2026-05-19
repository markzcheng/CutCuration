import os
import csv
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import google.generativeai as genai
from dotenv import load_dotenv

# =====================================================================
# 🛠️ DEVELOPER CONFIGURATION MATRIX
# =====================================================================
MOCK_DEV_MODE = True  # Toggle to FALSE to reactivate live Gemini execution pipelines
# =====================================================================

load_dotenv()
if not MOCK_DEV_MODE:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

from prompts import EDITING_CONFIGS
from preprocess import compress_video_for_analysis

app = FastAPI(title="CutCuration Streaming Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_INPUT_DIR = Path(__file__).resolve().parent.parent / "RawVideos"
OPTIMIZED_DIR = Path(__file__).resolve().parent.parent / "OptimizedVideos"
OUTPUT_DIR = Path(__file__).resolve().parent.parent

# Mock Data Payload Configuration Definition
MOCK_CLIPS_DATA = [
    {
        "new_filename": "sizzling_garlic_butter_shrimp_15sec.mp4",
        "description": "Extreme close-up shot of garlic slices bubbling rapidly in melted butter with high-frequency acoustic sizzle.",
        "length_seconds": 15
    },
    {
        "new_filename": "dicing_red_onions_speedrun_22sec.mp4",
        "description": "Rhythmic, rapid chef knife strokes reducing a whole red onion into uniform fine dice against a wooden block surface.",
        "length_seconds": 22
    },
    {
        "new_filename": "boston_skyline_sunset_pan_45sec.mp4",
        "description": "Cinematic wide panning sequence capturing the Prudential Tower silhouetted against a deep amber and purple sunset gradient.",
        "length_seconds": 45
    }
]

MOCK_STRATEGIC_BLUEPRINT = """# MOCK EDITING BLUEPRINT STRATEGY (DEV MODE ACTIVE)

## 1. THE HOOK (0:00 - 0:03)
Start immediately with `sizzling_garlic_butter_shrimp_15sec.mp4`. Introduce the high-frequency ASMR sizzling noise within the first fraction of a second to anchor scrolling viewer attention immediately.

## 2. THE RHYTHMIC MID-SECTION (0:03 - 0:18)
Cut aggressively on the beat to `dicing_red_onions_speedrun_22sec.mp4`. Match the speed of your visual cuts to the rhythmic tapping sound of the chef's knife contact points.

## 3. THE GRAND PAYOFF & OUTRO (0:18 - 0:30)
Transition gracefully into the wide aesthetic profile of `boston_skyline_sunset_pan_45sec.mp4`. Layer an ambient atmospheric audio track underneath to finalize the cinematic slice-of-life tone."""


async def process_single_video_with_logs(video_path: Path, config: dict, log_queue: asyncio.Queue, semaphore: asyncio.Semaphore, idx: int):
    """Processes a clip natively or routes into high-fidelity mock loops depending on state configurations."""
    filename = video_path.name

    if MOCK_DEV_MODE:
        # Simulate local background pipeline pacing delays so frontend logs feel authentic
        await log_queue.put(f"⚙️ [MOCK] Starting local preprocessing simulation for {filename}")
        await asyncio.sleep(1.0)
        await log_queue.put(f"⚡ [MOCK] Compressed {filename} down to 480p @ 1 FPS proxy")
        await asyncio.sleep(0.8)
        
        await log_queue.put(f"📤 [MOCK] Uploading optimized proxy for {filename} to sandbox memory storage nodes...")
        await asyncio.sleep(1.2)
        
        await log_queue.put(f"⏳ [MOCK] Sandbox environment cluster is evaluating frame data layout for {filename}...")
        await asyncio.sleep(1.5)
        
        await log_queue.put(f"🧠 [MOCK] Generating strict structured asset metadata strings for {filename}...")
        await asyncio.sleep(0.5)

        # Select a mock data object cyclically if there are more files than array definitions
        mock_selection = MOCK_CLIPS_DATA[idx % len(MOCK_CLIPS_DATA)]
        
        await log_queue.put(f"✅ [MOCK] Finished indexing metadata for {filename}")
        return {
            "original_filename": filename,
            "new_filename": f"optimized_{filename.split('.')[0]}_{mock_selection['length_seconds']}sec.mp4",
            "description": mock_selection["description"],
            "length_seconds": mock_selection["length_seconds"],
            "status": "success"
        }

    # --- LIVE PRODUCTION SYSTEM PIPELINE ---
    async with semaphore:
        try:
            await log_queue.put(f"⚙️ Starting local preprocessing for {filename}")
            loop = asyncio.get_running_loop()
            optimized_path = await loop.run_in_executor(
                None, compress_video_for_analysis, video_path, OPTIMIZED_DIR
            )
            await log_queue.put(f"⚡ Compressed {filename} down to 480p @ 1 FPS proxy")

            await log_queue.put(f"📤 Uploading optimized proxy for {filename} to Gemini clusters...")
            uploaded_file = genai.upload_file(path=optimized_path)
            
            while uploaded_file.state.name == "PROCESSING":
                await log_queue.put(f"⏳ Gemini cluster is ingest-processing {filename}...")
                await asyncio.sleep(5)
                uploaded_file = genai.get_file(uploaded_file.name)
                
            if uploaded_file.state.name == "FAILED":
                raise Exception(f"Gemini server-side parsing failed for: {filename}")

            await log_queue.put(f"🧠 Running contextual analysis pass on {filename}...")
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            response = await model.generate_content_async([uploaded_file, config["analysis_prompt"]])
            
            genai.delete_file(uploaded_file.name)
            
            raw_text = response.text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            if raw_text.endswith("```"): raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_json = json.loads(raw_text)
            await log_queue.put(f"✅ Finished indexing metadata for {filename}")
            
            await asyncio.sleep(2)
            
            return {
                "original_filename": filename,
                "new_filename": parsed_json.get("new_filename", f"processed_{video_path.stem}.mp4"),
                "description": parsed_json.get("description", "No description generated."),
                "length_seconds": parsed_json.get("length_seconds", 0),
                "status": "success"
            }
        except Exception as e:
            await log_queue.put(f"❌ Error handling asset {video_path.name}: {str(e)}")
            return {
                "original_filename": video_path.name,
                "new_filename": f"failed_{video_path.name}",
                "description": f"Failed during pipeline operation: {str(e)}",
                "length_seconds": 0,
                "status": "error"
            }


@app.get("/api/process/stream")
async def stream_pipeline(mode: str = Query(...)):
    if mode not in EDITING_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid session mode profile identifier.")
        
    # Check physical folder state only if running in production mode
    if not MOCK_DEV_MODE and not VIDEO_INPUT_DIR.exists():
        raise HTTPException(status_code=404, detail="RawVideos ingestion directory target path is missing.")

    # Target local file system arrays
    if VIDEO_INPUT_DIR.exists():
        video_extensions = {".mp4", ".mov", ".mkv", ".avi"}
        video_files = [p for p in VIDEO_INPUT_DIR.iterdir() if p.suffix.lower() in video_extensions]
    else:
        video_files = []
    
    # If the folder is empty or non-existent in Dev Mode, simulate standard mock file loops anyway
    if not video_files and MOCK_DEV_MODE:
        video_files = [Path("sample_clip_A.mp4"), Path("sample_clip_B.mov"), Path("sample_clip_C.mp4")]
    elif not video_files:
        async def empty_generator():
            yield {"event": "error", "data": "No raw assets found inside RawVideos directory setup."}
        return EventSourceResponse(empty_generator())

    config = EDITING_CONFIGS[mode]
    shared_log_queue = asyncio.Queue()
    rate_limiter = asyncio.Semaphore(2)

    async def event_generator():
        if MOCK_DEV_MODE:
            yield {"event": "info", "data": "⚠️ NOTICE: CutCuration sandbox engine is running in MOCK_DEV_MODE."}
            yield {"event": "info", "data": "Tokens and server bandwidth usage metrics are completely paused."}
        
        yield {"event": "info", "data": f"🚀 Initializing CutCuration pipeline in operational mode: {mode}"}
        yield {"event": "info", "data": f"📂 Target task array generated: {len(video_files)} items registered."}

        # Spawn processing tasks concurrently, tracking item position index parameters
        tasks = [
            process_single_video_with_logs(video, config, shared_log_queue, rate_limiter, idx) 
            for idx, video in enumerate(video_files)
        ]
        processing_future = asyncio.gather(*tasks)

        while not processing_future.done() or not shared_log_queue.empty():
            try:
                log_message = await asyncio.wait_for(shared_log_queue.get(), timeout=0.2)
                yield {"event": "progress", "data": log_message}
                shared_log_queue.task_done()
            except asyncio.TimeoutError:
                continue

        analysis_results = processing_future.result()

        # --- ORIGINAL OUTPUT MECHANIC A: Write report.csv ---
        valid_descriptions = []
        success_count = 0
        
        csv_path = OUTPUT_DIR / "report.csv"
        try:
            with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["original_filename", "new_filename", "description", "length_seconds"])
                
                for r in analysis_results:
                    if isinstance(r, dict) and r.get("status") == "success":
                        success_count += 1
                        writer.writerow([r["original_filename"], r["new_filename"], r["description"], r["length_seconds"]])
                        valid_descriptions.append(f"File: {r['new_filename']} - Context: {r['description']}")
                        
            yield {"event": "progress", "data": f"💾 Local database artifact map successfully written to: {csv_path.name}"}
        except Exception as csv_err:
            yield {"event": "progress", "data": f"⚠️ Local report generation warning: {str(csv_err)}"}

        if not valid_descriptions:
            yield {"event": "error", "data": "Pipeline stopped: None of the video targets were successfully processed."}
            return

        # --- Compile Cumulative Summary Context ---
        yield {"event": "progress", "data": "📝 Passing cumulative context back to Gemini for strategic storyboard blueprint..."}
        
        if MOCK_DEV_MODE:
            await asyncio.sleep(2.0)  # Simulate strategic generation delay frame
            strategic_blueprint = MOCK_STRATEGIC_BLUEPRINT
        else:
            combined_context = "\n".join(valid_descriptions)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            summary_response = await model.generate_content_async([config["summary_prompt"], combined_context])
            strategic_blueprint = summary_response.text

        # --- ORIGINAL OUTPUT MECHANIC B: Write summary.txt ---
        txt_path = OUTPUT_DIR / "summary.txt"
        try:
            with open(txt_path, mode="w", encoding="utf-8") as txt_file:
                txt_file.write(strategic_blueprint)
            yield {"event": "progress", "data": f"💾 Strategic text log written successfully to: {txt_path.name}"}
        except Exception as txt_err:
            yield {"event": "progress", "data": f"⚠️ Local summary file output write warning: {str(txt_err)}"}

        # Send completion structure mapping back to HTML UI interface layout channels
        yield {
            "event": "complete",
            "data": json.dumps({
                "processed_count": success_count,
                "blueprint": strategic_blueprint
            })
        }

    return EventSourceResponse(event_generator())