let currentImage = null;
let currentFilter = 'none';
let currentParams = {
    contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, 
    grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0,
    vibrance: 0.0, clarity: 0.0, texture: 0.0, dehaze: 0.0, sharpen: 0.0
};
let lastAppliedParams = JSON.stringify(currentParams);
let autoApply = true;
let generatedParams = null;
let updateTimer = null;
let applyTimer = null;

// Concurrency control
let applyController = null;
let aiController = null;

const filters = window.GLINT_FILTERS || [];

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

function updateURL() {
    clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
        const params = new URLSearchParams();
        if (currentFilter && currentFilter !== 'none') params.set('filter', currentFilter);
        
        const visionModel = document.getElementById('ai-vision-model')?.value;
        const textModel = document.getElementById('ai-text-model')?.value;
        if (visionModel) params.set('v_model', visionModel);
        if (textModel) params.set('t_model', textModel);
        if (!autoApply) params.set('auto', '0');

        const defaults = { 
            contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, 
            grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0,
            vibrance: 0.0, clarity: 0.0, texture: 0.0, dehaze: 0.0, sharpen: 0.0
        };
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
    
    currentParams = { 
        contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, 
        grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0,
        vibrance: 0.0, clarity: 0.0, texture: 0.0, dehaze: 0.0, sharpen: 0.0
    };
    
    if (filterName !== 'none') {
        const resp = await fetch('/filter/' + filterName);
        if (resp.ok) {
            const fParams = await resp.json();
            currentParams = { ...currentParams, ...fParams };
        }
    }
    
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
    
    lastAppliedParams = JSON.stringify(currentParams);
    updateApplyButtonState();

    if (currentImage) applyFilter();
}

document.addEventListener('submit', (e) => e.preventDefault(), true);

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
            console.error('Upload failed:', err);
        } finally {
            showLoading(false);
        }
    };
}

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
                console.error('Paste failed:', err);
            } finally {
                showLoading(false);
            }
            break;
        }
    }
});

async function selectFilter(name, push = true) {
    currentFilter = name;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === name.toLowerCase());
    });
    
    try {
        const resp = await fetch('/filter/' + name);
        const params = await resp.json();
        
        currentParams = { 
            contrast: 1.0, saturation: 1.0, brightness: 0.0, fade: 0.0, 
            grain: 0.0, temperature: 0.0, vignette: 0.0, highlights: 0.0, shadows: 0.0,
            vibrance: 0.0, clarity: 0.0, texture: 0.0, dehaze: 0.0, sharpen: 0.0
        };
        currentParams = { ...currentParams, ...params };
        
        renderParams(currentParams);
        if (currentImage && autoApply) await applyFilter();
        if (push) updateURL();
    } catch (err) {
        console.error('selectFilter error:', err);
    }
}

function renderParams(params) {
    const categories = {
        'tone-params': ['brightness', 'contrast', 'highlights', 'shadows', 'dehaze'],
        'detail-params': ['clarity', 'texture', 'sharpen', 'grain', 'vignette'],
        'color-params': ['saturation', 'vibrance', 'temperature', 'fade']
    };

    const config = {
        'contrast': { min: 0.5, max: 1.5, step: 0.01 },
        'brightness': { min: -0.5, max: 0.5, step: 0.01 },
        'saturation': { min: 0, max: 2, step: 0.01 },
        'vibrance': { min: -1, max: 1, step: 0.01 },
        'clarity': { min: -1, max: 1, step: 0.01 },
        'texture': { min: -1, max: 1, step: 0.01 },
        'dehaze': { min: -1, max: 1, step: 0.01 },
        'sharpen': { min: 0, max: 1, step: 0.01 },
        'fade': { min: 0, max: 1, step: 0.01 },
        'grain': { min: 0, max: 1, step: 0.01 },
        'temperature': { min: -0.5, max: 0.5, step: 0.01 },
        'vignette': { min: 0, max: 1, step: 0.01 },
        'highlights': { min: -0.5, max: 0.5, step: 0.01 },
        'shadows': { min: -0.5, max: 0.5, step: 0.01 }
    };

    Object.keys(categories).forEach(catId => {
        const container = document.getElementById(catId);
        if (!container) return;
        container.innerHTML = '';
        
        categories[catId].forEach(key => {
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
    
    if (applyController) applyController.abort();
    applyController = new AbortController();

    const img = document.getElementById('filtered-img');
    if (img) img.classList.add('loading');
    
    try {
        const resp = await fetch('/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: currentImage, params: currentParams }),
            signal: applyController.signal
        });
        const data = await resp.json();
        if (img) {
            img.onload = () => img.classList.remove('loading');
            img.src = data.image;
        }
        lastAppliedParams = JSON.stringify(currentParams);
        updateApplyButtonState();
    } catch (err) {
        if (err.name === 'AbortError') return;
        if (img) img.classList.remove('loading');
    }
}

const aiForm = document.getElementById('ai-form');
if (aiForm) {
    aiForm.onsubmit = async () => {
        if (!currentImage) return;
        
        if (aiController) aiController.abort();
        aiController = new AbortController();

        const statusBox = document.getElementById('ai-result-params');
        showLoading(true);
        
        const selectedModelEl = document.getElementById('ai-vision-model');
        const modelLabel = selectedModelEl?.options[selectedModelEl.selectedIndex]?.text || "AI";
        if (statusBox) statusBox.textContent = `${modelLabel} analyzing...`;
        
        console.group(`AI Vision Request: ${modelLabel}`);
        const startTime = performance.now();

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
                }),
                signal: aiController.signal
            });
            const data = await resp.json();
            console.log("Response Data:", data);
            console.log(`Execution Time: ${(performance.now() - startTime).toFixed(2)}ms`);
            
            currentParams = { ...currentParams, ...data.params };
            renderParams(currentParams);
            await applyFilter();
            updateURL();
            if (statusBox) statusBox.textContent = "Applied:\n" + JSON.stringify(data.params, null, 2);
        } catch (err) {
            if (err.name === 'AbortError') {
                console.info("AI Request Aborted");
            } else {
                console.error("AI Request Failed:", err);
                if (statusBox) statusBox.textContent = "Error: " + err.message;
            }
        } finally {
            console.groupEnd();
            showLoading(false);
        }
    };
}

const textPromptForm = document.getElementById('text-prompt-form');
if (textPromptForm) {
    textPromptForm.onsubmit = async () => {
        if (aiController) aiController.abort();
        aiController = new AbortController();

        const promptInput = document.getElementById('prompt-input');
        const prompt = promptInput?.value;
        const statusBox = document.getElementById('prompt-params-display');
        showLoading(true);
        if (statusBox) statusBox.textContent = "Generating filter...";
        
        console.group(`AI Text-to-Filter Request`);
        const startTime = performance.now();

        document.getElementById('prompt-result')?.classList.remove('hidden');
        try {
            const resp = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt, 
                    params: currentParams,
                    model: document.getElementById('ai-text-model')?.value
                }),
                signal: aiController.signal
            });
            const data = await resp.json();
            console.log("Response Data:", data);
            console.log(`Execution Time: ${(performance.now() - startTime).toFixed(2)}ms`);
            
            generatedParams = data.params;
            currentParams = { ...currentParams, ...generatedParams };
            renderParams(currentParams);
            await applyFilter();
            updateURL();

            if (statusBox) statusBox.textContent = "Applied:\n" + JSON.stringify(data.params, null, 2);
        } catch (err) {
            if (err.name === 'AbortError') {
                console.info("AI Request Aborted");
            } else {
                console.error("AI Request Failed:", err);
                if (statusBox) statusBox.textContent = "Error: " + err.message;
            }
        } finally {
            console.groupEnd();
            showLoading(false);
        }
    };
}

const savePromptBtn = document.getElementById('save-prompt-btn');
const nameInput = document.getElementById('save-filter-name');
if (savePromptBtn) {
    savePromptBtn.onclick = async () => {
        const name = nameInput?.value.trim();
        if (!name) return;
        const resp = await fetch('/save-filter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, params: currentParams })
        });
        if (resp.ok) {
            nameInput.value = '';
            filters.push([name, 'Custom']);
            buildFiltersGrid();
        }
    };
}

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
    console.info('Image copied to clipboard');
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

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        applyFilter();
    }
});

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
