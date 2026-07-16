/**
 * Transcripteur Audio Pro — Séquences : découpage audio + playlist + transcription en lot.
 * Découpe le fichier chargé en séquences numérotées (WAV 16 kHz mono, côté navigateur),
 * transcrit en lot via l'API async, et exporte manifest.csv + audios (jeu de données ASR).
 */

let decodedAudio = null;     // AudioBuffer décodé (mis en cache)
let decodedFor = null;       // fichier pour lequel decodedAudio est valide
let playlistItems = [];      // [{seq, start, end, text, status, progress}]

/* ----------------------- décodage & découpe ----------------------- */

async function ensureDecoded() {
    if (decodedAudio && decodedFor === currentFile) return decodedAudio;
    if (!currentFile) throw new Error('Aucun fichier audio chargé');
    const ctx = audioContext || new (window.AudioContext || window.webkitAudioContext)();
    const buf = await currentFile.arrayBuffer();
    decodedAudio = await ctx.decodeAudioData(buf.slice(0));
    decodedFor = currentFile;
    return decodedAudio;
}

async function autoSplitAudio() {
    if (!currentFile) {
        showToast('Charge d\'abord un audio (onglet Import)', 'warning');
        showTab('upload');
        return;
    }
    const input = document.getElementById('segDuration');
    const dur = Math.min(30, Math.max(5, parseInt(input && input.value, 10) || 30));
    showToast('Analyse de l\'audio…', 'info');
    try {
        await ensureDecoded();
        const total = decodedAudio.duration;
        playlistItems = [];
        let i = 0;
        for (let t = 0; t < total - 0.05; t += dur) {
            i += 1;
            playlistItems.push({ seq: i, start: t, end: Math.min(t + dur, total),
                                 text: '', status: 'pending', progress: 0 });
        }
        renderPlaylist();
        showToast(`${playlistItems.length} séquence(s) de ${dur}s créée(s)`, 'success');
    } catch (e) {
        console.error(e);
        showToast('❌ ' + e.message, 'error');
    }
}

function addSelectionToPlaylist() {
    if (!currentFile) { showToast('Aucun audio chargé', 'warning'); return; }
    const s = Math.min(selectionStart, selectionEnd);
    const e = Math.max(selectionStart, selectionEnd);
    if (e - s < 0.2) {
        showToast('Marque d\'abord une sélection (onglet Édition Audio)', 'warning');
        return;
    }
    playlistItems.push({ seq: playlistItems.length + 1, start: s, end: e,
                         text: '', status: 'pending', progress: 0 });
    renumber();
    renderPlaylist();
    showToast('Séquence ajoutée', 'success');
}

function renumber() { playlistItems.forEach((it, i) => { it.seq = i + 1; }); }
function seqName(item) { return 'seq_' + String(item.seq).padStart(3, '0') + '.wav'; }

/* ----------------------- rendu de la playlist ----------------------- */

function renderPlaylist() {
    const list = document.getElementById('seqList');
    const actions = document.getElementById('seqActions');
    if (!list) return;

    if (playlistItems.length === 0) {
        list.innerHTML = '<p class="dict-empty">Charge un audio puis « Découper automatiquement ».</p>';
        if (actions) actions.style.display = 'none';
        return;
    }
    if (actions) actions.style.display = 'flex';
    list.innerHTML = '';

    playlistItems.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'seq-item';

        const num = document.createElement('span');
        num.className = 'seq-num';
        num.textContent = String(item.seq).padStart(3, '0');

        const time = document.createElement('span');
        time.className = 'seq-time';
        time.textContent = `${formatTime(item.start)} – ${formatTime(item.end)}`;

        const badge = document.createElement('span');
        badge.className = 'seq-status seq-' + item.status;
        badge.textContent = {
            pending: '⏳ en attente', processing: `⚙️ ${item.progress || 0}%`,
            done: '✅ fait', error: '❌ erreur'
        }[item.status] || item.status;

        const text = document.createElement('input');
        text.type = 'text';
        text.className = 'seq-text';
        text.placeholder = 'transcription…';
        text.value = item.text || '';
        text.addEventListener('input', () => { item.text = text.value; });

        const play = document.createElement('button');
        play.className = 'btn btn-small btn-secondary';
        play.textContent = '▶️';
        play.setAttribute('aria-label', 'Écouter la séquence');
        play.addEventListener('click', () => previewSegment(item));

        const tr = document.createElement('button');
        tr.className = 'btn btn-small';
        tr.textContent = 'Transcrire';
        tr.addEventListener('click', () => transcribeItem(item));

        const del = document.createElement('button');
        del.className = 'btn btn-small btn-secondary';
        del.textContent = '🗑️';
        del.setAttribute('aria-label', 'Supprimer la séquence');
        del.addEventListener('click', () => { playlistItems = playlistItems.filter(x => x !== item); renumber(); renderPlaylist(); });

        const actionsCell = document.createElement('div');
        actionsCell.className = 'seq-actions-cell';
        actionsCell.append(play, tr, del);

        row.append(num, time, badge, text, actionsCell);
        list.appendChild(row);
    });
}

function updateItemStatus(item) {
    // maj légère du badge sans tout re-render (pendant la progression)
    const list = document.getElementById('seqList');
    if (!list) return;
    const rows = list.querySelectorAll('.seq-item');
    const idx = playlistItems.indexOf(item);
    if (idx < 0 || !rows[idx]) return;
    const badge = rows[idx].querySelector('.seq-status');
    if (badge) {
        badge.className = 'seq-status seq-' + item.status;
        badge.textContent = item.status === 'processing' ? `⚙️ ${item.progress || 0}%`
            : ({ pending: '⏳ en attente', done: '✅ fait', error: '❌ erreur' }[item.status] || item.status);
    }
}

/* ----------------------- audio (découpe WAV 16k mono) ----------------------- */

async function segmentToWav(item) {
    await ensureDecoded();
    const dur = item.end - item.start;
    const targetSR = 16000;
    const frames = Math.max(1, Math.floor(dur * targetSR));
    const off = new OfflineAudioContext(1, frames, targetSR);
    const src = off.createBufferSource();
    src.buffer = decodedAudio;
    src.connect(off.destination);
    src.start(0, item.start, dur);
    const rendered = await off.startRendering();
    return encodeWav(rendered.getChannelData(0), targetSR);
}

function encodeWav(samples, sr) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const wr = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
    wr(0, 'RIFF'); view.setUint32(4, 36 + samples.length * 2, true); wr(8, 'WAVE'); wr(12, 'fmt ');
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, sr, true); view.setUint32(28, sr * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    wr(36, 'data'); view.setUint32(40, samples.length * 2, true);
    let o = 44;
    for (let i = 0; i < samples.length; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        o += 2;
    }
    return new Blob([view], { type: 'audio/wav' });
}

async function previewSegment(item) {
    try {
        const blob = await segmentToWav(item);
        new Audio(URL.createObjectURL(blob)).play();
    } catch (e) { showToast('❌ ' + e.message, 'error'); }
}

/* ----------------------- transcription en lot ----------------------- */

function transcribeBlobAsync(blob, filename, params) {
    return new Promise((resolve, reject) => {
        const fd = new FormData();
        fd.append('audio', blob, filename);
        fd.append('language', params.language);
        fd.append('model', params.model);
        fd.append('speakers', 'false');
        fd.append('enhance', 'false');
        fd.append('format', 'text');
        fetch(apiUrl('/api/transcribe_async'), { method: 'POST', body: fd })
            .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok || d.success === false) throw new Error(d.error || `Erreur ${r.status}`); return d; })
            .then((d) => {
                let fails = 0;
                const poll = () => {
                    fetch(apiUrl('/api/transcribe_status/' + d.job_id))
                        .then(async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok || j.success === false) throw new Error(j.error || `Erreur ${r.status}`); return j; })
                        .then((j) => {
                            if (j.status === 'done') resolve((j.result && j.result.text) || '');
                            else if (j.status === 'error') reject(new Error(j.error || 'échec'));
                            else { fails = 0; if (params.onProgress) params.onProgress(j.progress || 0); setTimeout(poll, 2000); }
                        })
                        .catch((e) => { fails += 1; if (fails <= 3) setTimeout(poll, 3000); else reject(e); });
                };
                poll();
            })
            .catch(reject);
    });
}

function transcribeParams() {
    const lang = document.getElementById('language');
    const model = document.getElementById('model');
    return { language: (lang && lang.value) || 'fr', model: (model && model.value) || 'small' };
}

async function transcribeItem(item) {
    item.status = 'processing'; item.progress = 0; updateItemStatus(item);
    try {
        const blob = await segmentToWav(item);
        const params = transcribeParams();
        params.onProgress = (p) => { item.progress = p; updateItemStatus(item); };
        item.text = await transcribeBlobAsync(blob, seqName(item), params);
        item.status = 'done';
    } catch (e) {
        console.error(e); item.status = 'error'; item.error = e.message;
        showToast(`❌ Séquence ${item.seq}: ${e.message}`, 'error');
    }
    renderPlaylist();
}

async function transcribeQueue() {
    if (!playlistItems.length) { showToast('Playlist vide', 'warning'); return; }
    const btn = document.getElementById('seqTranscribeBtn');
    if (btn) btn.disabled = true;
    showToast('Transcription du lot en cours…', 'info');
    for (const item of playlistItems) {
        if (item.status === 'done') continue;
        await transcribeItem(item);
    }
    if (btn) btn.disabled = false;
    showToast('✅ Lot transcrit', 'success');
}

/* ----------------------- export (manifest + audios) ----------------------- */

async function exportPlaylistManifest() {
    if (!playlistItems.length) { showToast('Playlist vide', 'warning'); return; }
    let csv = 'audio_path,text\n';
    playlistItems.forEach((it) => {
        const t = (it.text || '').replace(/"/g, '""');
        csv += `${seqName(it)},"${t}"\n`;
    });
    downloadBlob(new Blob([csv], { type: 'text/csv' }), 'manifest.csv');

    showToast('Téléchargement des audios numérotés…', 'info');
    for (const it of playlistItems) {
        const blob = await segmentToWav(it);
        downloadBlob(blob, seqName(it));
        await new Promise((r) => setTimeout(r, 300)); // évite le blocage des téléchargements multiples
    }
    showToast('📥 manifest.csv + audios téléchargés', 'success');
}

function clearPlaylist() {
    playlistItems = [];
    renderPlaylist();
}
