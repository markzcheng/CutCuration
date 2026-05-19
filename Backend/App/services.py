import json
import asyncio
from pathlib import Path
import google.generativeai as genai

from config import MOCK_DEV_MODE, OPTIMIZED_DIR, MOCK_CLIPS_DATA
from preprocess import compress_video_for_analysis

async def process_single_video_with_logs(
    video_path: Path, 
    config: dict, 
    log_queue: asyncio.Queue, 
    semaphore: asyncio.Semaphore, 
    idx: int
) -> dict:
    """
    Orchestrates ingestion tracking pipeline for a single media asset file.
    
    Manages down-sampling execution loops, asset staging updates, cloud ingestion,
    and returns parsed schema maps describing analytical video metadata attributes.
    """
    filename = video_path.name
    
    # -------------------------------------------------------------
    # PATH A: SANDBOX EXECUTION (MOCK DEV MODE)
    # -------------------------------------------------------------
    if MOCK_DEV_MODE:
        await log_queue.put(f"⚙️ [MOCK] Preprocessing {filename}")
        await asyncio.sleep(0.5)
        await log_queue.put(f"⚡ [MOCK] Compressed {filename} down to 480p @ 1 FPS")
        await asyncio.sleep(0.5)
        await log_queue.put(f"📤 [MOCK] Uploading {filename} to sandbox...")
        await asyncio.sleep(0.5)
        await log_queue.put(f"🧠 [MOCK] Running analysis on {filename}...")
        await asyncio.sleep(0.5)
        
        # Pull round-robin assignments from mock data matrix safely
        mock_meta = MOCK_CLIPS_DATA[idx % len(MOCK_CLIPS_DATA)]
        await log_queue.put(f"✅ [MOCK] Indexed metadata for {filename}")
        
        return {
            "original_filename": filename,
            "new_filename": f"optimized_{filename.split('.')[0]}_{mock_meta['length_seconds']}s.mp4",
            "description": mock_meta["description"],
            "length_seconds": mock_meta["length_seconds"],
            "status": "success"
        }
    
    # -------------------------------------------------------------
    # PATH B: PRODUCTION PIPELINE (LIVE GEMINI EXECUTION)
    # -------------------------------------------------------------
    async with semaphore:
        try:
            await log_queue.put(f"⚙️ Preprocessing {filename}")
            
            # Delegate heavy structural video down-sampling to a non-blocking thread pool worker
            loop = asyncio.get_running_loop()
            opt_path = await loop.run_in_executor(
                None, 
                compress_video_for_analysis, 
                video_path, 
                OPTIMIZED_DIR
            )
            
            await log_queue.put(f"⚡ Compressed {filename} to 480p/1FPS")
            await log_queue.put(f"📤 Uploading {filename} to Gemini File API...")
            
            # Synchronous API upload executed under concurrent thread wrapper implicitly
            cloud_file = genai.upload_file(path=opt_path)
            
            # Poll status loop waiting for cloud video preprocessing mechanics to complete
            while cloud_file.state.name == "PROCESSING":
                await log_queue.put(f"⏳ Ingestion active for {filename}...")
                await asyncio.sleep(5)
                cloud_file = genai.get_file(cloud_file.name)
                
            if cloud_file.state.name == "FAILED":
                raise Exception("Cloud asset parse failure.")
                
            await log_queue.put(f"🧠 Running generation analysis for {filename}...")
            
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await model.generate_content_async([cloud_file, config["analysis_prompt"]])
            
            # Immediate cleanup maintenance of asset file allocation units in the cloud
            genai.delete_file(cloud_file.name)
            
            # Sanitize structural raw block returns wrapped within JSON fences securely
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            parsed_json = json.loads(raw_text.strip())
            await log_queue.put(f"✅ Finished indexing {filename}")
            await asyncio.sleep(2)
            
            return {
                "original_filename": filename,
                "new_filename": parsed_json.get("new_filename", f"proc_{video_path.stem}.mp4"),
                "description": parsed_json.get("description", ""),
                "length_seconds": parsed_json.get("length_seconds", 0),
                "status": "success"
            }
            
        except Exception as err:
            await log_queue.put(f"❌ Error on asset {filename}: {str(err)}")
            return {
                "original_filename": filename,
                "new_filename": f"failed_{filename}",
                "description": str(err),
                "length_seconds": 0,
                "status": "error"
            }