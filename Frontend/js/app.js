const DISCOVERED_RAW_CLIPS = [
    { filename: "clip_A.mp4", type: "video/mp4" },
    { filename: "clip_B.mov", type: "video/quicktime" },
    { filename: "clip_C.mp4", type: "video/mp4" }
];

const CLIENT_PROMPT_MAP = {
    short_form_cooking: "Analyze raw food footage arrays. Filter assets for sharp audio cues, transient pan pops, and high macro butter bubbling frequencies. Synthesize a 15-second multi-cut sequence script tracking continuous ASMR impact markers.",
    long_form_vlog: "Parse comprehensive multi-location scene elements. Identify historical location assets, establishing framing sequences, and outdoor traveling narratives. Generate a balanced 3-pillar episodic layout storyboard structure."
};

document.addEventListener('DOMContentLoaded', () => {
    setupTabNavigation();
    renderSourceClipsStaging();
    updatePromptPreview();
});

function setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-link');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetedTabId = button.getAttribute('data-tab');
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active-content');
            });
            document.getElementById(`${targetedTabId}Tab`).classList.add('active-content');
        });
    });
}

function renderSourceClipsStaging() {
    const container = document.getElementById('videoStagingArea');
    if (!container) return;
    
    container.innerHTML = DISCOVERED_RAW_CLIPS.map(clip => `
        <div class="video-item-node animate-fade-in">
            <span class="video-icon">🎞️</span>
            <span class="video-meta-name" title="${clip.filename}">${clip.filename}</span>
            <span class="video-meta-type">${clip.type}</span>
        </div>
    `).join('');
}

function updatePromptPreview() {
    const mode = document.getElementById('sessionMode').value;
    const promptText = document.getElementById('promptText');
    if (promptText && CLIENT_PROMPT_MAP[mode]) {
        promptText.textContent = CLIENT_PROMPT_MAP[mode];
    }
}
document.getElementById('sessionMode').addEventListener('change', updatePromptPreview);

// --- PIPELINE STREAM MECHANICS ENGINE ---
document.getElementById('processBtn').addEventListener('click', function() {
    const processButton = this;
    const mode = document.getElementById('sessionMode').value;
    const statusContainer = document.getElementById('statusContainer');
    const resultsLayout = document.getElementById('resultsLayout');
    const blueprintContainer = document.getElementById('blueprintContainer');
    
    // Trigger animations and wipe placeholder text blocks
    processButton.classList.add('processing-active');
    processButton.textContent = "Processing Assets under Gemini Layer...";
    resultsLayout.classList.add('hidden');
    
    // Clear out the startup placeholder and inject the first execution log entry
    statusContainer.innerHTML = '<div class="log-line info-log">⚡ Initializing connection pipeline matrix...</div>';
    blueprintContainer.textContent = '';

    const eventSource = new EventSource(`http://127.0.0.1:8000/api/process/stream?mode=${mode}`);

    eventSource.addEventListener('info', (event) => {
        appendLog(statusContainer, event.data, 'info-log');
    });

    eventSource.addEventListener('progress', (event) => {
        appendLog(statusContainer, event.data, 'progress-log');
    });

    eventSource.addEventListener('error', (event) => {
        appendLog(statusContainer, `❌ Error: ${event.data || "Pipeline channel crash."}`, 'error-log');
        resetExecutionButtonState(processButton);
        eventSource.close();
    });

    eventSource.addEventListener('complete', (event) => {
        const payload = JSON.parse(event.data);
        appendLog(statusContainer, `🎉 Core pipeline finished processing successfully.`, 'success-log');
        
        blueprintContainer.textContent = payload.blueprint;
        generateDataPreviewsAndDownloads(payload.blueprint, payload.processed_count);
        
        resetExecutionButtonState(processButton);
        resultsLayout.classList.remove('hidden');
        eventSource.close();
    });
});

function resetExecutionButtonState(buttonElement) {
    buttonElement.classList.remove('processing-active');
    buttonElement.textContent = "Kickoff AI Curation Engine";
}

function generateDataPreviewsAndDownloads(blueprintText, count) {
    const tableBody = document.querySelector('#csvPreviewTable tbody');
    tableBody.innerHTML = ''; 
    
    let generatedCsvContent = "original_filename,new_filename,description,length_seconds\n";
    const sampleRows = [
        { orig: "clip_A.mp4", newName: "optimized_sizzling_shrimp_15s.mp4", len: "15s", desc: "Garlic slices bubbling in butter" },
        { orig: "clip_B.mov", newName: "optimized_dicing_onions_22s.mp4", len: "22s", desc: "Chef knife cuts on onion" },
        { orig: "clip_C.mp4", newName: "optimized_skyline_sunset_45s.mp4", len: "45s", desc: "Cinematic wide panning skyline" }
    ];

    const displayCount = Math.min(count || 3, sampleRows.length);

    for (let i = 0; i < displayCount; i++) {
        const item = sampleRows[i];
        const elementRow = document.createElement('tr');
        elementRow.innerHTML = `
            <td><strong>${item.orig}</strong></td>
            <td><code>${item.newName}</code></td>
            <td><span class="badge" style="background:rgba(56,189,248,0.1); color:#38bdf8;">${item.len}</span></td>
        `;
        tableBody.appendChild(elementRow);
        
        generatedCsvContent += `"${item.orig}","${item.newName}","${item.desc}",${item.len.replace('s','')}\n`;
    }

    document.getElementById('downloadCsvBtn').href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(generatedCsvContent);
    document.getElementById('downloadTxtBtn').href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(blueprintText);
}

function appendLog(container, text, className) {
    const line = document.createElement('div');
    line.className = `log-line ${className || ''}`;
    line.textContent = text;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
}