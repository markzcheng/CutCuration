🎬 CutCuration: Automated Video Pipeline Studio
CutCuration is an asynchronous AI-augmented video preprocessing and strategic timeline compilation engine. It discovers raw media assets locally, optimizes their structural bitrates via non-blocking worker threads, handles remote streaming analysis passes using Google's Gemini 2.5 Flash model, and outputs structured production artifacts (report.csv and summary.txt).

🏗️ Architectural Matrix & System Design
                     ┌───────────────────────────────────────────────┐
                     │            HTML5 / JS WORKSTATION             │
                     └───────┬───────────────────────────────▲───────┘
                             │                               │
       1. POST Configuration │                               │ 4. Persistent Live
          Kickoff Request     │                               │    Log Streams (SSE)
                             ▼                               │
                     ┌───────────────────────────────────────┴───────┐
                     │          FASTAPI ROUTER ENGINE        │
                     └───────┬───────────────────────────────▲───────┘
                             │                               │
       2. Offload Non-       │                               │ 3. Pipeline Metrics
          Blocking Task      ▼                               │    & Content Payload
                     ┌───────────────────────────────────────┴───────┐
                     │      CORE WORKER SERVICES PROCESSING NODE     │
                     └───────┬───────────────────────────────▲───────┘
                             │                               │
            FFmpeg Command   │ Local File                    │ Cloud Analysis Passes
            Proxy Down-      ▼ System IO                     ▼ & Structural Token Returns
                     ┌───────────────┐               ┌───────────────┐
                     │ OptimizedDirs │               │ Gemini API    │
                     └───────────────┘               └───────────────┘
The system enforces a clean separation of concerns by splitting up complex routines into specialized modular helper components:

backend/app/config.py: Centralizes operational environments, handles path parsing via native pathlib matrices across differing platforms, validations, and encapsulates isolated development sandbox mock parameters.

backend/app/services.py: Houses core concurrent thread pool operations. Coordinates local video optimizations using FFmpeg, handles Gemini file transfers, and handles generative payload requests.

backend/app/main.py: Serves as a thin, highly structured application layer. It configures backend middleware, maps system prompts, reads endpoint queries, and runs persistent Server-Sent Events (SSE) data streams.

⚡ Concurrency & Resource Orchestration Guardrails
To run multi-file video processing efficiently over limited compute resource parameters without causing loop hangs, the system implements two critical design patterns:

1. The Non-Blocking Thread Executor Pattern
Video structural optimizations call heavy background processes (FFmpeg). Running these tasks directly inside an asynchronous web loop freezes execution frames completely. To preserve system responsiveness, tasks are wrapped inside an isolated thread executor context:

Python
loop = asyncio.get_running_loop()
optimized_path = await loop.run_in_executor(None, compress_video_for_analysis, video_path, OPTIMIZED_DIR)
This offloads intense CPU video encoding pipelines to dedicated background worker threads, allowing the main loop to continue managing network requests without a hitch.

2. Async Semaphore Rate Limiting
Google's Gemini API free tier enforces a protective limit of 5 Requests Per Minute (RPM). Pushing extensive parallel asset clusters concurrently under load causes remote servers to return 429 Resource Exhausted exceptions. We isolate this risk using an explicit concurrency token bucket:

Python
async with semaphore:  # Hard-capped at 2 concurrent worker operations
    # Upload, wait for cloud preprocessing, and request content analysis safely...
This lets the pipeline maximize background bandwidth while maintaining a safe operating threshold below rate-limit margins.

🛠️ Quickstart & Development Installation
1. Environmental Configuration
Clone the repository and create a standard configuration environment profile file named .env inside your project root workspace:

Code snippet
GEMINI_API_KEY=your_live_google_generative_ai_token_here
2. Toggle Operational Sandbox Environment Modes
You can validate full front-to-back application state changes instantly without spending your API tokens by tweaking the MOCK_DEV_MODE toggle found inside backend/app/config.py:

Python
# True  = Runs pipeline simulation using isolated offline sample data elements
# False = Activates real-time FFmpeg processing, file uploads, and live Gemini API requests
MOCK_DEV_MODE = True
3. Launching the Backend API
Install project dependency modules and start the local Uvicorn ASGI server instance using terminal execution configurations:

Bash
cd backend/app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
4. Opening the Workstation Interface
The dashboard uses vanilla JavaScript and standard CSS. Serve the root workspace folder using any basic local web server extension (such as Live Server in VS Code), or simply open the index.html file directly within your web browser.

📊 Standard System Output Schemas
When a processing run concludes successfully, two core analytical ledger files are written to your root directory:

Report Data Registry (report.csv)
Tracks optimized runtime naming rules, asset content summaries, and calculated duration boundaries:

Code snippet
original_filename,new_filename,description,length_seconds
video_A.mp4,optimized_video_A_15s.mp4,Close-up tracking shot of garlic slices bubbling in butter with high sizzle frequencies.,15
Compilation Blueprint Strategy (summary.txt)
Contains full contextual assembly guidelines compiled directly by Gemini matching your specific content profile strategies:

Markdown
# VIDEO EDITING STRATEGY BLUEPRINT
## 1. HOOK COMPONENT
* Clip: optimized_video_A_15s.mp4 (0:00 - 0:05)
* Action: Establish immediate viewer engagement using high-macro audio pan transitions...