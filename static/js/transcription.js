/**
 * Transcripteur Audio Pro — Transcription, export & partage
 * Complète app.js (variables globales currentFile / currentTranscription, showToast…).
 */

// Historique d'export en mémoire (affiché dans l'onglet Export)
const exportHistory = [];

/* ============================ TRANSCRIPTION ============================ */

let _progressTimer = null;

function startTranscription() {
    if (!currentFile) {
        showToast('Veuillez d\'abord importer un fichier audio', 'warning');
        showTab('upload');
        return;
    }

    const btn = document.getElementById('transcribeBtn');
    const progressContainer = document.getElementById('progressContainer');
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
    btn.disabled = true;
    if (transcriptArea) transcriptArea.style.display = 'none';
    startProgress();

    fetch('/api/transcribe', { method: 'POST', body: formData })
        .then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                throw new Error(data.error || `Erreur serveur (${response.status})`);
            }
            return data;
        })
        .then((result) => {
            completeProgress();
            currentTranscription = result;
            renderTranscription(result);
            showToast('✅ Transcription terminée !', 'success');
        })
        .catch((error) => {
            console.error('Erreur transcription:', error);
            showToast('❌ ' + error.message, 'error');
        })
        .finally(() => {
            btn.disabled = false;
            stopProgress();
            setTimeout(() => {
                if (progressContainer) progressContainer.style.display = 'none';
            }, 600);
        });
}

function startProgress() {
    const container = document.getElementById('progressContainer');
    const fill = document.getElementById('progressFill');
    const percent = document.getElementById('progressPercent');
    const text = document.getElementById('progressText');
    if (!container) return;

    container.style.display = 'block';
    let value = 0;
    if (text) text.textContent = 'Traitement de l\'audio…';
    _progressTimer = setInterval(() => {
        // Progression asymptotique jusqu'à 90 % en attendant la réponse
        value += Math.max(0.5, (90 - value) * 0.08);
        if (value > 90) value = 90;
        if (fill) fill.style.width = value + '%';
        if (percent) percent.textContent = Math.round(value) + '%';
    }, 400);
}

function completeProgress() {
    const fill = document.getElementById('progressFill');
    const percent = document.getElementById('progressPercent');
    const text = document.getElementById('progressText');
    if (fill) fill.style.width = '100%';
    if (percent) percent.textContent = '100%';
    if (text) text.textContent = 'Terminé';
}

function stopProgress() {
    if (_progressTimer) { clearInterval(_progressTimer); _progressTimer = null; }
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

    fetch('/api/convert_format', {
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
