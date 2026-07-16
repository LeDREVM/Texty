/**
 * Transcripteur Audio Pro — Transcription, export & partage
 * Complète app.js (variables globales currentFile / currentTranscription, showToast…).
 */

// Historique d'export en mémoire (affiché dans l'onglet Export)
const exportHistory = [];

/* ============================ TRANSCRIPTION ============================ */

let _pollTimer = null;

function startTranscription() {
    if (!currentFile) {
        showToast('Veuillez d\'abord importer un fichier audio', 'warning');
        showTab('upload');
        return;
    }

    const btn = document.getElementById('transcribeBtn');
    const transcriptArea = document.getElementById('transcriptArea');

    // Paramètres
    const formData = new FormData();
    formData.append('audio', currentFile);
    formData.append('language', document.getElementById('language').value);
    formData.append('model', document.getElementById('model').value);
    formData.append('speakers', document.getElementById('speakers').value);
    formData.append('format', document.getElementById('outputFormat').value);

    const enhance = document.getElementById('enhanceAudio');
    formData.append('enhance', enhance && enhance.checked ? 'true' : 'false');

    // Reprend les réglages d'amélioration si présents
    const noise = document.getElementById('noiseReduction');
    const amp = document.getElementById('amplification');
    const norm = document.getElementById('normalization');
    if (noise) formData.append('noise_reduction', (parseFloat(noise.value) / 100).toFixed(2));
    if (amp) formData.append('amplification', amp.value);
    if (norm) formData.append('normalize', parseFloat(norm.value) > 0 ? 'true' : 'false');

    // UI : démarrage
    if (btn) btn.disabled = true;
    if (transcriptArea) transcriptArea.style.display = 'none';
    showProgress(0, 'Envoi du fichier…');

    // Transcription asynchrone : on lance un job puis on interroge son état.
    fetch(apiUrl('/api/transcribe_async'), { method: 'POST', body: formData })
        .then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                throw new Error(data.error || `Erreur serveur (${response.status})`);
            }
            return data;
        })
        .then((data) => pollJob(data.job_id))
        .catch((error) => {
            console.error('Erreur transcription:', error);
            showToast('❌ ' + error.message, 'error');
            endProgress();
        });
}

function pollJob(jobId) {
    let failures = 0;
    const tick = () => {
        fetch(apiUrl('/api/transcribe_status/' + jobId))
            .then(async (response) => {
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data.success === false) {
                    throw new Error(data.error || `Erreur serveur (${response.status})`);
                }
                return data;
            })
            .then((data) => {
                failures = 0;
                if (data.status === 'pending') {
                    showProgress(data.progress || 0, 'En file d\'attente…');
                    _pollTimer = setTimeout(tick, 2000);
                } else if (data.status === 'processing') {
                    showProgress(data.progress || 0, 'Transcription en cours…');
                    _pollTimer = setTimeout(tick, 2000);
                } else if (data.status === 'done') {
                    showProgress(100, 'Terminé');
                    currentTranscription = data.result;
                    renderTranscription(data.result);
                    saveToHistory(data.result);
                    showToast('✅ Transcription terminée !', 'success');
                    endProgress();
                } else {
                    throw new Error(data.error || 'Échec de la transcription');
                }
            })
            .catch((error) => {
                // Tolère quelques échecs réseau passagers avant d'abandonner
                failures += 1;
                if (failures <= 3) {
                    _pollTimer = setTimeout(tick, 3000);
                } else {
                    console.error('Erreur suivi transcription:', error);
                    showToast('❌ ' + error.message, 'error');
                    endProgress();
                }
            });
    };
    tick();
}

function showProgress(pct, text) {
    const container = document.getElementById('progressContainer');
    const fill = document.getElementById('progressFill');
    const percent = document.getElementById('progressPercent');
    const label = document.getElementById('progressText');
    if (container) container.style.display = 'block';
    if (fill) fill.style.width = (pct || 0) + '%';
    if (percent) percent.textContent = Math.round(pct || 0) + '%';
    if (label && text) label.textContent = text;
}

function endProgress() {
    if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
    const btn = document.getElementById('transcribeBtn');
    const container = document.getElementById('progressContainer');
    if (btn) btn.disabled = false;
    setTimeout(() => { if (container) container.style.display = 'none'; }, 900);
}

function renderTranscription(result) {
    const area = document.getElementById('transcriptArea');
    const editor = document.getElementById('transcriptResult');
    if (area) area.style.display = 'block';
    if (editor) editor.value = result.text || '';

    const words = (result.text || '').trim().split(/\s+/).filter(Boolean).length;
    setText('wordCount', `${words} mots`);

    let conf = '-';
    if (typeof result.language_probability === 'number') {
        conf = Math.round(result.language_probability * 100) + '%';
    }
    setText('confidence', `Confiance: ${conf}`);

    const t = typeof result.processing_time === 'number'
        ? result.processing_time.toFixed(1) + 's' : '-';
    setText('processingTime', `Temps: ${t}`);
}

/* ============================ HISTORIQUE ============================ */
// Conservé dans le navigateur (localStorage) : la liste des transcriptions faites,
// rechargeable et ré-exportable, persistante après rechargement de la page.

const HISTORY_KEY = 'texty_history';
const HISTORY_MAX = 20;

function loadHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch (e) {
        return [];
    }
}

function persistHistory(list) {
    try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
    } catch (e) {
        // Quota dépassé : on réduit la liste et on réessaie
        if (list.length > 1) persistHistory(list.slice(0, Math.ceil(list.length / 2)));
    }
}

function saveToHistory(result) {
    if (!result || !result.text) return;
    const list = loadHistory();
    list.unshift({
        id: String(Date.now()) + '_' + Math.round(Math.random() * 1e6),
        filename: result.filename || 'transcription',
        date: new Date().toISOString(),
        model: result.model_used || '',
        text: result.text,
        segments: result.segments || [],
        formatted_output: result.formatted_output
    });
    if (list.length > HISTORY_MAX) list.length = HISTORY_MAX;
    persistHistory(list);
    renderHistory();
}

function renderHistory() {
    const panel = document.getElementById('transcriptionHistory');
    const listEl = document.getElementById('historyList');
    if (!listEl) return;
    const list = loadHistory();

    if (list.length === 0) {
        if (panel) panel.style.display = 'none';
        listEl.innerHTML = '';
        return;
    }
    if (panel) panel.style.display = 'block';
    listEl.innerHTML = '';

    list.forEach((entry) => {
        const words = (entry.text || '').trim().split(/\s+/).filter(Boolean).length;
        const d = new Date(entry.date);
        const dateStr = isNaN(d.getTime()) ? '' : d.toLocaleString();

        const item = document.createElement('div');
        item.className = 'history-item';

        const meta = document.createElement('div');
        meta.className = 'history-meta';
        const name = document.createElement('span');
        name.className = 'history-name';
        name.textContent = '📄 ' + entry.filename;
        const sub = document.createElement('span');
        sub.className = 'history-sub';
        sub.textContent = `${dateStr} · ${words} mots` + (entry.model ? ` · ${entry.model}` : '');
        meta.append(name, sub);

        const actions = document.createElement('div');
        actions.className = 'history-actions';
        const openBtn = document.createElement('button');
        openBtn.className = 'btn btn-small';
        openBtn.textContent = 'Ouvrir';
        openBtn.addEventListener('click', () => restoreFromHistory(entry.id));
        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-small btn-secondary';
        delBtn.textContent = '🗑️';
        delBtn.setAttribute('aria-label', 'Supprimer de l\'historique');
        delBtn.addEventListener('click', () => deleteFromHistory(entry.id));
        actions.append(openBtn, delBtn);

        item.append(meta, actions);
        listEl.appendChild(item);
    });
}

function restoreFromHistory(id) {
    const entry = loadHistory().find((e) => e.id === id);
    if (!entry) return;
    currentTranscription = {
        text: entry.text,
        segments: entry.segments || [],
        filename: entry.filename,
        formatted_output: entry.formatted_output
    };
    renderTranscription(currentTranscription);
    showTab('transcribe');
    showToast('Transcription restaurée : ' + entry.filename, 'success');
}

function deleteFromHistory(id) {
    persistHistory(loadHistory().filter((e) => e.id !== id));
    renderHistory();
}

function clearHistory() {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
    showToast('Historique vidé', 'info');
}

document.addEventListener('DOMContentLoaded', renderHistory);

/* ============================ EXPORT ============================ */

const EXPORT_META = {
    txt:  { format: 'text', ext: 'txt',  mime: 'text/plain' },
    srt:  { format: 'srt',  ext: 'srt',  mime: 'text/plain' },
    vtt:  { format: 'vtt',  ext: 'vtt',  mime: 'text/vtt' },
    json: { format: 'json', ext: 'json', mime: 'application/json' },
    docx: { format: 'docx', ext: 'doc',  mime: 'application/msword' },
    csv:  { format: 'csv',  ext: 'csv',  mime: 'text/csv' }
};

function exportFormat(kind) {
    if (!currentTranscription || !currentTranscription.text) {
        showToast('Aucune transcription à exporter', 'warning');
        return;
    }
    const meta = EXPORT_META[kind];
    if (!meta) { showToast('Format inconnu', 'error'); return; }

    fetch(apiUrl('/api/convert_format'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: currentTranscription.text,
            segments: currentTranscription.segments || [],
            format: meta.format
        })
    })
        .then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                throw new Error(data.error || `Erreur serveur (${response.status})`);
            }
            return data;
        })
        .then((data) => {
            const base = (currentTranscription.filename || 'transcription').replace(/\.[^.]+$/, '');
            const filename = `${base}.${meta.ext}`;
            downloadBlob(new Blob([data.content], { type: meta.mime }), filename);
            addToHistory(filename);
            showToast(`📥 Export ${kind.toUpperCase()} téléchargé`, 'success');
        })
        .catch((error) => {
            console.error('Erreur export:', error);
            showToast('❌ ' + error.message, 'error');
        });
}

function addToHistory(filename) {
    exportHistory.unshift({ name: filename, time: new Date().toLocaleTimeString() });
    updateExportPreview();
}

function updateExportPreview() {
    const list = document.getElementById('exportHistory');
    if (!list) return;
    if (exportHistory.length === 0) {
        list.innerHTML = '<div class="history-empty"><p>Aucun export récent</p></div>';
        return;
    }
    list.innerHTML = '';
    exportHistory.slice(0, 10).forEach((item) => {
        const div = document.createElement('div');
        div.className = 'history-item';
        const name = document.createElement('span');
        name.textContent = '📄 ' + item.name;
        const time = document.createElement('span');
        time.textContent = item.time;
        div.append(name, time);
        list.appendChild(div);
    });
}

/* ============================ PARTAGE ============================ */

function transcriptTextOrWarn() {
    if (!currentTranscription || !currentTranscription.text) {
        showToast('Aucune transcription à partager', 'warning');
        return null;
    }
    return currentTranscription.text;
}

function shareTranscript() {
    if (!transcriptTextOrWarn()) return;
    const modal = document.getElementById('shareModal');
    if (modal) modal.style.display = 'flex';
}

function shareViaEmail() { emailTranscript(); }

function emailTranscript() {
    const text = transcriptTextOrWarn();
    if (!text) return;
    const subject = encodeURIComponent('Transcription — Transcripteur Audio Pro');
    const body = encodeURIComponent(text.slice(0, 1800));
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
}

function shareViaWhatsApp() {
    const text = transcriptTextOrWarn();
    if (!text) return;
    window.open('https://wa.me/?text=' + encodeURIComponent(text.slice(0, 1800)), '_blank');
}

function shareViaDropbox() {
    showToast('Intégration Dropbox non configurée sur ce serveur', 'info');
}

function generateShareLink() {
    const text = transcriptTextOrWarn();
    if (!text) return;
    // Lien local (Blob) : téléchargeable sur cet appareil. Un vrai lien partagé
    // nécessiterait un stockage côté serveur.
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
    const block = document.getElementById('shareLink');
    const input = document.getElementById('shareLinkInput');
    if (input) input.value = url;
    if (block) block.style.display = 'block';
    showToast('Lien local généré (valable sur cet appareil)', 'info');
}

function copyShareLink() {
    const input = document.getElementById('shareLinkInput');
    if (!input || !input.value) return;
    navigator.clipboard.writeText(input.value)
        .then(() => showToast('Lien copié', 'success'))
        .catch(() => { input.select(); document.execCommand('copy'); showToast('Lien copié', 'success'); });
}

function printTranscript() {
    const text = transcriptTextOrWarn();
    if (!text) return;
    const win = window.open('', '_blank');
    if (!win) { showToast('Impossible d\'ouvrir la fenêtre d\'impression', 'error'); return; }
    const safe = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    win.document.write(
        '<html><head><title>Transcription</title></head><body>' +
        '<h1>Transcription Audio</h1><pre style="white-space:pre-wrap;font-family:Segoe UI,Arial,sans-serif;line-height:1.6">' +
        safe + '</pre></body></html>'
    );
    win.document.close();
    win.focus();
    win.print();
}

/* ============================ UTILITAIRES ============================ */

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}
