import subprocess
import shutil
from pathlib import Path

def check_ffmpeg_installed():
    """Verifies that ffmpeg is available on the local system path."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "System error: 'ffmpeg' dependency not found on your system path. "
            "Please install ffmpeg before running the pipeline."
        )

def compress_video_for_analysis(input_path: Path, output_dir: Path) -> Path:
    """
    Downscales a single video asset to 480p resolution and a strict 1 FPS frame rate.
    Preserves Gemini API token quotas.
    """
    check_ffmpeg_installed()
    
    # Ensure optimized target directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define clean path for the lightweight target
    output_path = output_dir / f"optimized_{input_path.stem}.mp4"
    
    # Cache optimization check: don't process again if already done
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"Using cached proxy asset: {output_path.name}")
        return output_path

    print(f"Compresing asset {input_path.name} -> 480p @ 1 FPS...")
    
    # Core ffmpeg command line instruction array:
    # -vf "fps=1,scale=-2:480" scales height to 480 while keeping ratio divisible by 2
    # -an completely strips audio track to drop token payloads even further
    cmd = [
        "ffmpeg",
        "-y",                       # Overwrite output file if it exists
        "-i", str(input_path),      # Source input track path
        "-vf", "fps=1,scale=-2:480",# Video scale filter chain configurations
        "-c:v", "libx264",          # Safe H.264 video codec allocation profile
        "-crf", "28",               # Lower quality encoding weight to drop file dimensions
        "-preset", "faster",        # Rapid CPU pass preset rule
        "-an",                      # Strip audio track arrays to optimize payload metrics
        str(output_path)            # Final compressed target location path destination
    ]
    
    # Execute structural system sub-process arrays
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg Error output logs:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg pipeline crashed handling processing routines on: {input_path.name}")
        
    return output_path