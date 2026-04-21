document.addEventListener('DOMContentLoaded', () => {
    // State
    const profile = {
        preferred_categories: [],
        preferred_sources: [],
        keywords: [],
        tone: "",
        top_k: 3
    };

    let currentFlashcardIndex = 0;

    // Elements
    const flashcards = document.querySelectorAll('.flashcard');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resetBtn = document.getElementById('reset-btn');
    const summaryScrollBtn = document.getElementById('summary-scroll-btn');
    
    const questionnaireSection = document.getElementById('questionnaire-section');
    const loadingSection = document.getElementById('loading-section');
    const resultsSection = document.getElementById('results-section');
    
    const loadingStatus = document.getElementById('loading-status');
    const chartContainer = document.getElementById('chart-container');
    const systemRationaleText = document.getElementById('system-rationale-text');
    const rationaleTarget = document.getElementById('rationale-target');
    const recommendationsContainer = document.getElementById('recommendations-container');

    const API_BASE = 'http://localhost:8000';

    // Flashcard Selection Logic
    const optionCards = document.querySelectorAll('.option-card');
    const skipBtns = document.querySelectorAll('.skip-btn');
    const nextBtns = document.querySelectorAll('.next-btn');
    const refreshDataBtn = document.getElementById('refresh-data-btn');
    const refreshStatus = document.getElementById('refresh-status');
    
    optionCards.forEach(card => {
        card.addEventListener('click', () => {
            const currentCard = flashcards[currentFlashcardIndex];
            const isSingleSelect = currentCard.querySelector('.single-select') !== null;
            
            if (isSingleSelect) {
                // Single select behavior
                const siblings = currentCard.querySelectorAll('.option-card');
                siblings.forEach(s => s.classList.remove('selected'));
                card.classList.add('selected');
                
                // For single select (tone, top_k), we can auto-advance or let them hit Next
                // We'll let the user hit Next or auto-advance
                const type = card.getAttribute('data-type');
                const value = card.getAttribute('data-value');
                if (type === 'tone') profile.tone = value;
                if (type === 'top_k') profile.top_k = parseInt(value, 10);
                
                advanceFlashcard();
            } else {
                // Multi select behavior
                if (card.getAttribute('data-value') === 'none') {
                    // if they click 'Skip', unselect others
                    const siblings = currentCard.querySelectorAll('.option-card');
                    siblings.forEach(s => s.classList.remove('selected'));
                    card.classList.add('selected');
                } else {
                    // if they click a real option, unselect 'Skip' if selected
                    const noneCard = currentCard.querySelector('[data-value="none"]');
                    if (noneCard) noneCard.classList.remove('selected');
                    
                    card.classList.toggle('selected');
                }
            }
        });
    });

    // Skip Button Logic
    skipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            advanceFlashcard();
        });
    });

    // Next Button Logic
    nextBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const currentCard = flashcards[currentFlashcardIndex];
            const selectedCards = currentCard.querySelectorAll('.option-card.selected');
            
            selectedCards.forEach(card => {
                const type = card.getAttribute('data-type');
                const value = card.getAttribute('data-value');
                
                if (value !== 'none') {
                    if (type === 'category' && !profile.preferred_categories.includes(value)) {
                        profile.preferred_categories.push(value);
                    } else if (type === 'source' && !profile.preferred_sources.includes(value)) {
                        profile.preferred_sources.push(value);
                    } else if (type === 'keyword' && !profile.keywords.includes(value)) {
                        profile.keywords.push(value);
                    } else if (type === 'tone') {
                        profile.tone = value;
                    } else if (type === 'top_k') {
                        profile.top_k = parseInt(value, 10);
                    }
                }
            });
            
            advanceFlashcard();
        });
    });

    function advanceFlashcard() {
        if (currentFlashcardIndex >= flashcards.length - 1) return; 
        
        const currentCard = flashcards[currentFlashcardIndex];
        currentCard.classList.add('fade-out');
        
        setTimeout(() => {
            currentCard.classList.remove('active');
            currentCard.classList.add('hidden');
            
            currentFlashcardIndex++;
            const nextCard = flashcards[currentFlashcardIndex];
            nextCard.classList.remove('hidden');
            nextCard.classList.remove('fade-out');
            nextCard.classList.add('active');
        }, 400); 
    }

    // Refresh Data Logic
    if (refreshDataBtn) {
        // Initialize status from localStorage
        const savedStatus = localStorage.getItem('refreshStatus');
        if (savedStatus) {
            refreshStatus.textContent = savedStatus;
            refreshStatus.style.color = savedStatus === 'Connected successfully' ? '#4FC3F7' : 'red';
            refreshStatus.classList.remove('hidden');
        }
        
        refreshDataBtn.addEventListener('click', async () => {
            refreshDataBtn.disabled = true;
            refreshDataBtn.style.opacity = '0.5';
            refreshStatus.classList.remove('hidden');
            if (refreshStatus.textContent !== 'Connected successfully') {
                refreshStatus.textContent = 'Scraping active sources... This may take a moment.';
                localStorage.setItem('refreshStatus', 'Scraping active sources... This may take a moment.');
            }
            
            try {
                const res = await fetch(`${API_BASE}/refresh`, { method: 'POST' });
                if (!res.ok) throw new Error('Refresh failed');
                const data = await res.json();
                
                refreshStatus.style.color = '#4FC3F7'; 
                refreshStatus.textContent = 'Connected successfully';
                localStorage.setItem('refreshStatus', 'Connected successfully');
            } catch (err) {
                console.error(err);
                refreshStatus.style.color = 'red';
                refreshStatus.textContent = 'Failed to trigger live scraping. Check backend server.';
                localStorage.setItem('refreshStatus', 'Failed to trigger live scraping. Check backend server.');
            } finally {
                refreshDataBtn.disabled = false;
                refreshDataBtn.style.opacity = '1';
            }
        });
    }

    // Reset Flow
    resetBtn.addEventListener('click', () => {
        resultsSection.classList.remove('active');
        resultsSection.classList.add('hidden');
        
        profile.preferred_categories = [];
        profile.preferred_sources = [];
        profile.keywords = [];
        profile.tone = "";
        profile.top_k = 3;
        
        flashcards.forEach(fc => {
            fc.classList.remove('active');
            fc.classList.add('hidden');
            fc.classList.remove('fade-out');
            
            const opts = fc.querySelectorAll('.option-card');
            opts.forEach(o => o.classList.remove('selected'));
        });
        
        currentFlashcardIndex = 0;
        flashcards[0].classList.remove('hidden');
        flashcards[0].classList.add('active');

        questionnaireSection.classList.remove('hidden');
        questionnaireSection.classList.add('active');
    });

    // Summary Scroll
    summaryScrollBtn.addEventListener('click', () => {
        rationaleTarget.scrollIntoView({ behavior: 'smooth' });
    });

    // Analyze Flow
    analyzeBtn.addEventListener('click', async () => {
        questionnaireSection.classList.remove('active');
        questionnaireSection.classList.add('hidden');
        
        loadingSection.classList.remove('hidden');
        loadingSection.classList.add('active');

        const loadingSteps = [
            "Extracting text streams...",
            "Classifying topics and mapping keywords...",
            "Applying weights...",
            "Ranking vectors...",
            "Finalizing report..."
        ];

        for (let i = 0; i < loadingSteps.length; i++) {
            loadingStatus.textContent = loadingSteps[i];
            await new Promise(r => setTimeout(r, 600)); 
        }

        try {
            const summaryRes = await fetch(`${API_BASE}/summary`);
            if (!summaryRes.ok) throw new Error('Failed to fetch summary');
            const summaryData = await summaryRes.json();

            const payload = {
                preferred_categories: profile.preferred_categories,
                preferred_sources: profile.preferred_sources,
                keywords: profile.keywords,
                tone: profile.tone
            };
            
            const recRes = await fetch(`${API_BASE}/recommend?top_k=${profile.top_k}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (!recRes.ok) throw new Error('Failed to fetch recommendations');
            const recData = await recRes.json();

            renderSummary(summaryData);
            renderRationale();
            renderRecommendations(recData.recommendations);

            loadingSection.classList.remove('active');
            loadingSection.classList.add('hidden');
            
            resultsSection.classList.remove('hidden');
            resultsSection.classList.add('active');

        } catch (err) {
            console.error(err);
            loadingStatus.textContent = "Error connecting to backend APIs. Please ensure the server is running.";
            setTimeout(() => {
                loadingSection.classList.remove('active');
                loadingSection.classList.add('hidden');
                questionnaireSection.classList.remove('hidden');
                questionnaireSection.classList.add('active');
            }, 3000);
        }
    });

    function renderSummary(data) {
        chartContainer.innerHTML = '';
        const sourceChartContainer = document.getElementById('source-chart-container');
        if (sourceChartContainer) sourceChartContainer.innerHTML = '';

        const dist = data.category_distribution || {};
        const maxVal = Math.max(...Object.values(dist), 1);

        for (const [cat, count] of Object.entries(dist)) {
            const pct = (count / maxVal) * 100;
            const row = document.createElement('div');
            row.className = 'bar-row';
            
            row.innerHTML = `
                <div class="bar-label">${cat.charAt(0).toUpperCase() + cat.slice(1)}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: 0%"></div>
                </div>
                <div class="bar-value">${count}</div>
            `;
            chartContainer.appendChild(row);
            setTimeout(() => {
                row.querySelector('.bar-fill').style.width = `${pct}%`;
            }, 100);
        }

        const srcDist = data.source_distribution || {};
        const maxSrcVal = Math.max(...Object.values(srcDist), 1);

        for (const [src, count] of Object.entries(srcDist)) {
            const pct = (count / maxSrcVal) * 100;
            const row = document.createElement('div');
            row.className = 'bar-row';
            
            let label = src.charAt(0).toUpperCase() + src.slice(1);
            if (src === 'google_trends') label = 'Google Trends';
            
            row.innerHTML = `
                <div class="bar-label">${label}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: 0%; background: var(--accent-orange);"></div>
                </div>
                <div class="bar-value" style="color: var(--accent-orange);">${count}</div>
            `;
            if (sourceChartContainer) sourceChartContainer.appendChild(row);
            setTimeout(() => {
                row.querySelector('.bar-fill').style.width = `${pct}%`;
            }, 100);
        }
    }

    function renderRationale() {
        const catText = profile.preferred_categories.length > 0 ? profile.preferred_categories.join(', ') : 'general topics';
        const kwText = profile.keywords.length > 0 ? profile.keywords.join(', ') : 'broad trends';
        const sourceText = profile.preferred_sources.length > 0 ? profile.preferred_sources.join(', ') : 'multiple streams';
        
        systemRationaleText.textContent = `The algorithm processed data from ${sourceText} to find patterns aligning with ${catText}. Priority was given to vectors matching emerging signals like ${kwText}. Trends were then sorted by their momentum score combined with a profile similarity match.`;
    }

    function renderRecommendations(recs) {
        recommendationsContainer.innerHTML = '';

        if (!recs || recs.length === 0) {
            recommendationsContainer.innerHTML = '<p>No data vectors found matching your parameters.</p>';
            return;
        }

        recs.forEach((rec, index) => {
            const card = document.createElement('div');
            card.className = 'trend-card';
            
            const reasonTag = rec.reason ? `<span class="badge reason">MATCH: ${rec.reason.toUpperCase()}</span>` : '';
            const sourceLabel = rec.source_label ? `<span class="badge source">${rec.source_label.toUpperCase()}</span>` : '';
            const linkHref = rec.combined_url || '#';
            const description = rec.description || rec.snippet || rec.raw_text || '';
            const hasDescription = description.length > 0;
            
            card.innerHTML = `
                <div class="trend-card-content">
                    <div class="trend-card-header">
                        <div class="trend-card-left">
                            <h4 class="trend-title">#${index + 1}. ${rec.topic || 'Unknown Signal'}</h4>
                            <div class="trend-meta">
                                ${reasonTag}
                                ${sourceLabel}
                            </div>
                        </div>
                        <div class="trend-card-right">
                            <div class="trend-score-badge">
                                <span>SC</span>
                                ${(rec.recommendation_score || 0).toFixed(2)}
                            </div>
                            ${hasDescription ? '<button class="expand-btn" title="Show details">⊕</button>' : ''}
                            <a href="${linkHref}" target="_blank" class="source-btn">Source Data &nearr;</a>
                        </div>
                    </div>
                    ${hasDescription ? `<div class="trend-description hidden">${description}</div>` : ''}
                </div>
            `;
            
            recommendationsContainer.appendChild(card);
            
            // Add expand button functionality
            if (hasDescription) {
                const expandBtn = card.querySelector('.expand-btn');
                const descriptionDiv = card.querySelector('.trend-description');
                expandBtn.addEventListener('click', () => {
                    descriptionDiv.classList.toggle('hidden');
                    expandBtn.textContent = descriptionDiv.classList.contains('hidden') ? '⊕' : '⊖';
                    expandBtn.title = descriptionDiv.classList.contains('hidden') ? 'Show details' : 'Hide details';
                });
            }
        });
    }
});
