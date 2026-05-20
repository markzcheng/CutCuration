import csv
import json
import asyncio
import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import google.generativeai as genai

from config import MOCK_DEV_MODE, VIDEO_INPUT_DIR, OUTPUT_DIR, MOCK_STRATEGIC_BLUEPRINT
from services import process_single_video_with_logs, execute_single_pass_studio_analysis
from prompts import EDITING_CONFIGS

app = FastAPI(title="Video Analytics Generation Engine")

# Configure broad access middleware layer properties safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/process/stream")
async def stream_pipeline(
    mode: str = Query(...),
    mock_mode: bool = Query(MOCK_DEV_MODE)
):
    """
    Main entrypoint SSE Endpoint providing live analytics logging streams.
    
    Gathers targeted storage items, constructs internal thread loops, executes
    asynchronous pipeline tasks, updates files, and pushes structural updates.
    """
    # 1. Validation checks against inputs and parameters
    if mode not in EDITING_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid session mode profile identifier.")
        
    if not mock_mode and not VIDEO_INPUT_DIR.exists():
        raise HTTPException(status_code=404, detail="Ingestion target path missing.")
        
    # 2. Identify and gather media files
    video_files = []
    if VIDEO_INPUT_DIR.exists():
        video_files = [
            file_path for file_path in VIDEO_INPUT_DIR.iterdir() 
            if file_path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}
        ]
        
    # Inject mock file mappings if environment targets are operating in simulation parameters
    if not video_files and mock_mode:
        video_files = [Path("clip_A.mp4"), Path("clip_B.mov"), Path("clip_C.mp4")]
    elif not video_files:
        async def fallback_error_stream():
            yield {"event": "error", "data": "No raw assets discovered."}
        return EventSourceResponse(fallback_error_stream())
        
    # 3. Setup core pipeline components
    active_config = EDITING_CONFIGS[mode]
    communication_queue = asyncio.Queue()
    concurrency_semaphore = asyncio.Semaphore(2)  # Caps concurrent generation limits smoothly
    
    async def pipeline_event_generator():
        if MOCK_DEV_MODE:
            yield {"event": "info", "data": "⚠️ MOCK_DEV_MODE active. Cloud token tracking suspended."}
            
        yield {
            "event": "info", 
            "data": f"🚀 Inverting pipeline execution matrix for mode: {mode} across {len(video_files)} tasks."
        }
        
        # Gather execution tasks concurrently across the file cluster list
        worker_tasks = [
            process_single_video_with_logs(file, active_config, communication_queue, concurrency_semaphore, idx, mock_mode=mock_mode)
            for idx, file in enumerate(video_files)
        ]
        async_gather_handle = asyncio.gather(*worker_tasks)
        
        # 4. Active streaming engine monitoring loop execution
        while not async_gather_handle.done() or not communication_queue.empty():
            try:
                log_message = await asyncio.wait_for(communication_queue.get(), timeout=0.2)
                yield {"event": "progress", "data": log_message}
                communication_queue.task_done()
            except asyncio.TimeoutError:
                continue
                
        # Extract response mapping lists directly from processing handles
        task_results = async_gather_handle.result()
        valid_descriptions = []
        successful_count = 0
        
        # 5. Flush results out into flat structural CSV outputs
        with open(OUTPUT_DIR / "report.csv", "w", newline="", encoding="utf-8") as target_csv:
            csv_writer = csv.writer(target_csv)
            csv_writer.writerow(["original_filename", "new_filename", "description", "length_seconds"])
            
            for item in task_results:
                if isinstance(item, dict) and item.get("status") == "success":
                    successful_count += 1
                    csv_writer.writerow([
                        item["original_filename"], 
                        item["new_filename"], 
                        item["description"], 
                        item["length_seconds"]
                    ])
                    valid_descriptions.append(f"File: {item['new_filename']} - Context: {item['description']}")
                    
        yield {"event": "progress", "data": "💾 Saved database artifact schema mappings locally to report.csv"}
        
        if not valid_descriptions:
            yield {"event": "error", "data": "Pipeline closed: zero successful updates."}
            return
            
        yield {"event": "progress", "data": "📝 Requesting layout strategy framework matrix pass..."}
        
        # 6. Structural Synthesis Engine Processing Sequence
        if mock_mode:
            await asyncio.sleep(1)
            strategic_blueprint = MOCK_STRATEGIC_BLUEPRINT
        else:
            generative_model = genai.GenerativeModel("gemini-2.5-flash")
            combined_context_payload = "\n".join(valid_descriptions)
            prompt_inputs = [active_config["summary_prompt"], combined_context_payload]
            
            gemini_response = await generative_model.generate_content_async(prompt_inputs)
            strategic_blueprint = gemini_response.text
            
        # Write compile logging strategy output document to file
        with open(OUTPUT_DIR / "summary.txt", "w", encoding="utf-8") as summary_file:
            summary_file.write(strategic_blueprint)
            
        yield {"event": "progress", "data": "💾 Saved strategic compilation log layout to summary.txt"}
        
        # Dispatch completion payload structure safely mapped as JSON string metrics
        yield {
            "event": "complete", 
            "data": json.dumps({"processed_count": successful_count, "blueprint": strategic_blueprint})
        }

    return EventSourceResponse(pipeline_event_generator())


def _guess_video_type(file_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(file_path.name)
    return mime_type or 'video/mp4'

@app.get('/api/videos')
async def list_raw_videos(mock_mode: bool = Query(MOCK_DEV_MODE)):
    if VIDEO_INPUT_DIR.exists():
        raw_files = sorted(
            [f for f in VIDEO_INPUT_DIR.iterdir() if f.suffix.lower() in {'.mp4', '.mov', '.mkv', '.avi'}]
        )
        if raw_files:
            return [
                {"filename": video.name, "type": _guess_video_type(video)}
                for video in raw_files
            ]
        if mock_mode:
            return [
                {"filename": "clip_A.mp4", "type": "video/mp4"},
                {"filename": "clip_B.mov", "type": "video/quicktime"},
                {"filename": "clip_C.mp4", "type": "video/mp4"}
            ]
        raise HTTPException(status_code=404, detail="No raw assets discovered in RawVideos.")
    if mock_mode:
        return [
            {"filename": "clip_A.mp4", "type": "video/mp4"},
            {"filename": "clip_B.mov", "type": "video/quicktime"},
            {"filename": "clip_C.mp4", "type": "video/mp4"}
        ]
    raise HTTPException(status_code=404, detail="RawVideos folder not found.")

@app.post("/api/process/batch")
async def process_video_batch(strategy_mode: str = Query(...)):
    # 1. Target the files your workspace found
    video_batch = ["./RawVideos/clip_A.mp4", "./RawVideos/clip_B.mov"]
    
    # 2. Get the prompt text map based on strategy selection
    strategy_prompt = "Your short-form or long-form prompt requirements..."
    
    # 3. Fire the single-pass architecture
    markdown_blueprint = await execute_single_pass_studio_analysis(video_batch, strategy_prompt)
    
    return {"status": "success", "blueprint": markdown_blueprint}