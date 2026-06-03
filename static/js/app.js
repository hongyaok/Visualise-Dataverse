/* ═══════════════════════════════════════════════════════════════════════════
   Dataverse Table Relationship Visualiser — Frontend JavaScript
   ═══════════════════════════════════════════════════════════════════════════ */

// ─── Solution Search / Filter ────────────────────────────────────────────────

function initSolutionSearch() {
    const searchInput = document.getElementById('solution-search');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const cards = document.querySelectorAll('.solution-card');
        let visibleCount = 0;

        cards.forEach(card => {
            const name = (card.dataset.name || '').toLowerCase();
            const unique = (card.dataset.unique || '').toLowerCase();
            const match = name.includes(query) || unique.includes(query);
            card.style.display = match ? '' : 'none';
            if (match) visibleCount++;
        });

        const countEl = document.getElementById('solutions-count');
        if (countEl) {
            countEl.textContent = `${visibleCount} solution${visibleCount !== 1 ? 's' : ''}`;
        }

        const emptyEl = document.getElementById('solutions-empty');
        if (emptyEl) {
            emptyEl.style.display = visibleCount === 0 ? '' : 'none';
        }
    });
}


// ─── Diagram Renderer ────────────────────────────────────────────────────────

function initDiagram(solutionId) {
    const container = document.getElementById('network-canvas');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const statsEl = document.getElementById('diagram-stats');

    if (!container || !solutionId) return;

    // Fetch diagram data from the Flask API
    loadingText.textContent = 'Fetching table metadata…';

    fetch(`/api/diagram/${solutionId}`)
        .then(resp => {
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return resp.json();
        })
        .then(data => {
            if (data.error) throw new Error(data.error);
            renderNetwork(container, data, loadingOverlay, statsEl);
        })
        .catch(err => {
            loadingText.textContent = `Error: ${err.message}`;
            const subtext = document.getElementById('loading-subtext');
            if (subtext) {
                subtext.textContent = 'Please check the console or try reconnecting.';
            }
            console.error('Diagram fetch error:', err);
        });
}


function renderNetwork(container, data, loadingOverlay, statsEl) {
    // ── Build Cytoscape Data ─────────────────────────────────────────────────

    const cyElements = [];
    const tableColumns = {};

    // 1. Collect columns for relationships
    data.edges.forEach(e => {
        if (e.type === '1:N') {
            if (e.from_key) {
                tableColumns[e.from] = tableColumns[e.from] || new Set();
                tableColumns[e.from].add(e.from_key);
            }
            if (e.to_key) {
                tableColumns[e.to] = tableColumns[e.to] || new Set();
                tableColumns[e.to].add(e.to_key);
            }
        }
    });

    // 2. Create nodes (Compound for Tables, child nodes for Columns)
    data.nodes.forEach(n => {
        // Table (Parent)
        cyElements.push({
            data: { id: n.id, label: n.label, isTable: true }
        });

        // Columns (Children)
        if (tableColumns[n.id]) {
            Array.from(tableColumns[n.id]).forEach(col => {
                cyElements.push({
                    data: { id: `${n.id}.${col}`, parent: n.id, label: col, isColumn: true }
                });
            });
        }
    });

    // 3. Create edges
    data.edges.forEach((e, i) => {
        const is1N = e.type === '1:N';
        let sourceId = e.from;
        let targetId = e.to;

        if (is1N) {
            if (e.from_key && tableColumns[e.from]?.has(e.from_key)) {
                sourceId = `${e.from}.${e.from_key}`;
            }
            if (e.to_key && tableColumns[e.to]?.has(e.to_key)) {
                targetId = `${e.to}.${e.to_key}`;
            }
        }

        cyElements.push({
            data: {
                id: `edge-${i}`,
                source: sourceId,
                target: targetId,
                type: e.type,
                schema_name: e.schema_name
            }
        });
    });

    // ── Cytoscape Initialization ─────────────────────────────────────────────

    // Check if we are in light theme initially
    const isLight = document.documentElement.classList.contains('theme-light');
    const getVar = (name, fallback) => {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    };

    const cy = cytoscape({
        container: container,
        elements: cyElements,
        style: [
            {
                selector: 'node[?isTable]',
                style: {
                    'shape': 'round-rectangle',
                    'background-color': isLight ? '#f1f5f9' : '#0f3460',
                    'border-color': isLight ? '#2563eb' : '#0984e3',
                    'border-width': 2,
                    'label': 'data(label)',
                    'color': isLight ? '#0f172a' : '#e8e8f0',
                    'font-family': 'Inter, sans-serif',
                    'font-size': 14,
                    'font-weight': 'bold',
                    'text-valign': 'top',
                    'text-halign': 'center',
                    'text-margin-y': -8,
                    'padding': 10
                }
            },
            {
                selector: 'node[?isColumn]',
                style: {
                    'shape': 'round-rectangle',
                    'background-color': isLight ? '#ffffff' : '#16213e',
                    'border-color': isLight ? '#cbd5e1' : '#5a5a72',
                    'border-width': 1,
                    'label': 'data(label)',
                    'color': isLight ? '#475569' : '#8b8ba3',
                    'font-family': 'Inter, monospace',
                    'font-size': 11,
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'padding': 6,
                    'width': 'label',
                    'height': 'label'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#a855f7', // Default N:N purple
                    'target-arrow-color': '#a855f7',
                    'target-arrow-shape': 'none',
                    'curve-style': 'bezier',
                    'opacity': 0.7
                }
            },
            {
                selector: 'edge[type="1:N"]',
                style: {
                    'line-color': isLight ? '#e11d48' : '#e94560',
                    'target-arrow-color': isLight ? '#e11d48' : '#e94560',
                    'target-arrow-shape': 'triangle'
                }
            },
            {
                selector: ':selected',
                style: {
                    'border-color': '#00cec9',
                    'border-width': 3,
                    'line-color': '#00cec9',
                    'target-arrow-color': '#00cec9'
                }
            },
            {
                selector: '.search-match',
                style: {
                    'border-width': 4,
                    'border-color': '#f59e0b',
                    'background-color': isLight ? '#fef3c7' : '#78350f',
                    'color': isLight ? '#92400e' : '#fef3c7'
                }
            },
            {
                selector: '.search-dim',
                style: {
                    'opacity': 0.15
                }
            }
        ],
        layout: {
            name: 'dagre',
            rankDir: 'LR',
            nodeSep: 50,
            edgeSep: 10,
            rankSep: 100
        },
        wheelSensitivity: 0.2
    });

    // Theme sync listener
    window.addEventListener('themeChanged', (e) => {
        const light = e.detail.theme === 'light';
        cy.style()
            .selector('node[?isTable]')
            .style({
                'background-color': light ? '#f1f5f9' : '#0f3460',
                'border-color': light ? '#2563eb' : '#0984e3',
                'color': light ? '#0f172a' : '#e8e8f0'
            })
            .selector('node[?isColumn]')
            .style({
                'background-color': light ? '#ffffff' : '#16213e',
                'border-color': light ? '#cbd5e1' : '#5a5a72',
                'color': light ? '#475569' : '#8b8ba3'
            })
            .selector('edge[type="1:N"]')
            .style({
                'line-color': light ? '#e11d48' : '#e94560',
                'target-arrow-color': light ? '#e11d48' : '#e94560'
            })
            .update();
    });

    // Show stats
    if (statsEl) {
        statsEl.textContent = `${data.nodes.length} tables · ${data.edges.length} relationships`;
    }

    // Hide loading
    cy.ready(() => {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    });

    // ── Controls ─────────────────────────────────────────────────────────────

    const fitBtn = document.getElementById('btn-fit');
    if (fitBtn) {
        fitBtn.addEventListener('click', () => {
            cy.fit(cy.elements(), 30);
        });
    }

    // Physics button is less relevant for dagre, maybe change to layout toggle
    const physicsBtn = document.getElementById('btn-physics');
    if (physicsBtn) {
        let isDagre = true;
        physicsBtn.innerHTML = '⟳ Relayout';
        physicsBtn.title = 'Re-run layout';
        physicsBtn.addEventListener('click', () => {
            isDagre = !isDagre;
            cy.layout({
                name: isDagre ? 'dagre' : 'cose',
                rankDir: 'LR',
                animate: true,
                animationDuration: 500
            }).run();
        });
    }

    const exportBtn = document.getElementById('btn-export');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const png64 = cy.png({ bg: isLight ? '#f8fafc' : '#0a0a1a' });
            const link = document.createElement('a');
            link.download = 'dataverse-diagram.png';
            link.href = png64;
            link.click();
        });
    }

    // ── Events ───────────────────────────────────────────────────────────────
    
    // Open table details panel when clicking a table node
    cy.on('tap', 'node[?isTable]', function(evt) {
        const node = evt.target;
        openTableDetails(node.id());
    });
    // Also support clicking column nodes to open parent table
    cy.on('tap', 'node[?isColumn]', function(evt) {
        const node = evt.target;
        openTableDetails(node.data('parent'));
    });

    window._cy = cy;
}

// ─── Table Details Panel ─────────────────────────────────────────────────────

function openTableDetails(logicalName) {
    let panel = document.getElementById('table-details-panel');
    if (!panel) {
        console.warn("Details panel not found in HTML");
        return;
    }
    
    panel.classList.add('open');
    const contentEl = document.getElementById('table-details-content');
    contentEl.innerHTML = '<div class="spinner"></div><p>Loading details...</p>';
    
    fetch(`/api/table/${logicalName}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            let html = `<h2 class="panel-title">${data.DisplayName}</h2>
                        <p class="panel-subtitle">${data.LogicalName}</p>
                        
                        <h3 class="panel-section-title">Columns (${data.Attributes.length})</h3>
                        <div class="column-list">`;
                        
            data.Attributes.forEach(attr => {
                let badges = '';
                if (attr.is_primary_id) badges += '<span class="badge badge--managed">PK</span> ';
                if (attr.is_primary_name) badges += '<span class="badge badge--unmanaged">Name</span> ';
                
                html += `<div class="column-item">
                            <div class="column-name">${attr.logical_name} ${badges}</div>
                            <div class="column-type">${attr.type}</div>
                         </div>`;
            });
            
            html += `</div>`;
            contentEl.innerHTML = html;
        })
        .catch(err => {
            contentEl.innerHTML = `<p class="error-text">Failed to load details: ${err.message}</p>`;
        });
}

function closeTableDetails() {
    const panel = document.getElementById('table-details-panel');
    if (panel) panel.classList.remove('open');
}


// ─── Column Search ────────────────────────────────────────────────────────────

let solutionColumns = null;

function fetchSolutionColumns(solutionId) {
    const searchInput = document.getElementById('column-search');
    if (!searchInput) return;

    fetch(`/api/solution/${solutionId}/columns`)
        .then(res => res.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            solutionColumns = data;
            searchInput.disabled = false;
            searchInput.placeholder = "Search columns...";
            
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                if (!window._cy) return;
                const cy = window._cy;

                cy.batch(() => {
                    if (!query) {
                        cy.elements().removeClass('search-match').removeClass('search-dim');
                        return;
                    }

                    // Find tables that have a matching column
                    const matchingTableIds = new Set();
                    for (const [tableName, cols] of Object.entries(solutionColumns)) {
                        for (const col of cols) {
                            if (col.logical_name && col.logical_name.toLowerCase().includes(query)) {
                                matchingTableIds.add(tableName);
                                break;
                            }
                        }
                    }

                    // Also search table names themselves just in case
                    cy.nodes('[?isTable]').forEach(node => {
                        const label = node.data('label').toLowerCase();
                        if (label.includes(query)) {
                            matchingTableIds.add(node.id());
                        }
                    });

                    cy.elements().removeClass('search-match').removeClass('search-dim');
                    
                    cy.nodes('[?isTable]').forEach(node => {
                        if (matchingTableIds.has(node.id())) {
                            node.addClass('search-match');
                        } else {
                            node.addClass('search-dim');
                        }
                    });
                    
                    // Dim columns that don't match or whose parent is dimmed
                    cy.nodes('[?isColumn]').forEach(node => {
                        const parentMatch = matchingTableIds.has(node.data('parent'));
                        const label = node.data('label').toLowerCase();
                        if (parentMatch && label.includes(query)) {
                            node.addClass('search-match');
                        } else {
                            node.addClass('search-dim');
                        }
                    });

                    // Dim edges
                    cy.edges().addClass('search-dim');
                });
            });
        })
        .catch(err => {
            console.error("Failed to fetch column metadata for search:", err);
            searchInput.placeholder = "Search unavailable";
        });
}

// ─── Flash Message Auto-dismiss ──────────────────────────────────────────────

function initFlashMessages() {
    const msgs = document.querySelectorAll('.flash-msg');
    msgs.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(30px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
}


// ─── Theme Toggle ────────────────────────────────────────────────────────────

function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    // Load preference from local storage
    const currentTheme = localStorage.getItem('theme') || 'dark';
    if (currentTheme === 'light') {
        document.documentElement.classList.add('theme-light');
        btn.textContent = '☀️';
    } else {
        document.documentElement.classList.remove('theme-light');
        btn.textContent = '🌙';
    }

    btn.addEventListener('click', () => {
        const isLight = document.documentElement.classList.toggle('theme-light');
        const newTheme = isLight ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        btn.textContent = isLight ? '☀️' : '🌙';

        // Optional: Trigger custom event for diagram re-render if needed
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
    });
}

// ─── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initSolutionSearch();
    initFlashMessages();

    // If we're on the diagram page, the solution ID is in a data attribute
    const diagramPage = document.getElementById('diagram-page');
    if (diagramPage) {
        const solutionId = diagramPage.dataset.solutionId;
        initDiagram(solutionId);
        
        // Fetch all columns in the background for searching
        fetchSolutionColumns(solutionId);
    }
});
