import os
import csv
import json
import time
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Import our new dynamic prompts
from prompts import EDITING_CONFIGS

VIDEO_INPUT_DIR = Path("./RawVideos") 
CSV_FILENAME = "report.csv"
SUMMARY_FILENAME = "summary.txt"

# 1. ADD PROMPT ARGUMENT HERE
def analyze_single_video(video_file_path: Path, model, prompt_text: str) -> dict | None:
    print(f"  Uploading {video_file_path.name} to Gemini... ", end="", flush=True)
    try:
        video_file = genai.upload_file(path=video_file_path)
        print("Done.")
    except Exception as e:
        print(f"Failed.\n    Error: {e}")
        return None

    while video_file.state.name == "PROCESSING":
        print("  Waiting for file processing...", end="\r", flush=True)
        time.sleep(2)
        video_file = genai.get_file(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        print(f"  File processing failed for {video_file_path.name}.")
        return None
    
    print("  Analyzing video content... ", end="", flush=True)

    try:
        # Use the passed-in specific prompt configuration
        response = model.generate_content([prompt_text, video_file], request_options={'timeout': 600})
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis_result = json.loads(json_text)
        print("Done.")
        genai.delete_file(name=video_file.name)
        return analysis_result
    except Exception as e:
        print(f"Failed.\n    Error during analysis: {e}")
        return None

# 2. ADD PROMPT ARGUMENT HERE
def generate_final_summary(descriptions: list[str], model, summary_instructions: str) -> str:
    print("\nGenerating final summary and edit suggestions...", end="", flush=True)
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

def main():
    print("--- Starting Local Gemini Content Pipeline ---")

    # 3. SELECT YOUR EDITING MODE HERE
    # Change this string to "long_form_vlog" when you switch sessions!
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
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
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
        
    print(f"Found {total_clips} clips locally in '{VIDEO_INPUT_DIR}'.")
    all_results = []
    
    for i, file_path in enumerate(local_files):
        print(f"\n--- Processing Local Clip {i+1} of {total_clips}: {file_path.name} ---")
        
        # 4. PASS THE DYNAMIC PROMPT TO THE FUNCTION
        result = analyze_single_video(file_path, model, active_config["analysis_prompt"])

        if result and "new_filename" in result:
            result["original_filename"] = file_path.name
            all_results.append(result)
            
            new_name = result["new_filename"]
            if not new_name.endswith(file_path.suffix):
                new_name += file_path.suffix
                
            new_file_path = file_path.with_name(new_name)
            print(f"  Renaming '{file_path.name}' to '{new_name}' locally... ", end="", flush=True)
            try:
                file_path.rename(new_file_path)
                print("Done.")
            except Exception as e:
                print(f"Failed.\n    Error renaming file: {e}")
        else:
            print(f"  Skipping rename due to analysis failure.")
            all_results.append({
                "original_filename": file_path.name,
                "new_filename": "FAILED_ANALYSIS",
                "description": "Analysis failed for this clip.",
                "length_seconds": "N/A"
            })

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

    if all_results:
        descriptions = [res.get("description", "") for res in all_results if "description" in res]
        
        # 5. PASS THE DYNAMIC SUMMARY PROMPT TO THE FUNCTION
        final_summary = generate_final_summary(descriptions, model, active_config["summary_prompt"])
        try:
            with open(SUMMARY_FILENAME, "w", encoding="utf-8") as f:
                f.write(final_summary)
            print(f"Final summary saved to {SUMMARY_FILENAME}.")
        except Exception as e:
            print(f"Error writing summary file: {e}")

    print("\n--- Workflow Complete ---")

if __name__ == "__main__":
    main()