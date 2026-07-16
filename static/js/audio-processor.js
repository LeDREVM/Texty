/**
 * Transcripteur Audio Pro — Analyse qualité & amélioration audio
 * Complète app.js. Analyse la qualité côté client (Web Audio) et pilote /api/enhance.
 */

/* ======================= ANALYSE DE QUALITÉ ======================= */

async function analyzeAudioQuality() {
    if (!currentFile) {
        showToast('Aucun fichier audio à analyser', 'warning');
        return;
    }

    const btn = document.getElementById('analyzeBtn');
    const qualityBar = document.getElementById('qualityBar');
    const qualityText = document.getElementById('qualityText');
    const original = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = '🔍 Analyse…'; }

    try {
        const ctx = audioContext || new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuffer = await currentFile.arrayBuffer();
        const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));

        const metrics = computeQualityMetrics(audioBuffer);
        if (qualityBar) qualityBar.style.width = metrics.score + '%';
        if (qualityText) {
            qualityText.textContent = `Qualité: ${metrics.score}/100 · pic ${metrics.peak.toFixed(2)} · SNR ~${metrics.snr.toFixed(0)} dB`;
        }

        applyQualitySuggestions(metrics);
        showToast(`✅ Analyse terminée — score ${metrics.score}/100`, 'success');
    } catch (error) {
        console.error('Erreur analyse:', error);
        if (qualityText) qualityText.textContent = 'Analyse impossible (format non décodable)';
        showToast('❌ Impossible d\'analyser ce fichier dans le navigateur', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = original; }
    }
}

function computeQualityMetrics(audioBuffer) {
    const data = audioBuffer.getChannelData(0);
    const n = data.length || 1;

    // Sous-échantillonnage pour rester rapide sur les longs fichiers
    const step = Math.max(1, Math.floor(n / 200000));
    let sumSq = 0, peak = 0, count = 0;
    const amps = [];
    for (let i = 0; i < n; i += step) {
        const a = Math.abs(data[i]);
        sumSq += data[i] * data[i];
        if (a > peak) peak = a;
        amps.push(a);
        count++;
    }
    const rms = Math.sqrt(sumSq / (count || 1));

    // Estimation du plancher de bruit : moyenne des 10 % d'amplitudes les plus faibles
    amps.sort((x, y) => x - y);
    const lowCount = Math.max(1, Math.floor(amps.length * 0.1));
    let noiseSum = 0;
    for (let i = 0; i < lowCount; i++) noiseSum += amps[i];
    const noiseFloor = noiseSum / lowCount;
    const snr = 20 * Math.log10(rms / (noiseFloor + 1e-10));

    // Score 0–100 (heuristique proche du backend)
    let score = 100;
    if (peak < 0.1) score -= 25;
    else if (peak > 0.98) score -= 30;
    if (snr < 10) score -= 25;
    else if (snr > 30) score += 5;
    if (rms < 0.02) score -= 15;
    score = Math.max(0, Math.min(100, Math.round(score)));

    return { score, peak, rms, snr, noiseFloor };
}

function applyQualitySuggestions(metrics) {
    const suggestions = document.getElementById('autoSuggestions');
    const list = document.getElementById('suggestionsList');
    if (!list) return;

    const items = [];
    if (metrics.snr < 15) {
        items.push({ text: 'Bruit de fond détecté — activer la réduction de bruit (70 %)',
            action: () => setSlider('noiseReduction', 70, 'noiseValue', '%') });
    }
    if (metrics.peak < 0.1) {
        items.push({ text: 'Signal faible — amplifier de +6 dB',
            action: () => setSlider('amplification', 6, 'ampValue', ' dB') });
    }
    if (metrics.peak > 0.98) {
        items.push({ text: 'Saturation possible — réduire de −3 dB',
            action: () => setSlider('amplification', -3, 'ampValue', ' dB') });
    }
    if (metrics.rms < 0.05) {
        items.push({ text: 'Niveau non optimal — activer la normalisation',
            action: () => setSlider('normalization', 80, 'normValue', '%') });
    }
    if (items.length === 0) {
        items.push({ text: 'Qualité satisfaisante — aucun réglage nécessaire', action: () => {} });
    }

    list.innerHTML = '';
    items.forEach((item) => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        const span = document.createElement('span');
        span.className = 'suggestion-text';
        span.textContent = item.text;
        const btn = document.createElement('button');
        btn.className = 'btn btn-small';
        btn.textContent = 'Appliquer';
        btn.addEventListener('click', item.action);
        div.append(span, btn);
        list.appendChild(div);
    });
    if (suggestions) suggestions.style.display = 'block';
}

/* ======================= AMÉLIORATION (API) ======================= */

function buildEnhanceFormData() {
    const formData = new FormData();
    formData.append('audio', currentFile);
    const noise = document.getElementById('noiseReduction');
    const amp = document.getElementById('amplification');
    const norm = document.getElementById('normalization');
    if (noise) formData.append('noise_reduction', (parseFloat(noise.value) / 100).toFixed(2));
    if (amp) formData.append('amplification', amp.value);
    if (norm) formData.append('normalize', parseFloat(norm.value) > 0 ? 'true' : 'false');
    return formData;
}

async function requestEnhancedBlob() {
    const response = await fetch(apiUrl('/api/enhance'), { method: 'POST', body: buildEnhanceFormData() });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Erreur serveur (${response.status})`);
    }
    return response.blob();
}

function applyEnhancements() { downloadEnhancedAudio(); }

async function downloadEnhancedAudio() {
    if (!currentFile) { showToast('Aucun fichier audio chargé', 'warning'); return; }
    showToast('⏳ Amélioration en cours…', 'info');
    try {
        const blob = await requestEnhancedBlob();
        const base = currentFile.name.replace(/\.[^.]+$/, '');
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `enhanced_${base}.wav`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        showToast('✅ Audio amélioré téléchargé', 'success');
    } catch (error) {
        console.error('Erreur amélioration:', error);
        showToast('❌ ' + error.message, 'error');
    }
}

async function previewEnhancements() {
    if (!currentFile) { showToast('Aucun fichier audio chargé', 'warning'); return; }
    showToast('⏳ Génération de l\'aperçu…', 'info');
    try {
        const blob = await requestEnhancedBlob();
        const url = URL.createObjectURL(blob);
        const preview = new Audio(url);
        preview.play();
        showToast('▶️ Lecture de l\'aperçu amélioré', 'success');
    } catch (error) {
        console.error('Erreur aperçu:', error);
        showToast('❌ ' + error.message, 'error');
    }
}

function resetEnhancements() {
    setSlider('noiseReduction', 50, 'noiseValue', '%');
    setSlider('amplification', 0, 'ampValue', ' dB');
    setSlider('bassEQ', 0, 'bassValue', ' dB');
    setSlider('midEQ', 0, 'midValue', ' dB');
    setSlider('trebleEQ', 0, 'trebleValue', ' dB');
    setSlider('normalization', 0, 'normValue', '%');
    showToast('↩️ Réglages réinitialisés', 'info');
}

function loadCurrentEnhancementSettings() {
    // Synchronise l'affichage des valeurs avec la position des curseurs
    syncDisplay('noiseReduction', 'noiseValue', '%');
    syncDisplay('amplification', 'ampValue', ' dB');
    syncDisplay('bassEQ', 'bassValue', ' dB');
    syncDisplay('midEQ', 'midValue', ' dB');
    syncDisplay('trebleEQ', 'trebleValue', ' dB');
    syncDisplay('normalization', 'normValue', '%');
}

/* ======================= UTILITAIRES ======================= */

function setSlider(sliderId, value, displayId, suffix) {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (slider) slider.value = value;
    if (display) display.textContent = value + suffix;
}

function syncDisplay(sliderId, displayId, suffix) {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (slider && display) display.textContent = slider.value + suffix;
}
