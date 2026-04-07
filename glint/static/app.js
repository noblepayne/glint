let currentImage = null;
let currentFilter = 'none';
let currentParams = {
    contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, 
    grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0
};
let lastAppliedParams = JSON.stringify(currentParams);
let autoApply = true;
let generatedParams = null;
let updateTimer = null;
let applyTimer = null;

const filters = window.GLINT_FILTERS || [];

// Build filters grid
function buildFiltersGrid() {
    const grid = document.getElementById('filters-grid');
    if (!grid) return;
    grid.innerHTML = '';
    filters.forEach(([name, desc]) => {
        const btn = document.createElement('button');
        btn.className = 'filter-btn';
        btn.textContent = name;
        btn.title = desc;
        btn.onclick = () => selectFilter(name);
        if (name === currentFilter) btn.classList.add('active');
        grid.appendChild(btn);
    });
}

// URL State Management
function updateURL() {
    clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
        const params = new URLSearchParams();
        if (currentFilter && currentFilter !== 'none') params.set('filter', currentFilter);
        
        // Sync AI model selections and Auto-Apply to URL
        const visionModel = document.getElementById('ai-vision-model')?.value;
        const textModel = document.getElementById('ai-text-model')?.value;
        if (visionModel) params.set('v_model', visionModel);
        if (textModel) params.set('t_model', textModel);
        if (!autoApply) params.set('auto', '0');

        const defaults = { contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0 };
        Object.keys(currentParams).forEach(key => {
            if (currentParams[key] !== defaults[key]) {
                params.set(key, currentParams[key].toFixed(2));
            }
        });

        const newURL = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
        window.history.pushState({ filter: currentFilter, params: { ...currentParams } }, '', newURL);
    }, 250);
}

window.onpopstate = function(event) {
    if (event.state) {
        currentFilter = event.state.filter;
        currentParams = event.state.params;
        renderParams(currentParams);
        applyFilter();
    } else {
        loadFromURL();
    }
};

async function loadFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const filterName = urlParams.get('filter') || 'none';
    
    currentParams = { contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0 };
    
    if (filterName !== 'none') {
        const resp = await fetch('/filter/' + filterName);
        if (resp.ok) {
            const fParams = await resp.json();
            currentParams = { ...currentParams, ...fParams };
        }
    }
    
    // Default to true unless explicitly '0'
    const autoParam = urlParams.get('auto');
    autoApply = autoParam !== '0';
    const sw = document.getElementById('auto-apply-switch');
    if (sw) sw.checked = autoApply;

    urlParams.forEach((value, key) => {
        if (key === 'v_model') {
            const el = document.getElementById('ai-vision-model');
            if (el) el.value = value;
        } else if (key === 't_model') {
            const el = document.getElementById('ai-text-model');
            if (el) el.value = value;
        } else if (key !== 'filter' && key !== 'auto' && currentParams.hasOwnProperty(key)) {
            currentParams[key] = parseFloat(value);
        }
    });
    
    currentFilter = filterName;
    buildFiltersGrid();
    renderParams(currentParams);
    
    // Set initial lastAppliedParams to match the loaded state
    lastAppliedParams = JSON.stringify(currentParams);
    updateApplyButtonState();

    if (currentImage) applyFilter();
}

// Global Form Prevention
document.addEventListener('submit', (e) => e.preventDefault(), true);

// Upload handling
const uploadForm = document.getElementById('upload-form');
if (uploadForm) {
    uploadForm.onsubmit = async () => {
        const file = document.getElementById('image-input')?.files[0];
        if (!file) return;
        showLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch('/upload', { method: 'POST', body: formData });
            const data = await resp.json();
            currentImage = data.image;
            document.getElementById('original-img').src = currentImage;
            document.getElementById('preview-section')?.classList.remove('hidden');
            await selectFilter('none');
        } catch (err) {
            alert('Upload failed: ' + err.message);
        } finally {
            showLoading(false);
        }
    };
}

// Paste handling
document.addEventListener('paste', async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            const file = item.getAsFile();
            showLoading(true);
            const formData = new FormData();
            formData.append('file', file);
            try {
                const resp = await fetch('/upload', { method: 'POST', body: formData });
                const data = await resp.json();
                currentImage = data.image;
                document.getElementById('original-img').src = currentImage;
                document.getElementById('preview-section')?.classList.remove('hidden');
                await selectFilter('none');
            } catch (err) {
                alert('Paste failed: ' + err.message);
            } finally {
                showLoading(false);
            }
            break;
        }
    }
});

// Filter selection
async function selectFilter(name, push = true) {
    currentFilter = name;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === name.toLowerCase());
    });
    
    try {
        const resp = await fetch('/filter/' + name);
        const params = await resp.json();
        
        currentParams = { contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0 };
        currentParams = { ...currentParams, ...params };
        
        renderParams(currentParams);
        if (currentImage && autoApply) await applyFilter();
        if (push) updateURL();
    } catch (err) {
        console.error('selectFilter error:', err);
    }
}

function renderParams(params) {
    const container = document.getElementById('params-container');
    if (!container) return;
    container.innerHTML = '';
    const config = {
        'contrast': { min: 0.5, max: 1.5, step: 0.01 },
        'brightness': { min: -0.5, max: 0.5, step: 0.01 },
        'saturation': { min: 0, max: 2, step: 0.01 },
        'fade': { min: 0, max: 1, step: 0.01 },
        'grain': { min: 0, max: 1, step: 0.01 },
        'temperature': { min: -0.5, max: 0.5, step: 0.01 },
        'vignette': { min: 0, max: 1, step: 0.01 },
        'highlights': { min: -0.5, max: 0.5, step: 0.01 },
        'shadows': { min: -0.5, max: 0.5, step: 0.01 }
    };

    Object.keys(config).forEach(key => {
        const c = config[key];
        const val = params[key] !== undefined ? params[key] : (key === 'contrast' || key === 'saturation' ? 1.0 : 0.0);
        const row = document.createElement('div');
        row.className = 'param-row';
        row.innerHTML = `
            <label>${key}</label>
            <input type="range" min="${c.min}" max="${c.max}" step="${c.step}" value="${val}" 
                   oninput="handleParamChange('${key}', this.value, this.nextElementSibling)">
            <span>${val.toFixed(2)}</span>
        `;
        container.appendChild(row);
    });
    updateApplyButtonState();
}

function handleParamChange(key, value, displayEl) {
    const val = parseFloat(value);
    currentParams[key] = val;
    if (displayEl) displayEl.textContent = val.toFixed(2);
    
    updateURL();
    updateApplyButtonState();

    if (autoApply) {
        clearTimeout(applyTimer);
        applyTimer = setTimeout(() => applyFilter(), 150);
    }
}

function updateApplyButtonState() {
    const btn = document.getElementById('apply-params');
    if (!btn) return;
    const isDirty = JSON.stringify(currentParams) !== lastAppliedParams;
    btn.classList.toggle('dirty', isDirty);
    if (!autoApply && isDirty) {
        btn.classList.add('contrast');
        btn.classList.remove('outline');
    } else {
        btn.classList.remove('contrast');
        btn.classList.add('outline');
    }
}

async function applyFilter() {
    if (!currentImage) return;
    const img = document.getElementById('filtered-img');
    if (img) img.classList.add('loading');
    lastAppliedParams = JSON.stringify(currentParams);
    updateApplyButtonState();
    try {
        const resp = await fetch('/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: currentImage, params: currentParams })
        });
        const data = await resp.json();
        if (img) {
            img.onload = () => img.classList.remove('loading');
            img.src = data.image;
        }
    } catch (err) {
        if (img) img.classList.remove('loading');
    }
}

// AI Vision
const aiForm = document.getElementById('ai-form');
if (aiForm) {
    aiForm.onsubmit = async () => {
        if (!currentImage) return alert('Upload image first');
        const statusBox = document.getElementById('ai-result-params');
        showLoading(true);
        if (statusBox) statusBox.textContent = "Gemma 4 analyzing...";
        document.getElementById('ai-result')?.classList.remove('hidden');
        try {
            const resp = await fetch('/vision/auto-fix', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: currentImage,
                    prompt: document.getElementById('ai-prompt')?.value,
                    focus: document.getElementById('ai-focus')?.value,
                    model: document.getElementById('ai-vision-model')?.value,
                    max_rounds: parseInt(document.getElementById('ai-rounds')?.value || "3")
                })
            });
            const data = await resp.json();
            // Merge AI params into current state
            currentParams = { ...currentParams, ...data.params };
            lastAppliedParams = JSON.stringify(currentParams);
            renderParams(currentParams);
            updateApplyButtonState();
            await applyFilter();
            updateURL();
            if (statusBox) statusBox.textContent = "Applied:\n" + JSON.stringify(data.params, null, 2);
        } catch (err) {
            if (statusBox) statusBox.textContent = "Error: " + err.message;
        } finally {
            showLoading(false);
        }
    };
}

// Text to Filter
const textPromptForm = document.getElementById('text-prompt-form');
if (textPromptForm) {
    textPromptForm.onsubmit = async () => {
        const prompt = document.getElementById('prompt-input')?.value;
        showLoading(true);
        try {
            const resp = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt, 
                    params: currentParams,
                    model: document.getElementById('ai-text-model')?.value
                })
            });
            const data = await resp.json();
            generatedParams = data.params;
            document.getElementById('prompt-params-display').textContent = JSON.stringify(data.params, null, 2);
            document.getElementById('prompt-result')?.classList.remove('hidden');
        } finally {
            showLoading(false);
        }
    };
}

document.getElementById('apply-prompt-btn').onclick = () => {
    if (generatedParams) {
        currentParams = { ...currentParams, ...generatedParams };
        lastAppliedParams = JSON.stringify(currentParams);
        renderParams(currentParams);
        updateApplyButtonState();
        applyFilter();
        updateURL();
    }
};

// Unified Save Preset
const savePromptBtn = document.getElementById('save-prompt-btn');
const nameInput = document.getElementById('save-filter-name');
if (savePromptBtn) {
    savePromptBtn.onclick = async () => {
        const name = nameInput?.value.trim();
        if (!name) return alert('Please enter a name for your preset');
        const resp = await fetch('/save-filter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, params: currentParams })
        });
        if (resp.ok) {
            alert('Saved as preset: ' + name);
            nameInput.value = '';
            filters.push([name, 'Custom']);
            buildFiltersGrid();
        }
    };
}

// Utils
document.querySelectorAll('.style-chip').forEach(chip => {
    chip.onclick = () => {
        const p = chip.dataset.style;
        if (document.getElementById('ai-prompt')) document.getElementById('ai-prompt').value = p;
        if (document.getElementById('prompt-input')) document.getElementById('prompt-input').value = p;
    };
});

document.getElementById('save-btn').onclick = () => {
    const a = document.createElement('a');
    const img = document.getElementById('filtered-img');
    if (!img) return;
    a.href = img.src;
    a.download = 'glint.png';
    a.click();
};

document.getElementById('copy-btn').onclick = async () => {
    const img = document.getElementById('filtered-img');
    if (!img) return;
    const blob = await (await fetch(img.src)).blob();
    await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
    alert('Copied to clipboard!');
};

document.getElementById('export-cube-btn').onclick = async () => {
    const resp = await fetch('/export-cube', { 
        method: 'POST', 
        body: JSON.stringify({ params: currentParams }), 
        headers: { 'Content-Type': 'application/json' } 
    });
    const data = await resp.json();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([atob(data.cube)]));
    a.download = data.filename;
    a.click();
};

function showLoading(show) {
    document.getElementById('loading')?.classList.toggle('hidden', !show);
}

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        applyFilter();
    }
});

// Boot
const autoApplySwitch = document.getElementById('auto-apply-switch');
if (autoApplySwitch) {
    autoApplySwitch.onchange = (e) => {
        autoApply = e.target.checked;
        updateURL();
        updateApplyButtonState();
        if (autoApply) applyFilter();
    };
}

const applyBtn = document.getElementById('apply-params');
if (applyBtn) {
    applyBtn.onclick = () => applyFilter();
}

buildFiltersGrid();
loadFromURL();
