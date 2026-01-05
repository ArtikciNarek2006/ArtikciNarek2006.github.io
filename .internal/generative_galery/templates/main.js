// Gallery Application JavaScript
// projects array is populated by injected data
let filteredProjects = [];
let currentView = 'grid';

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    setupEventListeners();
    loadTheme();
    loadViewPreference();
    
    // Update analog clock if visible
    const clockOverlay = document.getElementById('clockOverlay');
    if (clockOverlay && !clockOverlay.classList.contains('hidden')) {
        setInterval(updateAnalogClock, 1000);
    }
});

function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', filterProjects);
    document.getElementById('tagFilter').addEventListener('change', filterProjects);
    document.getElementById('sortBy').addEventListener('change', sortProjects);
}

// Theme Management
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gallery-theme', theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const themes = ['dark', 'light', 'oled'];
    const currentIndex = themes.indexOf(currentTheme);
    const nextTheme = themes[(currentIndex + 1) % themes.length];
    setTheme(nextTheme);
}

function loadTheme() {
    const savedTheme = localStorage.getItem('gallery-theme') || 'dark';
    setTheme(savedTheme);
}

// Storage Manager
function toggleStorageManager() {
    const modal = document.getElementById('storageManagerModal');
    const isVisible = modal.style.display === 'flex';
    
    if (isVisible) {
        modal.style.display = 'none';
    } else {
        viewStorage('localStorage');
        modal.style.display = 'flex';
    }
}

function closeStorageManager() {
    document.getElementById('storageManagerModal').style.display = 'none';
}

function viewStorage(type) {
    const data = {};
    const storage = type === 'localStorage' ? localStorage : sessionStorage;
    
    Object.keys(storage).forEach(key => {
        data[key] = storage.getItem(key);
    });
    
    document.getElementById('storageContent').value = JSON.stringify(data, null, 2);
}

function flushStorage(type) {
    if (confirm(`Are you sure you want to clear ${type}?`)) {
        if (type === 'localStorage') {
            localStorage.clear();
        } else {
            sessionStorage.clear();
        }
        viewStorage(type);
        alert(`${type} cleared!`);
    }
}

function saveStorage() {
    try {
        const content = JSON.parse(document.getElementById('storageContent').value);
        
        // Determine which storage to update based on current view
        // For simplicity, we'll update localStorage
        localStorage.clear();
        Object.entries(content).forEach(([key, value]) => {
            localStorage.setItem(key, value);
        });
        
        alert('Storage updated successfully!');
        loadTheme();
        loadViewPreference();
    } catch (e) {
        alert('Invalid JSON format: ' + e.message);
    }
}

function showClock() {
    const clockOverlay = document.getElementById('clockOverlay');
    if (clockOverlay) {
        clockOverlay.classList.remove('hidden');
        updateAnalogClock();
    }
}

function closeClock() {
    const clockOverlay = document.getElementById('clockOverlay');
    if (clockOverlay) {
        clockOverlay.classList.add('hidden');
    }
}

function updateAnalogClock() {
    const now = new Date();
    const hours = now.getHours() % 12;
    const minutes = now.getMinutes();
    const seconds = now.getSeconds();
    
    const hourHand = document.querySelector('.hour-hand');
    const minuteHand = document.querySelector('.minute-hand');
    const secondHand = document.querySelector('.second-hand');
    
    if (hourHand) hourHand.style.transform = `rotate(${hours * 30 + minutes * 0.5}deg)`;
    if (minuteHand) minuteHand.style.transform = `rotate(${minutes * 6}deg)`;
    if (secondHand) secondHand.style.transform = `rotate(${seconds * 6}deg)`;
    
    const digitalTime = document.getElementById('digitalTime');
    const dateDisplay = document.getElementById('dateDisplay');
    
    if (digitalTime) {
        digitalTime.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }
    if (dateDisplay) {
        dateDisplay.textContent = now.toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
}

// View Management
function loadViewPreference() {
    const savedView = localStorage.getItem('gallery-view') || 'grid';
    setView(savedView);
}

function setView(view) {
    currentView = view;
    localStorage.setItem('gallery-view', view);
    
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[onclick="setView('${view}')"]`).classList.add('active');
    
    const container = document.getElementById('projectsContainer');
    container.className = `projects-${view}`;
    
    renderProjects();
}

// Filter and Sort Functions
function populateFilters() {
    const tagFilter = document.getElementById('tagFilter');
    const allTags = new Set();
    
    projects.forEach(p => {
        p.tags.forEach(tag => allTags.add(tag));
    });
    
    Array.from(allTags).sort().forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        option.textContent = tag;
        tagFilter.appendChild(option);
    });
}

function filterProjects() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const selectedTag = document.getElementById('tagFilter').value;
    
    filteredProjects = projects.filter(project => {
        const matchesSearch = !searchTerm || 
            project.title.toLowerCase().includes(searchTerm) ||
            project.desciption_short.toLowerCase().includes(searchTerm) ||
            project.description_long.toLowerCase().includes(searchTerm);
        
        const matchesTag = !selectedTag || project.tags.includes(selectedTag);
        
        return matchesSearch && matchesTag;
    });
    
    sortProjects();
}

function sortProjects() {
    const sortBy = document.getElementById('sortBy').value;
    
    filteredProjects.sort((a, b) => {
        switch(sortBy) {
            case 'date-desc':
                return new Date(b.date_published) - new Date(a.date_published);
            case 'date-asc':
                return new Date(a.date_published) - new Date(b.date_published);
            case 'name-asc':
                return a.title.localeCompare(b.title);
            case 'name-desc':
                return b.title.localeCompare(a.title);
            default:
                return 0;
        }
    });
    
    renderProjects();
}

// Render Functions
function renderProjects() {
    const container = document.getElementById('projectsContainer');
    container.innerHTML = '';
    
    if (filteredProjects.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No projects found</p>';
        return;
    }
    
    filteredProjects.forEach(project => {
        const card = createProjectCard(project);
        container.appendChild(card);
    });
}

function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = `project-card ${currentView}-view`;
    card.dataset.projectId = project.id;
    
    const fallbackSVG = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="200"%3E%3Crect fill="%23333" width="300" height="200"/%3E%3Ctext fill="%23fff" x="50%25" y="50%25" text-anchor="middle" dy=".3em" font-family="sans-serif" font-size="20"%3ENo Image%3C/text%3E%3C/svg%3E';
    
    // Get all images for slideshow
    const images = project.images_full_paths && project.images_full_paths.length > 0 
        ? project.images_full_paths 
        : [project.icon_path || fallbackSVG];
    
    // Create slideshow HTML
    let slideshowHTML = '<div class="project-slideshow">';
    images.forEach((img, index) => {
        slideshowHTML += `<img src="${img}" alt="${project.title}" class="${index === 0 ? 'active' : 'inactive'}" onerror="this.src='${fallbackSVG}'">`;
    });
    slideshowHTML += '</div>';
    
    // Build card HTML based on view mode
    if (currentView === 'grid') {
        card.innerHTML = `
            ${slideshowHTML}
            <div class="project-content">
                <h3 class="project-title">${project.title}</h3>
                <div class="project-bottom">
                    <img src="${project.icon_path || images[0]}" class="project-mini-icon" alt="icon" onerror="this.src='${fallbackSVG}'">
                    <div class="project-short-desc">${project.desciption_short}</div>
                </div>
                <div class="project-tags">
                    ${project.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="project-meta">
                    <span>📅 ${new Date(project.date_published).toLocaleDateString()}</span>
                    <span>v${project.version}</span>
                </div>
                <div class="project-actions">
                    <button class="action-btn" onclick="openProject('${project.project_path}', event)">Open Project</button>
                </div>
            </div>
        `;
    } else if (currentView === 'list') {
        card.innerHTML = `
            ${slideshowHTML}
            <div class="project-content">
                <h3 class="project-title">${project.title}</h3>
                <p class="project-description long">${project.description_long}</p>
                <div class="project-tags">
                    ${project.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="project-meta">
                    <span>📅 ${new Date(project.date_published).toLocaleDateString()}</span>
                    <span>v${project.version}</span>
                </div>
                <div class="project-actions">
                    <button class="action-btn" onclick="openProject('${project.project_path}', event)">Open Project</button>
                </div>
            </div>
        `;
    } else { // compact
        const iconHTML = `<img src="${project.icon_path || fallbackSVG}" class="project-compact-icon" alt="icon" onerror="this.src='${fallbackSVG}'">`;
        card.innerHTML = `
            ${iconHTML}
            <div class="project-content">
                <h3 class="project-title">${project.title}</h3>
                <div class="project-meta">
                    <span>📅 ${new Date(project.date_published).toLocaleDateString()}</span>
                </div>
            </div>
            <button class="project-info-btn" data-project-id="${project.id}">
                ℹ
            </button>
        `;
        
        // Add event listener for info button
        const infoBtn = card.querySelector('.project-info-btn');
        infoBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showProjectInfo(project);
        });
        
        card.onclick = (e) => {
            if (!e.target.closest('.project-info-btn')) {
                openProject(project.project_path, e);
            }
        };
    }
    
    // Setup auto-playing slideshow on card hover (not just icon)
    if (images.length > 1 && currentView !== 'compact') {
        let currentIndex = 0;
        let intervalId = null;
        
        card.addEventListener('mouseenter', () => {
            intervalId = setInterval(() => {
                const slideshowEl = card.querySelector('.project-slideshow');
                if (!slideshowEl) return;
                const slideImages = slideshowEl.querySelectorAll('img');
                
                slideImages[currentIndex].classList.remove('active');
                slideImages[currentIndex].classList.add('inactive');
                
                currentIndex = (currentIndex + 1) % images.length;
                
                slideImages[currentIndex].classList.remove('inactive');
                slideImages[currentIndex].classList.add('active');
            }, 1500);
        });
        
        card.addEventListener('mouseleave', () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
            // Reset to first image
            const slideshowEl = card.querySelector('.project-slideshow');
            if (!slideshowEl) return;
            const slideImages = slideshowEl.querySelectorAll('img');
            slideImages.forEach((img, index) => {
                if (index === 0) {
                    img.classList.add('active');
                    img.classList.remove('inactive');
                } else {
                    img.classList.remove('active');
                    img.classList.add('inactive');
                }
            });
            currentIndex = 0;
        });
    }
    
    return card;
}

function openProject(path, event) {
    if (event) event.stopPropagation();
    window.location.href = `projects/${path}/index.html`;
}

// Project Info Modal
function showProjectInfo(project) {
    const modal = document.getElementById('projectInfoModal');
    const title = document.getElementById('projectInfoTitle');
    const content = document.getElementById('projectInfoContent');
    
    title.textContent = project.title;
    content.innerHTML = `
        <p class="project-info-description">${project.description_long}</p>
        <div class="project-info-details">
            <p><strong>Version:</strong> ${project.version}</p>
            <p><strong>Published:</strong> ${new Date(project.date_published).toLocaleDateString()}</p>
            <p><strong>Tags:</strong> ${project.tags.join(', ')}</p>
        </div>
    `;
    
    modal.style.display = 'flex';
}

function closeProjectInfo() {
    document.getElementById('projectInfoModal').style.display = 'none';
}

// GitHub Stats
function toggleGithubStats() {
    const panel = document.getElementById('githubStats');
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'block';
    
    if (!isVisible) {
        loadGithubStats();
    }
}

function loadGithubStats() {
    // Placeholder for GitHub API integration
    document.getElementById('githubStats').innerHTML = `
        <h3>GitHub Stats</h3>
        <p style="color: var(--text-secondary);">Connect to GitHub API to see repository statistics.</p>
        <p style="color: var(--text-secondary); font-size: 0.85rem;">Configure API token in settings to enable this feature.</p>
    `;
}

// Load Projects - Will be replaced with actual data
function loadProjects() {
    // PROJECTS_DATA_PLACEHOLDER
    filteredProjects = projects;
    populateFilters();
    renderProjects();
}
