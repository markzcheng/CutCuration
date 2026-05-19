// Local client configuration map of the active system prompts for clarity 
const CLIENT_PROMPT_MAP = {
    short_form_cooking: "Analyze raw food footage arrays. Filter assets for sharp audio cues, transient pan pops, and high macro butter bubbling frequencies. Synthesize a 15-second multi-cut sequence script tracking continuous ASMR impact markers.",
    long_form_vlog: "Parse comprehensive multi-location scene elements. Identify historical location assets, establishing framing sequences, and outdoor traveling narratives. Generate a balanced 3-pillar episodic layout storyboard structure."
};

// Update prompt preview text immediately based on option states
function updatePromptPreview() {
    const mode = document.getElementById('sessionMode').value;
    const promptText = document.getElementById('promptText');
    if (CLIENT_PROMPT_MAP[mode]) {
        promptText.textContent = CLIENT_PROMPT_MAP[mode];
        promptText.style.color = "#e2e8f0"; // Brighten text when active prompt populates
    }
}

// Attach initial load and change lifecycle bindings
document.getElementById('sessionMode').addEventListener('change', updatePromptPreview);
document.addEventListener('DOMContentLoaded', updatePromptPreview);

document.getElementById('processBtn').addEventListener('click', () => {
    const mode = document.getElementById('sessionMode').value;
    const statusContainer = document.getElementById('statusContainer');
    const resultsLayout = document.getElementById('resultsLayout');
    const blueprintContainer = document.getElementById('blueprintContainer');
    
    // Clear display structures and reveal live status console
    statusContainer.classList.remove('hidden');
    resultsLayout.classList.add('hidden');
    statusContainer.innerHTML = '<div class="log-line info-log">Initializing connection pipeline...</div>';
    blueprintContainer.textContent = '';

    // Open native SSE channel connection targeting streaming URL
    const eventSource = new EventSource(`http://127.0.0.1:8000/api/process/stream?mode=${mode}`);

    // Capture arbitrary text updates broadcasted by the cluster
    eventSource.addEventListener('info', (event) => {
        appendLog(statusContainer, event.data, 'info-log');
    });

    eventSource.addEventListener('progress', (event) => {
        appendLog(statusContainer, event.data, 'progress-log');
    });

    // Handle structural errors surfaced safely down streaming data streams
    eventSource.addEventListener('error', (event) => {
        const errorMsg = event.data || "An unexpected pipeline failure disrupted execution channels.";
        appendLog(statusContainer, `❌ Error: ${errorMsg}`, 'error-log');
        eventSource.close();
    });

    // Handle ultimate compilation delivery event
    eventSource.addEventListener('complete', (event) => {
        const payload = JSON.parse(event.data);
        
        appendLog(statusContainer, `🎉 Pipeline Finished! Successfully matched ${payload.processed_count} clips.`, 'success-log');
        
        // Populate the storyboard markdown code target area box
        blueprintContainer.textContent = payload.blueprint;
        
        resultsLayout.classList.remove('hidden');
        eventSource.close(); // Cleanly detach open persistent event streams
    });
});

// Clean helper module to keep scrolling locked to real-time console prints
function appendLog(container, text, className) {
    const line = document.createElement('div');
    line.className = `log-line ${className || ''}`;
    line.textContent = text;
    container.appendChild(line);
    
    // Auto scroll console container layout downward automatically
    container.scrollTop = container.scrollHeight;
}