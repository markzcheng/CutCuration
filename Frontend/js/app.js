const DISCOVERED_RAW_CLIPS = [
    { filename: "clip_A.mp4", type: "video/mp4" },
    { filename: "clip_B.mov", type: "video/quicktime" },
    { filename: "clip_C.mp4", type: "video/mp4" }
];

const CLIENT_PROMPT_MAP = {
    short_form_cooking: "Analyze raw food footage arrays. Filter assets for sharp audio cues, transient pan pops, and high macro butter bubbling frequencies. Synthesize a 15-second multi-cut sequence script tracking continuous ASMR impact markers.",
    long_form_vlog: "Parse comprehensive multi-location scene elements. Identify historical location assets, establishing framing sequences, and outdoor traveling narratives. Generate a balanced 3-pillar episodic layout storyboard structure."
};

let CURRENT_MOCK_MODE = true;
let PROMPT_DEFAULTS = {};
let PROMPT_DIRTY = false;

async function loadPromptDefaults() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/prompts/defaults');
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        PROMPT_DEFAULTS = await response.json();
    } catch (error) {
        console.warn('Could not load prompt defaults from backend:', error);
        PROMPT_DEFAULTS = {
            short_form_cooking: { analysis_prompt: CLIENT_PROMPT_MAP.short_form_cooking },
            long_form_vlog: { analysis_prompt: CLIENT_PROMPT_MAP.long_form_vlog }
        };
    }
}

function getSelectedSessionMode() {
    const modeField = document.getElementById('sessionMode');
    return modeField ? modeField.value : 'short_form_cooking';
}

function getCurrentDefaultPrompt() {
    const mode = getSelectedSessionMode();
    const modeConfig = PROMPT_DEFAULTS[mode] || {};
    return modeConfig.analysis_prompt || CLIENT_PROMPT_MAP[mode] || '';
}

function setPromptEditorValue(promptValue, dirty = false) {
    const editor = document.getElementById('promptEditor');
    if (!editor) return;
    editor.value = promptValue;
    PROMPT_DIRTY = dirty;
    updatePromptStatusBadge();
}

function updatePromptStatusBadge() {
    const badge = document.getElementById('promptStatusBadge');
    if (!badge) return;
    badge.textContent = PROMPT_DIRTY ? 'Custom prompt active' : 'Default prompt active';
    badge.className = PROMPT_DIRTY ? 'badge badge-custom' : 'badge';
}

function initPromptEditorControls() {
    const editor = document.getElementById('promptEditor');
    const resetButton = document.getElementById('resetPromptBtn');
    const modeSelect = document.getElementById('sessionMode');

    if (editor) {
        editor.addEventListener('input', () => {
            PROMPT_DIRTY = true;
            updatePromptStatusBadge();
        });
    }

    if (resetButton) {
        resetButton.addEventListener('click', () => {
            setPromptEditorValue(getCurrentDefaultPrompt(), false);
        });
    }

    if (modeSelect) {
        modeSelect.addEventListener('change', () => {
            if (!PROMPT_DIRTY) {
                setPromptEditorValue(getCurrentDefaultPrompt(), false);
            }
        });
    }
}

function getPromptOverrideQuery() {
    const editor = document.getElementById('promptEditor');
    if (!editor || !PROMPT_DIRTY) return '';
    const value = editor.value.trim();
    return value ? `&prompt_override=${encodeURIComponent(value)}` : '';
}

function getMockModeQueryParam() {
    return CURRENT_MOCK_MODE ? 'true' : 'false';
}

function updateMockModeUI() {
    const toggle = document.getElementById('mockModeToggle');
    const badge = document.getElementById('mockModeBadge');
    if (toggle) toggle.checked = CURRENT_MOCK_MODE;
    if (badge) {
        badge.textContent = CURRENT_MOCK_MODE ? 'Mock mode ON' : 'Real mode';
        badge.className = CURRENT_MOCK_MODE ? 'mock-mode-badge mock-mode-on' : 'mock-mode-badge mock-mode-off';
    }
}

function showMockDisableConfirmation() {
    const overlay = document.getElementById('mockConfirmOverlay');
    if (overlay) overlay.classList.remove('hidden');
}

function hideMockDisableConfirmation() {
    const overlay = document.getElementById('mockConfirmOverlay');
    if (overlay) overlay.classList.add('hidden');
}

function setMockMode(enabled) {
    CURRENT_MOCK_MODE = enabled;
    updateMockModeUI();
    renderSourceClipsStaging();
}

function bindMockToggleControl() {
    const toggle = document.getElementById('mockModeToggle');
    const confirmBtn = document.getElementById('confirmMockOffBtn');
    const cancelBtn = document.getElementById('cancelMockOffBtn');

    if (toggle) {
        toggle.addEventListener('change', (event) => {
            const checked = event.target.checked;
            if (!checked) {
                showMockDisableConfirmation();
                return;
            }
            setMockMode(true);
        });
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            setMockMode(false);
            hideMockDisableConfirmation();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            const toggleField = document.getElementById('mockModeToggle');
            if (toggleField) toggleField.checked = true;
            hideMockDisableConfirmation();
        });
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    setupTabNavigation();
    bindMockToggleControl();
    updateMockModeUI();
    await renderSourceClipsStaging();
    await loadPromptDefaults();
    initPromptEditorControls();
    setPromptEditorValue(getCurrentDefaultPrompt(), false);
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

async function renderSourceClipsStaging() {
    const container = document.getElementById('videoStagingArea');
    if (!container) return;

    const clips = await fetchSourceClipsFromBackend();
    container.innerHTML = clips.map(clip => `
        <div class="video-item-node animate-fade-in">
            <span class="video-icon">🎞️</span>
            <span class="video-meta-name" title="${clip.filename}">${clip.filename}</span>
            <span class="video-meta-type">${clip.type}</span>
        </div>
    `).join('');
}

async function fetchSourceClipsFromBackend() {
    try {
        const response = await fetch(`http://127.0.0.1:8000/api/videos?mock_mode=${getMockModeQueryParam()}`);
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        const clips = await response.json();
        if (Array.isArray(clips) && clips.length) return clips;
    } catch (error) {
        console.warn('Could not load RawVideos from backend:', error);
    }

    return DISCOVERED_RAW_CLIPS;
}

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

    const promptOverrideQuery = getPromptOverrideQuery();
    const eventSource = new EventSource(`http://127.0.0.1:8000/api/process/stream?mode=${mode}&mock_mode=${getMockModeQueryParam()}${promptOverrideQuery}`);

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
        
        blueprintContainer.innerHTML = renderMarkdownToHtml(payload.blueprint);
        generateDataPreviewsAndDownloads(payload.blueprint, payload.processed_count);
        
        resetExecutionButtonState(processButton);
        resultsLayout.classList.remove('hidden');
        eventSource.close();
    });
});

function renderMarkdownToHtml(markdown) {
    if (!markdown) return '';
    const escapeHtml = (text) => text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const inlineFormat = (text) => text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');

    const lines = markdown.split(/\r?\n/);
    let html = '';
    let listType = null;

    const closeList = () => {
        if (listType === 'ul') html += '</ul>';
        if (listType === 'ol') html += '</ol>';
        listType = null;
    };

    lines.forEach((rawLine) => {
        const line = rawLine.trim();
        if (!line) {
            closeList();
            return;
        }

        const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
        if (headingMatch) {
            closeList();
            const level = headingMatch[1].length;
            html += `<h${level}>${inlineFormat(escapeHtml(headingMatch[2]))}</h${level}>`;
            return;
        }

        const unorderedMatch = line.match(/^[-*+]\s+(.*)$/);
        if (unorderedMatch) {
            if (listType !== 'ul') {
                closeList();
                html += '<ul>';
                listType = 'ul';
            }
            html += `<li>${inlineFormat(escapeHtml(unorderedMatch[1]))}</li>`;
            return;
        }

        const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
        if (orderedMatch) {
            if (listType !== 'ol') {
                closeList();
                html += '<ol>';
                listType = 'ol';
            }
            html += `<li>${inlineFormat(escapeHtml(orderedMatch[1]))}</li>`;
            return;
        }

        closeList();
        html += `<p>${inlineFormat(escapeHtml(line))}</p>`;
    });

    closeList();
    return `<div class="markdown-body">${html}</div>`;
}

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