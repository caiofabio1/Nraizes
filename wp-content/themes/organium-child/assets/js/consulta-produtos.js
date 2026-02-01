/**
 * Ferramenta de Consulta de Produtos - Novas Raizes
 * 
 * GEO-Optimized: JS handles ONLY interactivity (search, filters).
 * All content is server-side rendered in PHP and already in the DOM.
 * LLM crawlers see the full HTML without needing JS execution.
 */
(function() {
    'use strict';

    var DEBOUNCE_MS = 250;
    var cards = [];
    var currentCategory = 'todos';
    var currentSearch = '';
    var currentEvidence = 'todos';

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        // Collect all server-rendered cards
        cards = Array.prototype.slice.call(
            document.querySelectorAll('#nrc-results .nrc-card')
        );
        if (!cards.length) return;

        bindSearch();
        bindCategoryFilters();
        bindEvidenceFilters();
        bindResetButton();
        bindKeyboard();
    }

    /* ============================
       Search
       ============================ */
    function bindSearch() {
        var input = document.getElementById('nrc-search');
        var clearBtn = document.getElementById('nrc-clear-search');
        if (!input) return;

        input.addEventListener('input', debounce(function() {
            currentSearch = input.value.trim().toLowerCase();
            if (clearBtn) clearBtn.style.display = currentSearch ? 'flex' : 'none';
            applyFilters();
        }, DEBOUNCE_MS));

        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                input.value = '';
                currentSearch = '';
                clearBtn.style.display = 'none';
                applyFilters();
                input.focus();
            });
        }
    }

    /* ============================
       Category Filters
       ============================ */
    function bindCategoryFilters() {
        var btns = document.querySelectorAll('.nrc-filter-btn');
        btns.forEach(function(btn) {
            btn.addEventListener('click', function() {
                btns.forEach(function(b) {
                    b.classList.remove('nrc-active');
                    b.setAttribute('aria-pressed', 'false');
                });
                this.classList.add('nrc-active');
                this.setAttribute('aria-pressed', 'true');
                currentCategory = this.dataset.categoria || 'todos';
                applyFilters();
            });
        });
    }

    /* ============================
       Evidence Level Filters
       ============================ */
    function bindEvidenceFilters() {
        var btns = document.querySelectorAll('.nrc-evidence-btn');
        btns.forEach(function(btn) {
            btn.addEventListener('click', function() {
                btns.forEach(function(b) {
                    b.classList.remove('nrc-active');
                    b.setAttribute('aria-pressed', 'false');
                });
                this.classList.add('nrc-active');
                this.setAttribute('aria-pressed', 'true');
                currentEvidence = this.dataset.nivel || 'todos';
                applyFilters();
            });
        });
    }

    /* ============================
       Reset
       ============================ */
    function bindResetButton() {
        var btn = document.getElementById('nrc-reset-filters');
        if (!btn) return;
        btn.addEventListener('click', function() {
            var input = document.getElementById('nrc-search');
            var clearBtn = document.getElementById('nrc-clear-search');
            if (input) input.value = '';
            if (clearBtn) clearBtn.style.display = 'none';
            currentSearch = '';
            currentCategory = 'todos';
            currentEvidence = 'todos';

            // Reset button states
            document.querySelectorAll('.nrc-filter-btn').forEach(function(b) {
                b.classList.remove('nrc-active');
                b.setAttribute('aria-pressed', 'false');
            });
            var todosBtn = document.querySelector('.nrc-filter-btn[data-categoria="todos"]');
            if (todosBtn) {
                todosBtn.classList.add('nrc-active');
                todosBtn.setAttribute('aria-pressed', 'true');
            }

            document.querySelectorAll('.nrc-evidence-btn').forEach(function(b) {
                b.classList.remove('nrc-active');
                b.setAttribute('aria-pressed', 'false');
            });
            var evTodos = document.querySelector('.nrc-evidence-btn[data-nivel="todos"]');
            if (evTodos) {
                evTodos.classList.add('nrc-active');
                evTodos.setAttribute('aria-pressed', 'true');
            }

            applyFilters();
        });
    }

    /* ============================
       Keyboard
       ============================ */
    function bindKeyboard() {
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                var input = document.getElementById('nrc-search');
                var clearBtn = document.getElementById('nrc-clear-search');
                if (input && input.value) {
                    input.value = '';
                    currentSearch = '';
                    if (clearBtn) clearBtn.style.display = 'none';
                    applyFilters();
                }
            }
        });
    }

    /* ============================
       Core Filter Logic
       ============================ */
    function applyFilters() {
        var visibleCount = 0;

        cards.forEach(function(card) {
            var show = true;

            // Category filter
            if (currentCategory !== 'todos') {
                var cardCat = card.getAttribute('data-categoria') || '';
                if (cardCat !== currentCategory) {
                    show = false;
                }
            }

            // Evidence filter
            if (show && currentEvidence !== 'todos') {
                var cardEv = card.getAttribute('data-evidencia') || '';
                if (currentEvidence === 'alta') {
                    show = cardEv.indexOf('alta') !== -1;
                } else if (currentEvidence === 'moderada') {
                    show = cardEv.indexOf('moderada') !== -1;
                } else if (currentEvidence === 'baixa') {
                    show = cardEv === 'baixa' || cardEv === 'baixa-moderada' || cardEv === 'muito-baixa';
                }
            }

            // Search filter
            if (show && currentSearch) {
                var searchText = card.getAttribute('data-search') || '';
                var terms = currentSearch.split(/\s+/);
                for (var i = 0; i < terms.length; i++) {
                    if (terms[i] && searchText.indexOf(terms[i]) === -1) {
                        show = false;
                        break;
                    }
                }
            }

            card.style.display = show ? '' : 'none';
            if (show) visibleCount++;
        });

        // Update counter
        var totalEl = document.getElementById('nrc-total-visible');
        if (totalEl) totalEl.textContent = visibleCount;

        // No results message
        var noResults = document.getElementById('nrc-no-results');
        if (noResults) {
            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }
    }

    /* ============================
       Utilities
       ============================ */
    function debounce(fn, ms) {
        var timer;
        return function() {
            var args = arguments;
            var ctx = this;
            clearTimeout(timer);
            timer = setTimeout(function() { fn.apply(ctx, args); }, ms);
        };
    }
})();
