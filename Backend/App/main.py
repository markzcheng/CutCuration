import os
import csv
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

# Load environmental configs and keys
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Ingest your decoupled instructions and local FFmpeg module
from prompts import EDITING_CONFIGS
from preprocess import compress_video_for_analysis

app = FastAPI(title="CutCuration Backend API")

# Allow your local web dashboard to communicate with this API layer seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core local directory path state matrix configurations
VIDEO_INPUT_DIR = Path(__file__).resolve().parent.parent / "RawVideos"
OPTIMIZED_DIR = Path(__file__).resolve().parent.parent / "OptimizedVideos"
OUTPUT_DIR = Path(__file__).resolve().parent.parent

class ProcessRequest(BaseModel):
    mode: str  # Matches keys: "short_form_cooking" or "long_form_vlog"

async def process_single_video(video_path: Path, config: dict):
    """
    Handles local FFmpeg compression step, uploads the lightweight proxy to Gemini, 
    waits for processing to finish asynchronously, and returns isolated structured JSON data.
    """
    try:
        # 1. Execute local compression step off the main thread to protect FastAPI loop
        loop = asyncio.get_running_loop()
        optimized_path = await loop.run_in_executor(
            None, compress_video_for_analysis, video_path, OPTIMIZED_DIR
        )

        # 2. Upload the optimized proxy layout rather than the heavy raw file
        print(f"Uploading optimized {optimized_path.name} to Gemini clusters...")
        uploaded_file = genai.upload_file(path=optimized_path)
        
        # 3. Asynchronous Polling Loop running parallel checks every 5 seconds
        while uploaded_file.state.name == "PROCESSING":
            print(f"Waiting for {optimized_path.name} asset processing analysis...")
            await asyncio.sleep(5)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise Exception(f"Gemini processing failure exception on asset: {optimized_path.name}")

        # 4. Request Analysis using the strict JSON prompt configurations
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        response = await model.generate_content_async([uploaded_file, config["analysis_prompt"]])
        
        # Immediate cloud storage cleanup pass to keep things secure and tidy
        genai.delete_file(uploaded_file.name)
        
        # Clean up Markdown ticks if the model returns them around our raw JSON
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        # Parse data structures safely to confirm compliance
        parsed_json = json.loads(raw_text)
        
        return {
            "original_filename": video_path.name,
            "new_filename": parsed_json.get("new_filename", f"processed_{video_path.stem}.mp4"),
            "description": parsed_json.get("description", "No description generated."),
            "length_seconds": parsed_json.get("length_seconds", 0),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error handling clip processing on {video_path.name}: {str(e)}")
        return {
            "original_filename": video_path.name,
            "new_filename": f"failed_{video_path.name}",
            "description": f"Failed during pipeline operation: {str(e)}",
            "length_seconds": 0,
            "status": "error"
        }

@app.post("/api/process")
async def process_pipeline(payload: ProcessRequest):
    if payload.mode not in EDITING_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid session mode string identifier.")
        
    if not VIDEO_INPUT_DIR.exists():
        raise HTTPException(status_code=404, detail="RawVideos ingestion directory target path is missing.")

    # Target local file system arrays
    video_extensions = {".mp4", ".mov", ".mkv", ".avi"}
    video_files = [p for p in VIDEO_INPUT_DIR.iterdir() if p.suffix.lower() in video_extensions]
    
    if not video_files:
        return {"message": "No source videos found inside RawVideos directory setup.", "results": []}

    config = EDITING_CONFIGS[payload.mode]
    
    # Fire off parallel async processing across all your targeted items concurrently
    tasks = [process_single_video(video, config) for video in video_files]
    analysis_results = await asyncio.gather(*tasks)

    # --- ORIGINAL OUTPUT MECHANIC A: Write report.csv ---
    csv_path = OUTPUT_DIR / "report.csv"
    try:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            # Write structured headings match
            writer.writerow(["original_filename", "new_filename", "description", "length_seconds"])
            for row in analysis_results:
                if row["status"] == "success":
                    writer.writerow([
                        row["original_filename"],
                        row["new_filename"],
                        row["description"],
                        row["length_seconds"]
                    ])
        print(f"Successfully generated local database artifact map: {csv_path.name}")
    except Exception as csv_err:
        print(f"Failed to compile report.csv engine files: {str(csv_err)}")

    # --- Compile Cumulative Summary Context Matrix ---
    valid_descriptions = [
        f"File: {r['new_filename']} - Context: {r['description']}" 
        for r in analysis_results if r["status"] == "success"
    ]
    combined_context = "\n".join(valid_descriptions)
    
    # Request strategic structural blueprint summary from Gemini clusters
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    summary_response = await model.generate_content_async([config["summary_prompt"], combined_context])
    strategic_blueprint = summary_response.text

    # --- ORIGINAL OUTPUT MECHANIC B: Write summary.txt ---
    txt_path = OUTPUT_DIR / "summary.txt"
    try:
        with open(txt_path, mode="w", encoding="utf-8") as txt_file:
            txt_file.write(strategic_blueprint)
        print(f"Successfully generated editing blueprint draft: {txt_path.name}")
    except Exception as txt_err:
        print(f"Failed to write physical summary.txt blueprint draft: {str(txt_err)}")

    # Return unified response to display on your HTML dashboard UI interface
    return {
        "mode_executed": payload.mode,
        "individual_clips": [r for r in analysis_results if r["status"] == "success"],
        "strategic_blueprint": strategic_blueprint
    }