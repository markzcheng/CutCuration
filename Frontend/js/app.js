document.getElementById('processBtn').addEventListener('click', async () => {
    const mode = document.getElementById('sessionMode').value;
    const statusContainer = document.getElementById('statusContainer');
    const resultsLayout = document.getElementById('resultsLayout');
    const blueprintContainer = document.getElementById('blueprintContainer');
    
    // Toggle UI States
    statusContainer.classList.remove('hidden');
    resultsLayout.classList.add('hidden');
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Server API Error');
        }
        
        const data = await response.json();
        
        // Render Output text strings
        blueprintContainer.textContent = data.strategic_blueprint;
        resultsLayout.classList.remove('hidden');
        
    } catch (error) {
        alert(`Pipeline Execution Failed: ${error.message}`);
    } finally {
        statusContainer.classList.add('hidden');
    }
});