import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import List
from google import genai
from google.genai import types

# Initialize the modern Google GenAI Client globally using the environment key
# Note: Ensure GEMINI_API_KEY is defined in your environment or .env file.
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

async def preprocess_video_for_tokens(input_video_path: str, output_dir: str) -> str:
    """
    CHANGE 1 IMPLEMENTATION: Aggressive Local Token Preprocessing.
    
    Down-samples a raw video file using non-blocking asynchronous sub-processes.
    Strips audio (-an), scales height to 480p, and drops sampling rate to 1 frame 
    every 2 seconds (-r 0.5). This saves up to 80% on downstream Gemini API Token usage
    and minimizes cloud file transmission times.
    """
    input_path = Path(input_video_path)
    output_path = Path(output_dir) / f"token_optimized_{input_path.name}"
    
    # Ensure our temporary processing workspace directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # FFmpeg Parameter Breakdown:
    # -y                  : Automatically overwrite output file if it exists
    # -i input_path       : Target source file string path
    # -r 0.5              : Sample rate (0.5 frames/sec = 1 frame every 2 seconds)
    # -vf "scale=-2:480"  : Locks height at 480p and keeps aspect ratio divisible by 2
    # -an                 : Strips the audio track to completely minimize file size
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-r", "0.5",
        "-vf", "scale=-2:480",
        "-an",
        str(output_path)
    ]
    
    print(f"🎬 Starting local token optimization for: {input_path.name}")
    
    # Spawn an asynchronous process so the web framework thread never gets blocked
    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Wait for completion hooks to execute safely without blocking other network requests
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_log = stderr.decode().strip()
        raise RuntimeError(f"FFmpeg pipeline crashed: {error_log}")
        
    print(f"✅ Optimization complete. Saved to proxy: {output_path.name}")
    return str(output_path)


async def get_video_duration_seconds(video_path: str) -> int:
    """Return the rounded duration of a video file in seconds, or fallback to 10."""
    loop = asyncio.get_running_loop()

    def probe_duration():
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffprobe failed")
        return result.stdout.strip()

    try:
        duration_output = await loop.run_in_executor(None, probe_duration)
        return int(float(duration_output.strip()))
    except Exception:
        return 10


def extract_json_payload(text: str) -> dict:
    """Extract the first JSON object from text and parse it."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    payload_text = match.group(0)
    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        return {}


async def wait_for_file_active(file_ref, timeout_seconds: int = 30):
    """Poll Gemini until the uploaded file reaches ACTIVE state or times out."""
    loop = asyncio.get_running_loop()

    def get_file():
        return client.files.get(name=file_ref.name)

    end_time = loop.time() + timeout_seconds
    while True:
        current_file = await loop.run_in_executor(None, get_file)
        if getattr(current_file, 'state', None) == genai.types.FileState.ACTIVE:
            return current_file
        if loop.time() >= end_time:
            raise RuntimeError(f"Uploaded file {file_ref.name} never became ACTIVE")
        await asyncio.sleep(1)


async def execute_single_pass_studio_analysis(raw_video_paths: List[str], target_strategy_prompt: str) -> str:
    """
    CHANGE 2 IMPLEMENTATION: Multi-File Single-Pass Request.
    
    Preprocesses multiple video assets, uploads them concurrently to Gemini Cloud,
    bundles their cloud object pointers into ONE single text instruction array payload,
    fires a single evaluation pass, and guarantees structural remote/local cleanup.
    """
    optimized_local_paths = []
    uploaded_cloud_references = []
    tmp_workspace_dir = "./tmp/optimized_assets"
    
    # Rate Limit Guardrail: Cap processing to 2 concurrent video encodings at a time
    semaphore = asyncio.Semaphore(2)
    
    try:
        # 1. Pipeline Run: Preprocess every raw asset file sequentially
        for raw_path in raw_video_paths:
            async with semaphore:
                optimized_file = await preprocess_video_for_tokens(raw_path, tmp_workspace_dir)
                optimized_local_paths.append(optimized_file)
                
        # 2. Upload Pass: Stream your lightweight optimized files into Gemini's cloud staging storage
        loop = asyncio.get_running_loop()
        for local_opt_path in optimized_local_paths:
            print(f"🚀 Streaming optimized asset to Gemini Cloud storage: {Path(local_opt_path).name}")
            
            # client.files.upload is a blocking I/O call; we offload it to a background thread executor
            cloud_file_ref = await loop.run_in_executor(
                None, 
                lambda p=local_opt_path: client.files.upload(file=p)
            )
            await wait_for_file_active(cloud_file_ref)
            uploaded_cloud_references.append(cloud_file_ref)
            
        # 3. System Staging Assembly: Construct contents payload holding text instructions AND multi-media pointers
        prompt_payload_contents = []
        
        # Add all cloud media references into the payload array directly
        prompt_payload_contents.extend(uploaded_cloud_references)
        
        # Inject structural instructions demanding a cross-referenced timeline blueprint
        orchestration_directive = f"""
        Context Instruction Directive:
        You are an elite automated video sequencing agent. You are being provided exactly {len(uploaded_cloud_references)} source clips.
        
        Your Goal:
        Analyze all attached visual assets. Cross-reference their visual data points simultaneously 
        to compile a unified, seamless timeline storyboard structure based on the following strategy rules:
        
        "{target_strategy_prompt}"
        
        Output Requirements:
        Deliver your final structural results as a clean markdown template tracking timestamp transitions explicitly.
        """
        prompt_payload_contents.append(orchestration_directive)
        
        print("🧠 Transmitting structural multi-file bundle down to Gemini 2.5 Flash Layer...")
        
        # Fire off your SINGLE request pass
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_payload_contents
            )
        )
        
        # Return final raw markdown text string payload back to the calling client controller
        return response.text

    finally:
        # 4. Clean-Up Operations Lifecycle: Always wipe transient files from the cloud bucket to avoid leaking data
        print("🧹 Initiating storage repository cleanup loops...")
        loop = asyncio.get_running_loop()
        
        for cloud_ref in uploaded_cloud_references:
            try:
                # Remove remote staging files
                await loop.run_in_executor(None, lambda r=cloud_ref: client.files.delete(name=r.name))
                print(f"Deleted remote tracking cloud file asset: {cloud_ref.name}")
            except Exception as clean_err:
                print(f"Non-critical cleanup failure tracking cloud resource node: {clean_err}")
                
        # Scrub local transient optimized filesystem proxy clips to preserve host disk space
        for local_opt_path in optimized_local_paths:
            if os.path.exists(local_opt_path):
                try:
                    os.remove(local_opt_path)
                    print(f"Cleaned local workspace file: {Path(local_opt_path).name}")
                except Exception as file_err:
                    print(f"Failed to clear local file {local_opt_path}: {file_err}")


async def process_single_video_with_logs(file_path, config, communication_queue, semaphore, idx: int, mock_mode: bool = True):
    """
    Process a single video clip and return a structured result.

    Uses live Gemini inference to produce a content-aware description when mock_mode is False.
    """
    filename = Path(file_path).name if not isinstance(file_path, str) else Path(file_path).name
    await communication_queue.put(f"[{idx}] Started processing {filename}")
    optimized_local_path = None
    uploaded_file = None

    try:
        async with semaphore:
            if mock_mode:
                await asyncio.sleep(0.5)
                new_filename = f"processed_{filename}"
                description = f"Auto-generated description for {filename} using config {config.get('name', 'default') if isinstance(config, dict) else getattr(config, 'get', lambda k, d=None: d)('name', 'default')}"
                length_seconds = 10
            else:
                optimized_local_path = await preprocess_video_for_tokens(file_path, "./tmp/description_assets")
                await communication_queue.put(f"[{idx}] Uploaded optimized clip for Gemini analysis: {Path(optimized_local_path).name}")

                loop = asyncio.get_running_loop()
                uploaded_file = await loop.run_in_executor(
                    None,
                    lambda path=optimized_local_path: client.files.upload(file=path)
                )
                await wait_for_file_active(uploaded_file)

                await communication_queue.put(f"[{idx}] Gemini cloud staging ready for {filename}")
                prompt_text = config.get("analysis_prompt") if isinstance(config, dict) else getattr(config, "analysis_prompt", "")
                prompt_text = prompt_text or "Analyze the attached video and return a single JSON object with keys new_filename, description, length_seconds."
                prompt_text = prompt_text + "\n\nThe attached clip should be analyzed for actions, ingredients, and editing relevance. Respond only with the JSON object."

                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[uploaded_file, prompt_text]
                    )
                )

                raw_text = getattr(response, 'text', '')
                parsed = extract_json_payload(raw_text)

                new_filename = parsed.get("new_filename", f"processed_{filename}")
                description = parsed.get("description", f"Auto-generated description for {filename} using config {config.get('name', 'default') if isinstance(config, dict) else getattr(config, 'get', lambda k, d=None: d)('name', 'default')}")
                length_seconds = int(parsed.get("length_seconds", await get_video_duration_seconds(optimized_local_path)))

            await communication_queue.put(f"[{idx}] Finished processing {filename}")

            return {
                "status": "success",
                "original_filename": filename,
                "new_filename": new_filename,
                "description": description,
                "length_seconds": length_seconds,
            }
    except Exception as err:
        await communication_queue.put(f"[{idx}] Error processing {file_path}: {err}")
        return {"status": "failed", "original_filename": str(file_path)}
    finally:
        if uploaded_file is not None:
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda ref=uploaded_file: client.files.delete(name=ref.name)
                )
            except Exception:
                pass
        if optimized_local_path and os.path.exists(optimized_local_path):
            try:
                os.remove(optimized_local_path)
            except Exception:
                pass