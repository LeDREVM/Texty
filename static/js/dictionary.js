/**
 * Transcripteur Audio Pro — Dictionnaire français <-> créole guadeloupéen
 * Interroge l'API /api/dictionary et /api/dictionary/all.
 */

let _dictMeta = null;
let _dictLoaded = false;

// Chargement paresseux : appelé par showTab('dictionnaire') à la première ouverture.
function ensureDictionaryLoaded() {
    if (_dictLoaded) return;
    _dictLoaded = true;
    initDictionary();
}

function initDictionary() {
    // Charge une fois les métadonnées + catégories (sans tout afficher)
    fetch('/api/dictionary/all')
        .then((r) => r.json())
        .then((data) => {
            if (!data.success) return;
            _dictMeta = data.meta || {};
            renderCategories(data.categories || []);
            showDictWarning(_dictMeta.avertissement);
        })
        .catch((err) => console.warn('Dictionnaire indisponible:', err));
}

function renderCategories(categories) {
    const container = document.getElementById('dictCategories');
    if (!container) return;
    container.innerHTML = '';

    const all = makeChip('Toutes', true, () => {
        setActiveChip(all);
        dictionaryShowAll();
    });
    container.appendChild(all);

    categories.forEach((cat) => {
        const chip = makeChip(cat, false, () => {
            setActiveChip(chip);
            filterByCategory(cat);
        });
        container.appendChild(chip);
    });
}

function makeChip(label, active, onClick) {
    const chip = document.createElement('span');
    chip.className = 'chip' + (active ? ' active' : '');
    chip.textContent = label;
    chip.addEventListener('click', onClick);
    return chip;
}

function setActiveChip(activeChip) {
    document.querySelectorAll('#dictCategories .chip').forEach((c) => c.classList.remove('active'));
    if (activeChip) activeChip.classList.add('active');
}

function dictionaryLookup() {
    const query = (document.getElementById('dictQuery').value || '').trim();
    if (!query) {
        showToast('Saisissez un mot à rechercher', 'warning');
        return;
    }
    const direction = document.getElementById('dictDirection').value;
    const mode = document.getElementById('dictMode').value;
    const params = new URLSearchParams({ q: query, direction: direction, mode: mode });

    fetch('/api/dictionary?' + params.toString())
        .then(async (r) => {
            const data = await r.json().catch(() => ({}));
            if (!r.ok || data.success === false) {
                throw new Error(data.error || `Erreur serveur (${r.status})`);
            }
            return data;
        })
        .then((data) => renderEntries(data.results, `« ${query} »`))
        .catch((err) => {
            console.error('Erreur dictionnaire:', err);
            showToast('❌ ' + err.message, 'error');
        });
}

function dictionaryShowAll() {
    fetch('/api/dictionary/all')
        .then((r) => r.json())
        .then((data) => renderEntries(data.entries, 'tout le lexique'))
        .catch((err) => showToast('❌ ' + err.message, 'error'));
}

function filterByCategory(category) {
    fetch('/api/dictionary/all?category=' + encodeURIComponent(category))
        .then((r) => r.json())
        .then((data) => renderEntries(data.entries, `catégorie « ${category} »`))
        .catch((err) => showToast('❌ ' + err.message, 'error'));
}

function renderEntries(entries, label) {
    const container = document.getElementById('dictionaryResults');
    if (!container) return;
    container.innerHTML = '';

    if (!entries || entries.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'dict-empty';
        empty.textContent = `Aucun résultat pour ${label || 'cette recherche'}.`;
        container.appendChild(empty);
        return;
    }

    entries.forEach((entry) => container.appendChild(buildEntry(entry)));
}

function buildEntry(entry) {
    const row = document.createElement('div');
    row.className = 'dict-entry';

    const fr = document.createElement('span');
    fr.className = 'dict-fr';
    fr.textContent = entry.fr || '';

    const arrow = document.createElement('span');
    arrow.className = 'dict-arrow';
    arrow.textContent = '↔';

    const cr = document.createElement('span');
    cr.className = 'dict-cr';
    cr.textContent = entry.cr || '';

    row.append(fr, arrow, cr);

    if (entry.category) {
        const cat = document.createElement('span');
        cat.className = 'dict-cat';
        cat.textContent = entry.category;
        row.appendChild(cat);
    }
    if (entry.notes) {
        const notes = document.createElement('span');
        notes.className = 'dict-notes';
        notes.textContent = entry.notes;
        row.appendChild(notes);
    }
    return row;
}

function showDictWarning(text) {
    const el = document.getElementById('dictWarning');
    if (!el || !text) return;
    el.textContent = '⚠️ ' + text;
    el.style.display = 'block';
}

/* ============================ TRADUCTION ============================ */

function translateText() {
    const input = document.getElementById('translateInput');
    const text = (input.value || '').trim();
    if (!text) {
        showToast('Saisissez un texte à traduire', 'warning');
        return;
    }
    const direction = document.getElementById('translateDirection').value;

    fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, direction: direction })
    })
        .then(async (r) => {
            const data = await r.json().catch(() => ({}));
            if (!r.ok || data.success === false) {
                throw new Error(data.error || `Erreur serveur (${r.status})`);
            }
            return data;
        })
        .then((data) => renderTranslation(data))
        .catch((err) => {
            console.error('Erreur traduction:', err);
            showToast('❌ ' + err.message, 'error');
        });
}

function renderTranslation(data) {
    const out = document.getElementById('translateOutput');
    if (!out) return;
    out.innerHTML = '';
    out.style.display = 'block';

    const result = document.createElement('div');
    result.className = 'translate-result';
    result.textContent = data.translation || '(vide)';
    out.appendChild(result);

    // Badge de méthode
    const badge = document.createElement('span');
    badge.className = 'translate-method';
    badge.textContent = data.method === 'model'
        ? '🧠 modèle NLLB' : '📖 dictionnaire (mot à mot, approximatif)';
    out.appendChild(badge);

    // Mots non traduits
    if (Array.isArray(data.unknown) && data.unknown.length) {
        const unknown = document.createElement('div');
        unknown.className = 'translate-unknown';
        unknown.textContent = 'Mots non trouvés : ' + data.unknown.join(', ');
        out.appendChild(unknown);
    }

    // Note éventuelle (repli dictionnaire)
    if (data.note) {
        const note = document.createElement('div');
        note.className = 'translate-note';
        note.textContent = 'ℹ️ ' + data.note;
        out.appendChild(note);
    }
}
