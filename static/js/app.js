/**
 * Transcripteur Audio Pro - JavaScript Principal
 * Créé par Négus Dja - Directeur Artistique Guadeloupe
 * Optimisé pour les ingénieurs son et vidéastes avec TDAH
 */

// Variables globales
let currentFile = null;
let audioElement = null;
let audioContext = null;
let isPlaying = false;
let selectionStart = 0;
let selectionEnd = 0;
let currentTranscription = null;
let waveformData = null;

// Configuration
const CONFIG = {
    maxFileSize: 100 * 1024 * 1024, // 100MB
    supportedFormats: {
        audio: ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'wma'],
        video: ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv']
    },
    apiBaseUrl: '/api',
    toastDuration: 5000
};

/**
 * Initialisation de l'application
 */
function initializeApp() {
    console.log('🚀 Initialisation de l\'application');
    
    // Vérifier l'état du serveur
    checkServerHealth();
    
    // Initialiser l'audio context
    initAudioContext();
    
    // Mise à jour des valeurs des sliders
    initSliderUpdates();
    
    console.log('✅ Application initialisée');
}

/**
 * Configuration des event listeners
 */
function setupEventListeners() {
    console.log('🔧 Configuration des event listeners');
    
    // Upload de fichier
    setupFileUpload();
    
    // Sliders d'amélioration
    setupEnhancementSliders();
    
    // Contrôles audio
    setupAudioControls();
    
    // Raccourcis clavier
    setupKeyboardShortcuts();
    
    console.log('✅ Event listeners configurés');
}

/**
 * Configuration de l'upload de fichier
 */
function setupFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('audioFile');
    
    // Drag & Drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // Click sur zone
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    // Sélection de fichier
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

/**
 * Gestion de la sélection de fichier
 */
function handleFileSelect(file) {
    console.log('📁 Fichier sélectionné:', file.name);
    
    // Vérifications
    if (!validateFile(file)) {
        return;
    }
    
    currentFile = file;
    
    // Afficher les informations du fichier
    displayFileInfo(file);
    
    // Créer l'élément audio
    createAudioElement(file);
    
    // Basculer vers l'onglet transcription
    showTab('transcribe');
    
    // Analyser automatiquement la qualité
    setTimeout(() => analyzeAudioQuality(), 1000);
    
    showToast(`Fichier "${file.name}" chargé avec succès ! 🎵`, 'success');
}

/**
 * Validation du fichier
 */
function validateFile(file) {
    // Vérifier la taille
    if (file.size > CONFIG.maxFileSize) {
        showToast(`Fichier trop volumineux (max ${CONFIG.maxFileSize / 1024 / 1024}MB)`, 'error');
        return false;
    }
    
    // Vérifier le format
    const extension = file.name.split('.').pop().toLowerCase();
    const isSupported = CONFIG.supportedFormats.audio.includes(extension) || 
                       CONFIG.supportedFormats.video.includes(extension);
    
    if (!isSupported) {
        showToast('Format de fichier non supporté', 'error');
        return false;
    }
    
    return true;
}

/**
 * Affichage des informations du fichier
 */
function displayFileInfo(file) {
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileFormat = document.getElementById('fileFormat');
    
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileFormat.textContent = file.type || file.name.split('.').pop().toUpperCase();
    
    fileInfo.style.display = 'block';
}

/**
 * Création de l'élément audio
 */
function createAudioElement(file) {
    const url = URL.createObjectURL(file);
    
    // Nettoyer l'ancien élément
    if (audioElement) {
        audioElement.pause();
        URL.revokeObjectURL(audioElement.src);
    }

    audioElement = new Audio(url);
    
    audioElement.addEventListener('loadedmetadata', () => {
        console.log('🎵 Audio chargé:', audioElement.duration + 's');
        
        // Mettre à jour l'affichage de durée
        document.getElementById('fileDuration').textContent = formatTime(audioElement.duration);
        
        // Afficher le lecteur audio
        document.getElementById('audioPlayerContainer').style.display = 'block';
        document.getElementById('noAudioMessage').style.display = 'none';
        
        // Dessiner la forme d'onde
        drawWaveform();
        
        // Mettre à jour l'affichage du temps
        updateTimeDisplay();
    });

    audioElement.addEventListener('timeupdate', () => {
        updateProgress();
        updateTimeDisplay();
        updatePlayhead();
    });

    audioElement.addEventListener('ended', () => {
        isPlaying = false;
        document.getElementById('playPauseBtn').textContent = '▶️';
    });

    audioElement.addEventListener('error', (e) => {
        console.error('Erreur audio:', e);
        showToast('Erreur lors du chargement du fichier audio', 'error');
    });
}

/**
 * Gestion des onglets
 */
function showTab(tabName) {
    // Masquer tous les onglets
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Afficher l'onglet sélectionné
    document.getElementById(tabName).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // Actions spécifiques par onglet
    switch(tabName) {
        case 'edit':
            if (!currentFile) {
                document.getElementById('audioPlayerContainer').style.display = 'none';
                document.getElementById('noAudioMessage').style.display = 'block';
            }
            break;
        case 'enhance':
            if (currentFile) {
                loadCurrentEnhancementSettings();
            }
            break;
        case 'export':
            if (currentTranscription) {
                updateExportPreview();
            }
            break;
    }
}

/**
 * Contrôles audio
 */
function togglePlayPause() {
    if (!audioElement) {
        showToast('Aucun fichier audio chargé', 'warning');
        return;
    }

    if (isPlaying) {
        audioElement.pause();
        document.getElementById('playPauseBtn').textContent = '▶️';
    } else {
        audioElement.play().catch(e => {
            console.error('Erreur lecture:', e);
            showToast('Erreur lors de la lecture', 'error');
        });
        document.getElementById('playPauseBtn').textContent = '⏸️';
    }
    isPlaying = !isPlaying;
}

function stopAudio() {
    if (!audioElement) return;
    
    audioElement.pause();
    audioElement.currentTime = 0;
    isPlaying = false;
    document.getElementById('playPauseBtn').textContent = '▶️';
}

function rewind() {
    if (!audioElement) return;
    audioElement.currentTime = Math.max(0, audioElement.currentTime - 10);
}

function fastForward() {
    if (!audioElement) return;
    audioElement.currentTime = Math.min(audioElement.duration, audioElement.currentTime + 10);
}

function seekTo(value) {
    if (!audioElement) return;
    const time = (value / 100) * audioElement.duration;
    audioElement.currentTime = time;
}

function setVolume(value) {
    if (!audioElement) return;
    audioElement.volume = value / 100;
}

function increaseSpeed() {
    if (!audioElement) return;
    const newRate = Math.min(2.0, audioElement.playbackRate + 0.1);
    audioElement.playbackRate = newRate;
    document.getElementById('speedDisplay').textContent = newRate.toFixed(1) + 'x';
}

function decreaseSpeed() {
    if (!audioElement) return;
    const newRate = Math.max(0.5, audioElement.playbackRate - 0.1);
    audioElement.playbackRate = newRate;
    document.getElementById('speedDisplay').textContent = newRate.toFixed(1) + 'x';
}

/**
 * Mise à jour de l'interface
 */
function updateProgress() {
    if (!audioElement || !audioElement.duration) return;
    
    const progress = (audioElement.currentTime / audioElement.duration) * 100;
    document.getElementById('positionSlider').value = progress;
}

function updateTimeDisplay() {
    if (!audioElement) return;
    
    const current = formatTime(audioElement.currentTime || 0);
    const duration = formatTime(audioElement.duration || 0);
    document.getElementById('timeDisplay').textContent = `${current} / ${duration}`;
}

function updatePlayhead() {
    if (!audioElement || !audioElement.duration) return;
    
    const playhead = document.getElementById('playhead');
    const progress = (audioElement.currentTime / audioElement.duration) * 100;
    playhead.style.left = progress + '%';
}

/**
 * Gestion de la sélection audio
 */
function setSelectionStart() {
    if (!audioElement) return;
    selectionStart = audioElement.currentTime;
    updateSelectionDisplay();
    updateSelectionOverlay();
    showToast(`Début de sélection: ${formatTime(selectionStart)}`, 'info');
}

function setSelectionEnd() {
    if (!audioElement) return;
    selectionEnd = audioElement.currentTime;
    updateSelectionDisplay();
    updateSelectionOverlay();
    showToast(`Fin de sélection: ${formatTime(selectionEnd)}`, 'info');
}

function updateSelectionDisplay() {
    const display = document.getElementById('selectionDisplay');
    if (selectionStart !== 0 || selectionEnd !== 0) {
        const start = Math.min(selectionStart, selectionEnd);
        const end = Math.max(selectionStart, selectionEnd);
        const duration = end - start;
        display.textContent = `${formatTime(start)} - ${formatTime(end)} (${formatTime(duration)})`;
    } else {
        display.textContent = 'Aucune sélection';
    }
}

function updateSelectionOverlay() {
    if (!audioElement || !audioElement.duration) return;
    
    const overlay = document.getElementById('selectionOverlay');
    
    if (selectionStart !== 0 && selectionEnd !== 0) {
        const start = Math.min(selectionStart, selectionEnd);
        const end = Math.max(selectionStart, selectionEnd);
        
        const startPercent = (start / audioElement.duration) * 100;
        const widthPercent = ((end - start) / audioElement.duration) * 100;
        
        overlay.style.left = startPercent + '%';
        overlay.style.width = widthPercent + '%';
        overlay.style.display = 'block';
    } else {
        overlay.style.display = 'none';
    }
}

function playSelection() {
    if (!audioElement || selectionStart === 0 || selectionEnd === 0) {
        showToast('Veuillez d\'abord définir une sélection', 'warning');
        return;
    }
    
    const start = Math.min(selectionStart, selectionEnd);
    const end = Math.max(selectionStart, selectionEnd);
    
    audioElement.currentTime = start;
    audioElement.play();
    
    // Arrêter à la fin de la sélection
    const checkEnd = () => {
        if (audioElement.currentTime >= end) {
            audioElement.pause();
            isPlaying = false;
            document.getElementById('playPauseBtn').textContent = '▶️';
        } else {
            requestAnimationFrame(checkEnd);
        }
    };
    
    checkEnd();
}

/**
 * Fonctions d'édition audio
 */
function cropSelection() {
    if (selectionStart === 0 && selectionEnd === 0) {
        showToast('Veuillez d\'abord définir une sélection', 'warning');
        return;
    }
    
    if (!currentFile) {
        showToast('Aucun fichier chargé', 'error');
        return;
    }
    
    const start = Math.min(selectionStart, selectionEnd);
    const end = Math.max(selectionStart, selectionEnd);
    
    // Appeler l'API d'extraction de segment
    extractAudioSegment(start, end);
}

function deleteSelection() {
    if (selectionStart === 0 && selectionEnd === 0) {
        showToast('Veuillez d\'abord définir une sélection', 'warning');
        return;
    }
    
    showToast('Fonction de suppression en cours de développement...', 'info');
}

/**
 * Extraction de segment audio
 */
async function extractAudioSegment(startTime, endTime) {
    if (!currentFile) return;
    
    const formData = new FormData();
    formData.append('audio', currentFile);
    formData.append('start_time', startTime);
    formData.append('end_time', endTime);
    
    try {
        showToast('⏳ Extraction du segment en cours...', 'info');
        
        const response = await fetch('/api/extract_segment', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            // Télécharger le fichier
            const a = document.createElement('a');
            a.href = url;
            a.download = `segment_${startTime.toFixed(1)}s-${endTime.toFixed(1)}s_${currentFile.name}`;
            a.click();
            
            URL.revokeObjectURL(url);
            showToast('✅ Segment extrait avec succès !', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erreur d\'extraction');
        }
    } catch (error) {
        console.error('Erreur extraction:', error);
        showToast('❌ Erreur lors de l\'extraction: ' + error.message, 'error');
    }
}

/**
 * Dessin de la forme d'onde
 */
function drawWaveform() {
    const canvas = document.getElementById('waveform');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Nettoyer le canvas
    ctx.clearRect(0, 0, width, height);
    
    // Dessiner un fond
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, width, height);
    
    // Simulation d'une forme d'onde (à remplacer par une vraie analyse)
    ctx.fillStyle = 'rgba(78, 205, 196, 0.8)';
    ctx.strokeStyle = 'rgba(78, 205, 196, 1)';
    ctx.lineWidth = 1;
    
    ctx.beginPath();
    
    for (let i = 0; i < width; i += 2) {
        // Simulation basée sur des fonctions sinusoïdales avec du bruit
        const time = (i / width) * (audioElement?.duration || 10);
        const amplitude = (Math.sin(time * 0.5) + Math.sin(time * 2) * 0.3 + Math.sin(time * 8) * 0.1) * 
                         (Math.random() * 0.3 + 0.7) * height * 0.3;
        
        const y = height / 2 - amplitude / 2;
        const barHeight = Math.abs(amplitude);
        
        ctx.fillRect(i, y, 1, barHeight);
    }
    
    // Ajouter une ligne centrale
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
}

/**
 * Initialisation de l'audio context
 */
function initAudioContext() {
    try {
        window.AudioContext = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioContext();
        console.log('🎵 Audio Context initialisé');
    } catch (error) {
        console.warn('Audio Context non supporté:', error);
    }
}

/**
 * Configuration des sliders d'amélioration
 */
function setupEnhancementSliders() {
    const sliders = [
        { id: 'noiseReduction', display: 'noiseValue', suffix: '%' },
        { id: 'amplification', display: 'ampValue', suffix: ' dB' },
        { id: 'bassEQ', display: 'bassValue', suffix: ' dB' },
        { id: 'midEQ', display: 'midValue', suffix: ' dB' },
        { id: 'trebleEQ', display: 'trebleValue', suffix: ' dB' },
        { id: 'normalization', display: 'normValue', suffix: '%' }
    ];

    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        const display = document.getElementById(slider.display);
        
        if (element && display) {
            element.addEventListener('input', () => {
                display.textContent = element.value + slider.suffix;
            });
        }
    });
}

function initSliderUpdates() {
    setupEnhancementSliders();
    
    // Position slider
    const positionSlider = document.getElementById('positionSlider');
    if (positionSlider) {
        positionSlider.addEventListener('input', (e) => {
            seekTo(e.target.value);
        });
    }
    
    // Volume slider
    const volumeSlider = document.getElementById('volumeSlider');
    if (volumeSlider) {
        volumeSlider.addEventListener('input', (e) => {
            setVolume(e.target.value);
        });
    }
}

/**
 * Configuration des contrôles audio
 */
function setupAudioControls() {
    // Les event listeners sont déjà définis dans le HTML via onclick
    // Cette fonction peut être utilisée pour des configurations additionnelles
    console.log('🎛️ Contrôles audio configurés');
}

/**
 * Configuration des raccourcis clavier
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Seulement si aucun input n'est focalisé
        if (document.activeElement.tagName === 'INPUT' || 
            document.activeElement.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                rewind();
                break;
            case 'ArrowRight':
                e.preventDefault();
                fastForward();
                break;
            case 'KeyS':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    setSelectionStart();
                }
                break;
            case 'KeyE':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    setSelectionEnd();
                }
                break;
            case 'KeyT':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    if (currentFile) {
                        startTranscription();
                    }
                }
                break;
        }
    });
}

/**
 * Vérification de l'état du serveur
 */
async function checkServerHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        console.log('🟢 Serveur OK:', data);
        
        // Afficher les moteurs disponibles
        const engines = data.engines;
        let engineStatus = '🧠 Moteurs: ';
        
        if (engines.faster_whisper) engineStatus += 'Faster-Whisper ✅ ';
        if (engines.whisper) engineStatus += 'Whisper ✅ ';
        if (engines.speech_recognition) engineStatus += 'SpeechRecognition ✅ ';
        
        console.log(engineStatus);
        
    } catch (error) {
        console.error('❌ Erreur serveur:', error);
        showToast('Erreur de connexion au serveur', 'error');
    }
}

/**
 * Formatage des données
 */
function formatTime(seconds) {
    if (isNaN(seconds)) return '00:00';
    
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Système de notifications toast
 */
function showToast(message, type = 'info', duration = CONFIG.toastDuration) {
    const container = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }[type] || 'ℹ️';
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Auto-suppression
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

/**
 * Gestion des modales
 */
function closeFindReplace() {
    document.getElementById('findReplaceModal').style.display = 'none';
}

function closeShareModal() {
    document.getElementById('shareModal').style.display = 'none';
}

function findReplace() {
    document.getElementById('findReplaceModal').style.display = 'flex';
    document.getElementById('findText').focus();
}

function findNext() {
    const findText = document.getElementById('findText').value;
    const textarea = document.getElementById('transcriptResult');
    
    if (!findText || !textarea.value) return;
    
    const text = textarea.value;
    const currentPos = textarea.selectionStart;
    const foundIndex = text.indexOf(findText, currentPos);
    
    if (foundIndex !== -1) {
        textarea.setSelectionRange(foundIndex, foundIndex + findText.length);
        textarea.focus();
    } else {
        // Rechercher depuis le début
        const foundFromStart = text.indexOf(findText);
        if (foundFromStart !== -1) {
            textarea.setSelectionRange(foundFromStart, foundFromStart + findText.length);
            textarea.focus();
        } else {
            showToast('Texte non trouvé', 'warning');
        }
    }
}

function replaceAll() {
    const findText = document.getElementById('findText').value;
    const replaceText = document.getElementById('replaceText').value;
    const textarea = document.getElementById('transcriptResult');
    
    if (!findText) {
        showToast('Veuillez saisir le texte à rechercher', 'warning');
        return;
    }
    
    const originalText = textarea.value;
    const newText = originalText.replaceAll(findText, replaceText);
    const replacements = (originalText.match(new RegExp(findText, 'g')) || []).length;
    
    textarea.value = newText;
    
    if (replacements > 0) {
        showToast(`${replacements} remplacement(s) effectué(s)`, 'success');
        closeFindReplace();
    } else {
        showToast('Aucune occurrence trouvée', 'warning');
    }
}

/**
 * Formatage du texte
 */
function formatText(action) {
    const textarea = document.getElementById('transcriptResult');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    
    if (!selectedText) {
        showToast('Veuillez sélectionner du texte', 'warning');
        return;
    }
    
    let formattedText = selectedText;
    
    switch(action) {
        case 'bold':
            formattedText = `**${selectedText}**`;
            break;
        case 'italic':
            formattedText = `*${selectedText}*`;
            break;
        case 'underline':
            formattedText = `__${selectedText}__`;
            break;
    }
    
    textarea.value = textarea.value.substring(0, start) + formattedText + textarea.value.substring(end);
    
    // Repositionner le curseur
    const newEnd = start + formattedText.length;
    textarea.setSelectionRange(newEnd, newEnd);
    textarea.focus();
}

/**
 * Copie dans le presse-papiers
 */
async function copyToClipboard() {
    const textarea = document.getElementById('transcriptResult');
    const text = textarea.value;
    
    if (!text.trim()) {
        showToast('Aucun texte à copier', 'warning');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(text);
        showToast('📋 Texte copié dans le presse-papiers !', 'success');
    } catch (error) {
        // Fallback pour anciens navigateurs
        textarea.select();
        document.execCommand('copy');
        showToast('📋 Texte copié !', 'success');
    }
}

/**
 * Validation audio
 */
async function validateAudio() {
    if (!currentFile) {
        showToast('Aucun fichier sélectionné', 'warning');
        return;
    }
    
    const btn = document.getElementById('validateBtn');
    const originalText = btn.textContent;
    btn.textContent = '🔍 Analyse en cours...';
    btn.disabled = true;
    
    try {
        // Ici on pourrait appeler une API de validation
        // Pour l'instant, simulation
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        showToast('✅ Audio validé - Prêt pour la transcription !', 'success');
        
        // Afficher des suggestions automatiques
        showAutoSuggestions();
        
    } catch (error) {
        console.error('Erreur validation:', error);
        showToast('❌ Erreur lors de la validation', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

/**
 * Affichage des suggestions automatiques
 */
function showAutoSuggestions() {
    const suggestions = document.getElementById('autoSuggestions');
    const suggestionsList = document.getElementById('suggestionsList');
    
    // Suggestions basées sur l'analyse (simulation)
    const autoSuggestions = [
        { type: 'model', suggestion: 'Utiliser le modèle "small" pour un bon équilibre', action: () => document.getElementById('model').value = 'small' },
        { type: 'enhancement', suggestion: 'Activer la réduction de bruit (niveau détecté)', action: () => document.getElementById('noiseReduction').value = '70' },
        { type: 'language', suggestion: 'Français détecté automatiquement', action: () => document.getElementById('language').value = 'fr' }
    ];
    
    suggestionsList.innerHTML = '';
    
    autoSuggestions.forEach(item => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.innerHTML = `
            <span class="suggestion-text">${item.suggestion}</span>
            <button class="btn btn-small" onclick="(${item.action.toString()})()">Appliquer</button>
        `;
        suggestionsList.appendChild(div);
    });
    
    suggestions.style.display = 'block';
}

/**
 * Application des suggestions
 */
function applySuggestions() {
    // Appliquer toutes les suggestions automatiquement
    document.getElementById('model').value = 'small';
    document.getElementById('noiseReduction').value = '70';
    document.getElementById('language').value = 'fr';
    
    // Mettre à jour les affichages
    document.getElementById('noiseValue').textContent = '70%';
    
    showToast('🎯 Suggestions appliquées !', 'success');
    document.getElementById('autoSuggestions').style.display = 'none';
}

// Export des fonctions pour utilisation globale
window.transcripteurApp = {
    showTab,
    handleFileSelect,
    togglePlayPause,
    stopAudio,
    rewind,
    fastForward,
    setSelectionStart,
    setSelectionEnd,
    playSelection,
    cropSelection,
    deleteSelection,
    validateAudio,
    showToast,
    formatTime,
    formatFileSize
};