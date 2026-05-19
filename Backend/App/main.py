import os
import csv
import json
import asyncio  # Crucial for concurrency
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Import our dynamic prompts configuration
from prompts import EDITING_CONFIGS

VIDEO_INPUT_DIR = Path(__file__).resolve().parent.parent / "RawVideos"
CSV_FILENAME = "report.csv"
SUMMARY_FILENAME = "summary.txt"

# This function is now 'async' so it can run concurrently with others
async def analyze_single_video_async(video_file_path: Path, model, prompt_text: str) -> dict | None:
    """Uploads, processes, and analyzes a video file asynchronously."""
    print(f"  [Queue] Starting upload for {video_file_path.name}...")
    
    try:
        # Uploading runs synchronously in the SDK, but running it inside 
        # an async task allows other tasks to progress around it.
        video_file = genai.upload_file(path=video_file_path)
        print(f"  [Uploaded] {video_file_path.name} is now processing on Gemini servers.")
    except Exception as e:
        print(f"  [Error] Failed to upload {video_file_path.name}: {e}")
        return None

    # Wait for processing without locking up the CPU
    while video_file.state.name == "PROCESSING":
        # 'await asyncio.sleep' pauses THIS specific video's loop,
        # letting other clips upload or finish analyzing in the meantime.
        await asyncio.sleep(5) 
        video_file = genai.get_file(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        print(f"  [Error] Processing failed on Gemini's backend for {video_file_path.name}.")
        return None
    
    print(f"  [Analyzing] {video_file_path.name} is ready. Running AI evaluation...")

    try:
        # Running the content generation request
        response = model.generate_content([prompt_text, video_file], request_options={'timeout': 600})
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis_result = json.loads(json_text)
        
        # Clean up the file reference from Gemini right away
        genai.delete_file(name=video_file.name)
        analysis_result["original_filename"] = video_file_path.name
        
        # Local Rename operation right after analysis finishes
        new_name = analysis_result["new_filename"]
        if not new_name.endswith(video_file_path.suffix):
            new_name += video_file_path.suffix
            
        new_file_path = video_file_path.with_name(new_name)
        video_file_path.rename(new_file_path)
        print(f"  [Success] Renamed '{video_file_path.name}' -> '{new_name}'")
        
        return analysis_result

    except Exception as e:
        print(f"  [Error] Critical failure during analysis of {video_file_path.name}: {e}")
        # Return a fallback object so the CSV reporting structure doesn't snap
        return {
            "original_filename": video_file_path.name,
            "new_filename": "FAILED_ANALYSIS",
            "description": f"Analysis failed: {e}",
            "length_seconds": "N/A"
        }


def generate_final_summary(descriptions: list[str], model, summary_instructions: str) -> str:
    """Generates a final narrative summary edit plan (synchronous)."""
    print("\nGenerating final editing framework blueprint...", end="", flush=True)
    clips_list = "\n".join(f"- Clip {i+1}: {desc}" for i, desc in enumerate(descriptions))

    full_summary_prompt = f"""
    {summary_instructions}

    Here are the descriptions of the raw footage clips:
    {clips_list}
    """
    try:
        response = model.generate_content(full_summary_prompt)
        print("Done.")
        return response.text
    except Exception as e:
        print(f"Failed.\n    Error generating summary: {e}")
        return "Failed to generate summary."


# Main changes into an async function to orchestrate our parallel task groups
async def main_async():
    print("--- Starting Concurrent Local Gemini Content Pipeline ---")

    # Select your mode here: "short_form_cooking" or "long_form_vlog"
    SESSION_MODE = "short_form_cooking" 
    
    if SESSION_MODE not in EDITING_CONFIGS:
        raise ValueError(f"Mode '{SESSION_MODE}' is not recognized in prompts.py")
        
    active_config = EDITING_CONFIGS[SESSION_MODE]
    print(f"Active Session Mode: {SESSION_MODE.upper()}")

    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    try:
        genai.configure(api_key=gemini_api_key)
        # Using the current, optimized model path
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        print("Successfully connected to Gemini API.")
    except Exception as e:
        print(f"Error during client initialization: {e}")
        return

    video_extensions = {".mp4", ".mov", ".mkv", ".avi"}
    local_files = [f for f in VIDEO_INPUT_DIR.iterdir() if f.suffix.lower() in video_extensions]
    total_clips = len(local_files)
    
    if total_clips == 0:
        print(f"No videos found in directory: {VIDEO_INPUT_DIR.resolve()}")
        return
        
    print(f"Found {total_clips} clips locally. Packing tasks for parallel execution...\n")
    
    # -----------------------------------------------------------------
    # THE CONCURRENCY ENGINE
    # Create an independent, individual tracking task for every file found
    tasks = [
        analyze_single_video_async(file_path, model, active_config["analysis_prompt"])
        for file_path in local_files
    ]
    
    # Fire all tasks into the event loop at once and wait for them all to cross the line
    all_results = await asyncio.gather(*tasks)
    # Filter out any absolute dead drops (None values) from the final tracking arrays
    all_results = [res for res in all_results if res is not None]
    # -----------------------------------------------------------------

    # Write CSV Report
    if all_results:
        print(f"\nWriting results to {CSV_FILENAME}...")
        try:
            with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["original_filename", "new_filename", "description", "length_seconds"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)
            print("CSV report generated successfully.")
        except Exception as e:
            print(f"Error writing CSV file: {e}")

    # Generate Narrative Summary
    if all_results:
        descriptions = [res.get("description", "") for res in all_results if "description" in res]
        final_summary = generate_final_summary(descriptions, model, active_config["summary_prompt"])
        try:
            with open(SUMMARY_FILENAME, "w", encoding="utf-8") as f:
                f.write(final_summary)
            print(f"Final summary saved to {SUMMARY_FILENAME}.")
        except Exception as e:
            print(f"Error writing summary file: {e}")

    print("\n--- Parallel Pipeline Workflow Complete ---")


if __name__ == "__main__":
    # Bootstraps the Python file execution straight into an async runtime loop
    asyncio.run(main_async())