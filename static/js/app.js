// --- DATA INITIALIZATION ---
let allHistory = {};
let folderMetadata = {};

function loadDataFromDOM() {
    try {
        allHistory = JSON.parse(document.getElementById('history-data').textContent || '{}');
        folderMetadata = JSON.parse(document.getElementById('folders-data').textContent || '{}');
        console.log("Galleria: Wczytano folderów:", Object.keys(folderMetadata).length);
        console.log("Galleria: Wczytano historię dla autorów:", Object.keys(allHistory).length);
    } catch (e) {
        console.error("Błąd podczas ładowania danych z DOM:", e);
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    if (tabId === 'generator') document.getElementById('tabGenBtn').classList.add('active');
    else if (tabId === 'authors') document.getElementById('tabAuthorBtn').classList.add('active');
    else if (tabId === 'queue') document.getElementById('tabQueueBtn').classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    if (tabId === 'generator') document.getElementById('tabGenerator').classList.add('active');
    else if (tabId === 'authors') document.getElementById('tabAuthors').classList.add('active');
    else if (tabId === 'queue') {
        document.getElementById('tabQueue').classList.add('active');
        refreshBatchQueue();
    }
}

async function refreshBatchQueue() {
    const list = document.getElementById('batchQueueList');
    try {
        const resp = await fetch('/api/batch-jobs');
        const jobs = await resp.json();
        
        if (!jobs || jobs.length === 0) {
            list.innerHTML = '<div class="empty-queue">Brak aktywnych zadań w kolejce.</div>';
            return;
        }
        
        list.innerHTML = jobs.map(job => {
            const isCompleted = job.status === 'COMPLETED';
            const isFailed = job.status === 'FAILED';
            
            let actionBtn = '';
            if (isCompleted) {
                actionBtn = `<button class="btn-new" style="margin-top: 10px; width: 100%; font-size: 11px;" onclick="importBatchResults('${job.id}')">📥 Importuj wyniki do galerii</button>`;
            } else if (isFailed) {
                actionBtn = `<button class="btn-secondary" style="margin-top: 10px; width: 100%; font-size: 11px; background: #e67e22; color: white;" onclick="retryBatchJob('${job.id}')">🔄 Ponów zadanie (użyj tych samych pomysłów)</button>`;
            }
            
            return `
                <div class="batch-item">
                    <div class="batch-header">
                        <span class="batch-id">${job.id.split('/').pop()}</span>
                        <div style="display: flex; gap: 5px; align-items: center;">
                            <span class="batch-status-tag status-${job.status.toLowerCase()}">${job.status}</span>
                            <button onclick="deleteBatchJob('${job.id}')" style="background: none; border: none; color: #ff4757; cursor: pointer; font-size: 16px; padding: 0 5px;">&times;</button>
                        </div>
                    </div>
                    <div style="font-size: 13px; font-weight: 600;">${job.author_name} - ${job.count}</div>
                    <div style="font-size: 11px; color: #888;">Zlecono: ${job.created_at}</div>
                    <div class="batch-progress">
                        <div class="batch-progress-fill" style="width: ${job.progress}%"></div>
                    </div>
                    ${actionBtn}
                </div>
            `;
        }).join('');
        
    } catch (e) {
        console.error("Błąd odświeżania kolejki:", e);
        list.innerHTML = '<div class="empty-queue" style="color: #e74c3c;">Błąd połączenia z serwerem.</div>';
    }
}

async function importBatchResults(jobId) {
    if (!confirm("Czy chcesz zaimportować obrazy z tego zadania do galerii? Może to chwilę potrwać.")) return;
    
    const btn = event.target;
    const originalText = btn.textContent;
    const progress = document.getElementById('progressBar');
    const status = document.getElementById('statusText');
    
    try {
        btn.disabled = true;
        btn.textContent = "⏳ Importowanie obrazów...";
        if (progress) progress.classList.add('active');
        if (status) status.textContent = "Pobieranie i wysyłka do chmury...";

        const resp = await fetch(`/api/batch-results/${jobId}`, { method: 'POST' });
        const data = await resp.json();
        
        if (data.session_id) {
            const eventSource = new EventSource(`/events/${data.session_id}`);
            eventSource.onmessage = (event) => {
                const evt = JSON.parse(event.data);
                if (evt.type === 'done') {
                    btn.textContent = "✅ Gotowe!";
                    if (status) status.textContent = `Sukces! Zaimportowano ${evt.count} obrazów.`;
                    eventSource.close();
                    setTimeout(() => window.location.reload(), 1500);
                } else if (evt.type === 'error') {
                    status.innerHTML = `<span style="color: #ff4757;">⚠️ ${evt.message}</span><br>
                                       <small style="color: #888;">Zalecamy odczekać 2-3 minuty i spróbować ponownie.</small>`;
                    eventSource.close();
                    resetGenerateBtn();
                }
            };
        } else {
            alert(data.error || "Błąd podczas inicjalizacji importu.");
            resetImportBtn(btn, originalText);
        }
    } catch (e) {
        console.error(e);
        status.innerHTML = `<span style="color: #ff4757;">❌ Błąd: ${e.message}</span>`;
        resetGenerateBtn();
    }
}

async function retryBatchJob(jobId) {
    if (!confirm("Czy na pewno chcesz ponowić to zadanie używając tych samych pomysłów?")) return;
    
    try {
        const resp = await fetch(`/api/batch-retry/${jobId}`, { method: 'POST' });
        const data = await resp.json();
        
        if (data.success) {
            alert("Zadanie zostało ponowione! Sprawdź górę kolejki.");
            refreshBatchQueue();
        } else {
            alert("Błąd podczas ponawiania: " + data.error);
        }
    } catch (e) {
        alert("Błąd sieci: " + e.message);
    }
}

async function deleteBatchJob(jobId) {
    if (!confirm("Czy na pewno chcesz usunąć/anulować to zadanie?")) return;
    
    try {
        const resp = await fetch(`/api/batch-jobs/${jobId}`, { method: 'DELETE' });
        const data = await resp.json();
        
        if (data.success) {
            refreshBatchQueue();
        } else {
            alert("Zadanie zostało anulowane lub ukryte.");
            refreshBatchQueue();
        }
    } catch (e) {
        alert("Błąd sieci: " + e.message);
    }
}

function resetImportBtn(btn, text) {
    btn.disabled = false;
    btn.textContent = text;
    document.getElementById('progressBar').classList.remove('active');
    document.getElementById('statusText').textContent = 'Gotowy';
}

// --- GALLERY NAVIGATION LOGIC ---
let currentAuthor = null;

function initGallery() {
    loadDataFromDOM();
    
    // Sprawdź czy mamy wrócić do konkretnego autora po odświeżeniu
    const lastAuthor = sessionStorage.getItem('lastAuthorView');
    if (lastAuthor && folderMetadata[lastAuthor]) {
        showAuthorGallery(lastAuthor);
        sessionStorage.removeItem('lastAuthorView'); // Czyścimy po użyciu
    } else {
        showFolders();
    }
}

function showFolders() {
    currentAuthor = null;
    selectedItems.clear(); // Czyścimy mapę zaznaczeń
    document.getElementById('galleryTitle').textContent = 'Kolekcje Autorów';
    document.getElementById('backBtn').style.display = 'none';
    document.getElementById('bulkActions').style.display = 'none';
    
    const gallery = document.getElementById('gallery');
    gallery.innerHTML = '';
    
    const slugs = Object.keys(folderMetadata);
    
    if (slugs.length === 0) {
        gallery.innerHTML = `<div class="empty-state"><div class="icon">📁</div><div class="text">Brak wygenerowanych obrazków.<br>Wybierz autora i kliknij "Generuj puzzle"!</div></div>`;
        return;
    }

    slugs.forEach(slug => {
        const meta = folderMetadata[slug];
        const card = document.createElement('div');
        card.className = 'folder-card';
        card.onclick = () => showAuthorGallery(slug);
        
        const coverImg = meta.cover ? `<img src="${meta.cover}" class="folder-cover">` : `<div class="folder-icon" style="position:absolute; top:40%; left:50%; transform:translate(-50%,-50%); opacity:0.2;">📂</div>`;
        
        card.innerHTML = `
            ${coverImg}
            <div class="folder-info-overlay">
                <div class="folder-name">${meta.name}</div>
                <div class="folder-count">${meta.count} obrazków</div>
            </div>
        `;
        gallery.appendChild(card);
    });
}

function showAuthorGallery(slug) {
    currentAuthor = slug;
    selectedItems.clear(); // Czyścimy przy wejściu do folderu
    updateBulkActionsUI();
    
    const images = allHistory[slug] || [];
    const authorName = slug.replace(/_/g, ' ').toUpperCase();
    document.getElementById('galleryTitle').textContent = `Autor: ${authorName}`;
    document.getElementById('backBtn').style.display = 'flex';
    document.getElementById('bulkActions').style.display = 'flex';
    
    const gallery = document.getElementById('gallery');
    gallery.innerHTML = '';
    
    if (images.length === 0) {
        gallery.innerHTML = `<div class="empty-state"><div class="icon">🖼️</div><div class="text">Ten folder jest jeszcze pusty.</div></div>`;
        return;
    }
    
    images.forEach(img => addImageToGallery(img, true));
}

// --- SELECTION LOGIC ---
let selectedItems = new Map(); // publicId -> {url, title}

function toggleImageSelection(publicId, url, title, cardElement) {
    if (selectedItems.has(publicId)) {
        selectedItems.delete(publicId);
        cardElement.classList.remove('selected');
    } else {
        selectedItems.set(publicId, {url, title});
        cardElement.classList.add('selected');
    }
    updateBulkActionsUI();
}

function updateBulkActionsUI() {
    const btn = document.getElementById('downloadSelectedBtn');
    const count = selectedItems.size;
    btn.textContent = count === 1 ? `💾 Pobierz zaznaczony` : `💾 Pobierz zaznaczone (${count})`;
    btn.disabled = count === 0;
}

async function downloadSelectedZip() {
    const count = selectedItems.size;
    if (count === 0) return;
    
    if (count === 1) {
        // POBIERANIE POJEDYNCZEGO PLIKU
        const [publicId, data] = Array.from(selectedItems.entries())[0];
        let downloadUrl = data.url;
        if (downloadUrl.includes('cloudinary.com')) {
            downloadUrl = downloadUrl.replace('/upload/', '/upload/fl_attachment/');
        }
        window.location.href = downloadUrl;
    } else {
        // POBIERANIE ZIP (WIELU PLIKÓW)
        await triggerZipDownload(Array.from(selectedItems.keys()));
    }
}

async function downloadAllZip() {
    if (!currentAuthor || !allHistory[currentAuthor]) return;
    const allIds = [];
    allHistory[currentAuthor].forEach(img => {
        const originalId = getPublicIdFromUrl(img.url);
        if (originalId) allIds.push(originalId);
        if (img.preview_url) {
            const pixelId = getPublicIdFromUrl(img.preview_url);
            if (pixelId) allIds.push(pixelId);
        }
    });
    await triggerZipDownload(allIds);
}

function getPublicIdFromUrl(url) {
    const parts = url.split('/upload/');
    if (parts.length < 2) return null;
    const path = parts[1].split('/').slice(1).join('/');
    return path.split('.')[0];
}

async function triggerZipDownload(publicIds) {
    const btnSelected = document.getElementById('downloadSelectedBtn');
    const originalText = btnSelected.textContent;
    
    try {
        btnSelected.textContent = '⏳ Generuję ZIP...';
        const resp = await fetch('/api/download-zip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_ids: publicIds, author_slug: currentAuthor })
        });
        const data = await resp.json();
        if (data.url) {
            window.location.href = data.url;
        } else {
            alert(data.error || 'Błąd generowania ZIP');
        }
    } catch (e) {
        alert('Błąd: ' + e.message);
    } finally {
        btnSelected.textContent = originalText;
    }
}

function addImageToGallery(data, append = false) {
    const gallery = document.getElementById('gallery');
    
    if (!allHistory[data.author_slug]) allHistory[data.author_slug] = [];
    if (!allHistory[data.author_slug].find(i => i.id === data.id)) {
        if (append) allHistory[data.author_slug].push(data);
        else allHistory[data.author_slug].unshift(data);
    }
    
    if (currentAuthor !== data.author_slug && currentAuthor !== null) return;
    if (currentAuthor === null) { 
        showFolders(); 
        return; 
    }

    const createCard = (url, title, model, isPixel, cost) => {
        const publicId = getPublicIdFromUrl(url);
        const card = document.createElement('div');
        card.className = 'gallery-item';
        if (selectedItems.has(publicId)) card.classList.add('selected');

        // Klasa CSS dla badge'a (małe litery, bez spacji i nawiasów)
        const badgeClass = model.toLowerCase().split(' ')[0].replace(/[^a-z]/g, '');
        const costLabel = cost ? `<span class="cost-tag">${parseFloat(cost).toFixed(2)} zł</span>` : '';

        card.innerHTML = `
            <div class="selection-indicator"></div>
            <div class="image-container">
                <img src="${url}" alt="${title}" loading="lazy">
            </div>
            <div class="info">
                <div class="info-top">
                    <div class="title">${title} ${isPixel ? '(Pixel Art)' : ''}</div>
                    <div class="model-badge badge-${badgeClass}">${model} ${costLabel}</div>
                </div>
            </div>
        `;
        
        card.onclick = () => toggleImageSelection(publicId, url, title, card);
        return card;
    };

    const cardOrig = createCard(data.url, data.title, data.model, false, data.cost);
    if (append) gallery.appendChild(cardOrig); else gallery.prepend(cardOrig);
    
    if (data.preview_url) {
        const cardPixel = createCard(data.preview_url, data.title, data.model, true, data.cost);
        if (append) gallery.appendChild(cardPixel); else gallery.prepend(cardPixel);
    }
}
window.addEventListener('load', initGallery);

function updateUploadStatus() {
    const input = document.getElementById('manualUpload');
    const status = document.getElementById('uploadStatus');
    const clearBtn = document.getElementById('clearUploadBtn');
    const genBtn = document.getElementById('generateBtn');

    if (input.files && input.files[0]) {
        status.textContent = `Wybrano: ${input.files[0].name}`;
        status.style.color = '#27ae60';
        clearBtn.style.display = 'block';
        genBtn.textContent = '🎨 Konwertuj własny obraz';
    } else {
        status.textContent = 'Nie wybrano pliku (użyje AI)';
        status.style.color = '#888';
        clearBtn.style.display = 'none';
        genBtn.textContent = '🎨 Generuj puzzle';
    }
}

function clearUpload() {
    document.getElementById('manualUpload').value = '';
    updateUploadStatus();
}

function setGenMode(mode, el) {
    document.getElementById('genMode').value = mode;
    el.parentElement.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
    el.classList.add('active');
}

async function startGeneration() {
    const author = document.getElementById('authorSelect').value;
    const countInput = document.getElementById('countInput');
    const count = parseInt(countInput.value);
    const useGemini = document.getElementById('modelGemini').checked;
    const useFlux = document.getElementById('modelFlux').checked;
    const pixelSize = parseInt(document.getElementById('pixelSizeSelect').value);
    const manualFile = document.getElementById('manualUpload').files[0];
    const genMode = document.getElementById('genMode').value;

    if (!author) { alert('Wybierz autora!'); return; }
    
    const btn = document.getElementById('generateBtn');
    const originalBtnText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Przetwarzam...';
    document.getElementById('progressBar').classList.add('active');
    document.getElementById('statusText').textContent = 'Inicjalizacja...';

    try {
        let resp;
        if (manualFile) {
            // Tryb ręczny - wysyłamy plik
            const formData = new FormData();
            formData.append('author', author);
            formData.append('file', manualFile);
            formData.append('pixel_size', pixelSize);
            
            resp = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
        } else {
            // Tryb AI
            if (!useGemini && !useFlux) { alert('Wybierz przynajmniej jeden model!'); resetUI(); return; }
            resp = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    author, count, 
                    gemini: useGemini, flux: useFlux, 
                    pixel_size: pixelSize,
                    gen_mode: genMode 
                }),
            });
        }

        const data = await resp.json();
        if (data.error) { alert(data.error); resetUI(); return; }
        
        const eventSource = new EventSource(`/events/${data.session_id}`);
        eventSource.onmessage = (event) => {
            const evt = JSON.parse(event.data);
            switch (evt.type) {
                case 'status': document.getElementById('statusText').textContent = evt.message; break;
                case 'generating':
                    document.getElementById('progressLabel').textContent = `${evt.title} (${evt.model})`;
                    document.getElementById('progressCount').textContent = `${evt.current}/${evt.total}`;
                    document.getElementById('progressFill').style.width = `${(evt.current / evt.total) * 100}%`;
                    break;
                case 'image_ready': addImageToGallery(evt); break;
                case 'done': 
                    resetUI(); 
                    eventSource.close();
                    if (currentAuthor) sessionStorage.setItem('lastAuthorView', currentAuthor);
                    setTimeout(() => window.location.reload(), 1000);
                    break;
                case 'error': alert(evt.message); resetUI(); eventSource.close(); break;
            }
        };
    } catch (e) { 
        alert('Błąd: ' + e.message); 
        resetUI(); 
    }
}

function resetUI() {
    const btn = document.getElementById('generateBtn');
    btn.disabled = false;
    btn.textContent = '🎨 Generuj puzzle';
    document.getElementById('progressBar').classList.remove('active');
}

function updateAuthorManageInfo() {
    const select = document.getElementById('authorManageSelect');
    const info = document.getElementById('authorManageInfo');
    const actions = document.getElementById('authorActions');
    const option = select.options[select.selectedIndex];
    if (option.value) {
        info.style.display = 'block';
        info.textContent = option.dataset.theme;
        actions.style.display = 'grid';
    } else {
        info.style.display = 'none';
        actions.style.display = 'none';
    }
}

function createNewAuthor() {
    document.getElementById('editOriginalName').value = '';
    document.getElementById('editName').value = '';
    document.getElementById('editTheme').value = '';
    document.getElementById('editStyleTemplate').value = '';
    document.getElementById('editSceneInstructions').value = '';
    document.getElementById('editNegativePrompts').value = '';
    document.getElementById('editTags').value = '';
    document.getElementById('editPostProcessing').value = '';
    document.getElementById('modalTitle').textContent = 'Nowy Autor';
    document.getElementById('authorModal').classList.add('active');
}

async function deleteAuthor() {
    const authorName = document.getElementById('authorManageSelect').value;
    if (!authorName) return;
    if (!confirm(`Czy na pewno chcesz usunąć autora "${authorName}"?`)) return;
    try {
        const resp = await fetch(`/api/author/${encodeURIComponent(authorName)}`, { method: 'DELETE' });
        if (!resp.ok) throw new Error('Błąd podczas usuwania');
        alert('Autor usunięty!');
        window.location.reload();
    } catch (e) { alert(e.message); }
}

function updateAuthorInfo() {
    const select = document.getElementById('authorSelect');
    const info = document.getElementById('authorInfo');
    const option = select.options[select.selectedIndex];
    if (option.value) {
        info.style.display = 'block';
        info.textContent = option.dataset.theme;
        const isPixelArt = (option.dataset.postprocessing === 'pixel_art_50x50');
        document.getElementById('pixelSizeGroup').style.display = isPixelArt ? 'flex' : 'none';
        document.getElementById('uploadGroup').style.display = isPixelArt ? 'flex' : 'none';
    } else {
        info.style.display = 'none';
        document.getElementById('pixelSizeGroup').style.display = 'none';
        document.getElementById('uploadGroup').style.display = 'none';
    }
}

function toggleModel(el) {
    const checkbox = el.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
    el.classList.toggle('selected', checkbox.checked);
}

function autoExpandTextarea(el) { el.style.height = 'auto'; el.style.height = (el.scrollHeight) + 'px'; }
document.querySelectorAll('textarea').forEach(textarea => textarea.addEventListener('input', function() { autoExpandTextarea(this); }));

async function openAuthorEditor(mode = 'generator') {
    const selectId = mode === 'generator' ? 'authorSelect' : 'authorManageSelect';
    const authorName = document.getElementById(selectId).value;
    if (!authorName) { alert('Wybierz autora!'); return; }
    try {
        const resp = await fetch(`/api/author/${encodeURIComponent(authorName)}`);
        const data = await resp.json();
        document.getElementById('editOriginalName').value = data.name || authorName;
        document.getElementById('editName').value = data.name || '';
        document.getElementById('editTheme').value = data.theme || '';
        document.getElementById('editStyleTemplate').value = data.style_template || '';
        document.getElementById('editSceneInstructions').value = data.scene_instructions || '';
        document.getElementById('editNegativePrompts').value = (data.negative_prompts || []).join(', ');
        document.getElementById('editTags').value = (data.tags || []).join(', ');
        document.getElementById('editPostProcessing').value = data.post_processing || '';
        document.getElementById('modalTitle').textContent = 'Edycja Autora';
        document.getElementById('authorModal').classList.add('active');
        setTimeout(() => document.querySelectorAll('#authorModal textarea').forEach(autoExpandTextarea), 50);
    } catch (e) { alert(e.message); }
}

function closeAuthorEditor() { document.getElementById('authorModal').classList.remove('active'); }

async function saveAuthor() {
    const originalName = document.getElementById('editOriginalName').value;
    const name = document.getElementById('editName').value.trim();
    if (!name) { alert('Nazwa autora jest wymagana!'); return; }
    const payload = {
        name: name,
        theme: document.getElementById('editTheme').value,
        style_template: document.getElementById('editStyleTemplate').value,
        scene_instructions: document.getElementById('editSceneInstructions').value,
        negative_prompts: document.getElementById('editNegativePrompts').value.split(',').map(s => s.trim()).filter(s => s),
        tags: document.getElementById('editTags').value.split(',').map(s => s.trim()).filter(s => s),
        post_processing: document.getElementById('editPostProcessing').value || null
    };
    const btn = document.querySelector('.btn-save');
    const originalText = btn.textContent;
    btn.textContent = 'Zapisywanie...';
    btn.disabled = true;

    try {
        const targetName = originalName || name;
        const resp = await fetch(`/api/author/${encodeURIComponent(targetName)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await resp.json();
        if (result.error) throw new Error(result.error);
        closeAuthorEditor();
        window.location.reload();
    } catch (e) {
        alert('Błąd podczas zapisywania: ' + e.message);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
