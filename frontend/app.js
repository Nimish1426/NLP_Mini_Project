// DOM Elements
const elements = {
    senderCulture: document.getElementById('sender-culture'),
    recipientCulture: document.getElementById('recipient-culture'),
    swapBtn: document.getElementById('swap-cultures'),
    exampleSelect: document.getElementById('example-select'),
    messageInput: document.getElementById('message-input'),
    charCount: document.getElementById('char-count'),
    analyzeBtn: document.getElementById('analyze-btn'),
    clearBtn: document.getElementById('clear-btn'),
    errorMsg: document.getElementById('error-message'),
    resultsPanel: document.getElementById('results-panel'),
    noFlagsState: document.getElementById('no-flags-state'),
    resultsContent: document.getElementById('results-content'),
    
    // Toggles
    layerSemantic: document.getElementById('layer-semantic'),
    layerMl: document.getElementById('layer-ml'),
    layerTone: document.getElementById('layer-tone'),

    // Result elements
    riskScore: document.getElementById('risk-score'),
    riskText: document.getElementById('risk-text'),
    gaugePath: document.getElementById('gauge-path'),
    highlightedText: document.getElementById('highlighted-text'),
    improvedText: document.getElementById('improved-text'),
    cultureTips: document.getElementById('culture-tips'),
    categoryBreakdown: document.getElementById('category-breakdown'),
    toneMeters: document.getElementById('tone-meters'),
    flagCount: document.getElementById('flag-count'),
    flagCardsList: document.getElementById('flag-cards-list'),
    debugContent: document.getElementById('debug-content'),

    // Actions
    copyImprovedBtn: document.getElementById('copy-improved-btn'),
    reanalyzeBtn: document.getElementById('reanalyze-btn'),
    downloadBtn: document.getElementById('download-report-btn')
};

// State
let lastAnalysisResult = null;
let examplesData = [];
const API_BASE = ''; // Empty string for same-origin

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    setupEventListeners();
    await fetchCultures();
    await fetchExamples();
}

function setupEventListeners() {
    elements.messageInput.addEventListener('input', updateCharCount);
    elements.analyzeBtn.addEventListener('click', handleAnalyze);
    elements.clearBtn.addEventListener('click', clearForm);
    elements.swapBtn.addEventListener('click', swapCultures);
    elements.exampleSelect.addEventListener('change', loadExample);
    
    elements.copyImprovedBtn.addEventListener('click', copyImprovedText);
    elements.reanalyzeBtn.addEventListener('click', reanalyzeImprovedText);
    elements.downloadBtn.addEventListener('click', downloadReport);

    // Re-analyze on toggle change if we have results
    [elements.layerSemantic, elements.layerMl, elements.layerTone].forEach(toggle => {
        toggle.addEventListener('change', () => {
            if (!elements.resultsPanel.classList.contains('hidden')) {
                handleAnalyze();
            }
        });
    });
}

function updateCharCount() {
    const len = elements.messageInput.value.length;
    elements.charCount.textContent = len;
    if (len > 5000) {
        elements.charCount.style.color = 'var(--severity-high)';
    } else {
        elements.charCount.style.color = 'var(--text-muted)';
    }
}

async function fetchCultures() {
    try {
        const res = await fetch(`${API_BASE}/api/cultures`);
        if (!res.ok) throw new Error('Failed to load cultures');
        const cultures = await res.json();
        
        const populateSelect = (selectElem) => {
            cultures.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.flag_emoji} ${c.display_name}`;
                selectElem.appendChild(opt);
            });
        };
        populateSelect(elements.senderCulture);
        populateSelect(elements.recipientCulture);
    } catch (err) {
        showError('Could not load cultures from server.');
        console.error(err);
    }
}

async function fetchExamples() {
    try {
        const res = await fetch(`${API_BASE}/api/examples`);
        if (!res.ok) throw new Error('Failed to load examples');
        examplesData = await res.json();
        
        examplesData.forEach((ex, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.textContent = ex.title || `Example ${idx + 1}`;
            elements.exampleSelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Could not load examples:', err);
    }
}

function loadExample() {
    const idx = elements.exampleSelect.value;
    if (idx !== "") {
        const ex = examplesData[idx];
        elements.messageInput.value = ex.text;
        elements.senderCulture.value = ex.source_culture || '';
        elements.recipientCulture.value = ex.target_culture || '';
        updateCharCount();
        handleAnalyze();
    }
}

function swapCultures() {
    const temp = elements.senderCulture.value;
    elements.senderCulture.value = elements.recipientCulture.value;
    elements.recipientCulture.value = temp;
}

function clearForm() {
    elements.messageInput.value = '';
    elements.senderCulture.value = '';
    elements.recipientCulture.value = '';
    elements.exampleSelect.value = '';
    updateCharCount();
    elements.resultsPanel.classList.add('hidden');
    elements.errorMsg.classList.add('hidden');
    lastAnalysisResult = null;
}

function showError(msg) {
    elements.errorMsg.textContent = msg;
    elements.errorMsg.classList.remove('hidden');
}

function hideError() {
    elements.errorMsg.classList.add('hidden');
}

// Utility: escape HTML
function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

async function handleAnalyze() {
    hideError();
    const text = elements.messageInput.value.trim();
    const sender = elements.senderCulture.value;
    const recipient = elements.recipientCulture.value;

    if (!text) return showError('Please enter a message to analyze.');
    if (!sender || !recipient) return showError('Please select both cultures.');
    if (text.length > 5000) return showError('Message exceeds 5000 characters.');

    // Show loading
    elements.resultsPanel.classList.add('hidden');
    const analyzeBtnText = elements.analyzeBtn.querySelector('.btn-text');
    const analyzeBtnSpinner = elements.analyzeBtn.querySelector('.spinner');
    analyzeBtnText.textContent = 'Analyzing...';
    analyzeBtnSpinner.classList.remove('hidden');
    elements.analyzeBtn.disabled = true;

    const payload = {
        text,
        source_culture: sender,
        target_culture: recipient,
        options: {
            use_semantic: elements.layerSemantic.checked,
            use_ml: elements.layerMl.checked,
            use_tone: elements.layerTone.checked
        }
    };

    try {
        const res = await fetch(`${API_BASE}/api/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Analysis failed on server.');
        }

        const data = await res.json();
        lastAnalysisResult = data;
        renderResults(data);
        
    } catch (err) {
        showError(`Analysis error: ${err.message}`);
    } finally {
        analyzeBtnText.textContent = 'Analyze';
        analyzeBtnSpinner.classList.add('hidden');
        elements.analyzeBtn.disabled = false;
    }
}

function renderResults(data) {
    elements.resultsPanel.classList.remove('hidden');
    elements.debugContent.textContent = JSON.stringify(data.debug, null, 2);

    if (!data.flags || data.flags.length === 0) {
        elements.noFlagsState.classList.remove('hidden');
        elements.resultsContent.classList.add('hidden');
    } else {
        elements.noFlagsState.classList.add('hidden');
        elements.resultsContent.classList.remove('hidden');
        
        renderRiskGauge(data.risk_score);
        renderHighlightedText(elements.messageInput.value, data.flags);
        renderImprovedText(data.suggested_rewrite);
        renderCultureInsight(data.culture_insight);
        renderCategoryBreakdown(data.category_breakdown);
        if (data.tone_profile) {
            renderToneProfile(data.tone_profile, null); // Target culture tone logic requires culture fetch, omit for simplicity or fetch separately
        }
        renderFlagCards(data.flags);
    }
}

function renderRiskGauge(score) {
    elements.riskScore.textContent = score;
    let color = 'var(--severity-low)';
    let text = 'Low Risk';
    
    if (score >= 70) { color = 'var(--severity-high)'; text = 'High Risk'; }
    else if (score >= 30) { color = 'var(--severity-medium)'; text = 'Medium Risk'; }
    
    elements.riskText.textContent = text;
    elements.riskText.style.color = color;
    
    // SVG path total length is approx 251.2
    const pathLength = 251.2;
    const offset = pathLength - (score / 100) * pathLength;
    elements.gaugePath.style.strokeDashoffset = offset;
    elements.gaugePath.style.stroke = color;
}

function renderHighlightedText(text, flags) {
    // Sort flags by start position
    const sortedFlags = [...flags].sort((a, b) => a.start - b.start);
    
    let html = '';
    let lastIndex = 0;
    
    // Very basic overlap handling: just take the first one if they overlap
    for (const flag of sortedFlags) {
        if (flag.start < lastIndex) continue; // Skip overlaps for simplicity in UI
        
        html += escapeHtml(text.substring(lastIndex, flag.start));
        const spanText = escapeHtml(text.substring(flag.start, flag.end));
        
        const severityLabel = flag.severity === 3 ? 'high' : (flag.severity === 2 ? 'medium' : 'low');
        const severityClass = `severity-${severityLabel}`;
        html += `<mark class="${severityClass}" data-flag-id="${flag.id}" title="${flag.category}: ${flag.explanation}">${spanText}</mark>`;
        
        lastIndex = flag.end;
    }
    
    html += escapeHtml(text.substring(lastIndex));
    elements.highlightedText.innerHTML = html;

    // Add click listeners to marks
    elements.highlightedText.querySelectorAll('mark').forEach(mark => {
        mark.addEventListener('click', (e) => {
            const id = e.target.getAttribute('data-flag-id');
            const card = document.getElementById(`flag-card-${id}`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                card.style.transform = 'scale(1.02)';
                setTimeout(() => card.style.transform = '', 300);
            }
        });
    });
}

function renderImprovedText(text) {
    elements.improvedText.innerText = text || 'No automatic improvements available.';
}

function renderCultureInsight(insights) {
    if (!insights || !insights.communication_tips) {
        elements.cultureTips.innerHTML = '<p>No specific insights available.</p>';
        return;
    }
    
    const ul = document.createElement('ul');
    ul.style.paddingLeft = '20px';
    ul.style.listStyleType = 'disc';
    insights.communication_tips.forEach(tip => {
        const li = document.createElement('li');
        li.textContent = tip;
        li.style.marginBottom = '8px';
        ul.appendChild(li);
    });
    elements.cultureTips.innerHTML = '';
    elements.cultureTips.appendChild(ul);
}

function renderCategoryBreakdown(breakdown) {
    const counts = {};
    breakdown.forEach(b => {
        counts[b.category] = b.count;
    });
    
    let html = '';
    const max = Math.max(...Object.values(counts), 1);
    
    for (const [cat, count] of Object.entries(counts)) {
        const pct = (count / max) * 100;
        html += `
            <div class="bar-chart-row">
                <div class="bar-label" title="${cat}">${cat}</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${pct}%"></div>
                </div>
                <div class="bar-value">${count}</div>
            </div>
        `;
    }
    elements.categoryBreakdown.innerHTML = html || '<p>No data</p>';
}

function renderToneProfile(tone, targetTone) {
    let html = '';
    const dims = [
        { key: 'directness', label: 'Directness', left: 'Indirect', right: 'Direct' },
        { key: 'formality', label: 'Formality', left: 'Informal', right: 'Formal' },
        { key: 'hedging', label: 'Hedging', left: 'Confident', right: 'Hedging' }
    ];

    dims.forEach(dim => {
        const val = tone[dim.key] !== undefined ? tone[dim.key] * 100 : 50;
        const target = targetTone && targetTone[dim.key] !== undefined ? targetTone[dim.key] * 100 : null;
        
        html += `
            <div class="tone-meter">
                <div class="tone-label-row">
                    <span>${dim.left}</span>
                    <span style="font-weight:600">${dim.label}</span>
                    <span>${dim.right}</span>
                </div>
                <div class="tone-track">
                    <div class="tone-value" style="left: ${val}%" title="Detected: ${(val/100).toFixed(2)}"></div>
                    ${target !== null ? `<div class="tone-target" style="left: ${target}%" title="Target Culture Preference: ${(target/100).toFixed(2)}"></div>` : ''}
                </div>
            </div>
        `;
    });
    
    elements.toneMeters.innerHTML = html;
}

function renderFlagCards(flags) {
    elements.flagCount.textContent = flags.length;
    let html = '';
    
    flags.forEach(f => {
        const severityLabel = f.severity === 3 ? 'High' : (f.severity === 2 ? 'Medium' : 'Low');
        const sevClass = `severity-${severityLabel.toLowerCase()}`;
        const methodClass = `badge-method-${f.detected_by.toLowerCase()}`;
        const confPct = Math.round(f.confidence * 100);
        
        let suggsHtml = '';
        if (f.suggestions && f.suggestions.length > 0) {
            suggsHtml = `<div class="suggestions">` + 
                f.suggestions.map(s => `<button class="suggestion-chip" data-phrase="${escapeHtml(f.text)}" data-repl="${escapeHtml(s)}">${escapeHtml(s)}</button>`).join('') +
                `</div>`;
        }

        html += `
            <div class="flag-card ${sevClass}" id="flag-card-${f.id}">
                <div class="flag-header">
                    <span class="phrase-quote">"${escapeHtml(f.text)}"</span>
                    <div class="badges">
                        <span class="badge badge-category">${f.category}</span>
                        <span class="badge badge-${severityLabel.toLowerCase()}">${severityLabel}</span>
                        <span class="badge ${methodClass}">${f.detected_by}</span>
                    </div>
                </div>
                <div class="confidence-bar" title="Confidence: ${confPct}%">
                    <div class="confidence-fill" style="width: ${confPct}%"></div>
                </div>
                <p class="flag-explanation">${f.explanation}</p>
                ${f.literal_meaning_risk ? `<p class="flag-misunderstood"><span>⚠️</span> Might be seen as: ${f.literal_meaning_risk}</p>` : ''}
                ${suggsHtml}
            </div>
        `;
    });
    
    elements.flagCardsList.innerHTML = html;

    // Add suggestion chip listeners
    elements.flagCardsList.querySelectorAll('.suggestion-chip').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const repl = e.target.getAttribute('data-repl');
            const orig = e.target.getAttribute('data-phrase');
            let currentText = elements.improvedText.innerHTML;
            
            // Build the highlighted span
            const spanRepl = `<span class="highlight-replace">${escapeHtml(repl)}</span>`;
            
            // Simple replace (only first occurrence for simplicity)
            elements.improvedText.innerHTML = currentText.replace(escapeHtml(orig), spanRepl);
        });
    });
}

function copyImprovedText() {
    navigator.clipboard.writeText(elements.improvedText.innerText).then(() => {
        const origText = elements.copyImprovedBtn.textContent;
        elements.copyImprovedBtn.textContent = 'Copied!';
        setTimeout(() => elements.copyImprovedBtn.textContent = origText, 2000);
    });
}

function reanalyzeImprovedText() {
    elements.messageInput.value = elements.improvedText.innerText;
    updateCharCount();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    handleAnalyze();
}

function downloadReport() {
    if (!lastAnalysisResult) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(lastAnalysisResult, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", "culturelens-report.json");
    dlAnchorElem.click();
}
