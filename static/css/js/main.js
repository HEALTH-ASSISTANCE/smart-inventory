// ==========================================
// 1. GLOBAL THEME PERSISTENCE (Runs Immediately)
// ==========================================
const savedTheme = localStorage.getItem('theme') || 'dark';
if (savedTheme === 'light') {
    document.body.classList.add('light-mode');
}

document.addEventListener("DOMContentLoaded", () => {
    // ==========================================
    // 2. ANIMATED STAT COUNTERS
    // ==========================================
    const statElements = document.querySelectorAll(".stat-card p, .report-value");
    
    statElements.forEach((el) => {
        const rawText = el.innerText.trim();
        const isCurrency = rawText.startsWith("$");
        const numericValue = parseFloat(rawText.replace(/[^0-9.]/g, ""));

        if (isNaN(numericValue)) return;

        let start = 0;
        const duration = 1000;
        const startTime = performance.now();

        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const currentVal = start + (numericValue - start) * progress;

            if (isCurrency) {
                el.innerText = `$${currentVal.toFixed(2)}`;
            } else {
                el.innerText = Math.floor(currentVal);
            }

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                el.innerText = rawText;
            }
        }

        requestAnimationFrame(updateCounter);
    });

    // ==========================================
    // 3. INTERACTIVE TABLE SORTING
    // ==========================================
    const getCellValue = (tr, idx) => {
        const cell = tr.children[idx];
        return cell ? cell.innerText || cell.textContent : "";
    };

    const comparer = (idx, asc) => (a, b) => {
        const v1 = getCellValue(asc ? a : b, idx).replace(/[^0-9.-]/g, "");
        const v2 = getCellValue(asc ? b : a, idx).replace(/[^0-9.-]/g, "");
        
        return !isNaN(parseFloat(v1)) && !isNaN(parseFloat(v2))
            ? parseFloat(v1) - parseFloat(v2)
            : getCellValue(asc ? a : b, idx).localeCompare(getCellValue(asc ? b : a, idx));
    };

    document.querySelectorAll("table th").forEach((th) => {
        th.style.cursor = "pointer";
        th.addEventListener("click", () => {
            const table = th.closest("table");
            const tbody = table.querySelector("tbody");
            const asc = th.dataset.asc === "true" ? false : true;
            th.dataset.asc = asc;

            Array.from(tbody.querySelectorAll("tr"))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), asc))
                .forEach((tr) => tbody.appendChild(tr));
        });
    });

    // ==========================================
    // 4. LIVE SEARCH FILTER
    // ==========================================
    const searchInputs = document.querySelectorAll('.search-form input[type="text"]');
    searchInputs.forEach((input) => {
        input.addEventListener("input", (e) => {
            const term = e.target.value.toLowerCase();
            const tableRows = document.querySelectorAll("tbody tr");

            tableRows.forEach((row) => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(term) ? "" : "none";
            });
        });
    });

    // ==========================================
    // 5. GLOBAL THEME TOGGLE LISTENER
    // ==========================================
    const themeBtn = document.getElementById('themeToggle');
    const themeLabel = document.getElementById('themeLabel');

    if (themeBtn) {
        // Set proper initial text based on loaded theme
        if (themeLabel) {
            themeLabel.textContent = document.body.classList.contains('light-mode') ? 'Light Mode' : '3D Glassmorphic (Dark)';
        }

        themeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const isLight = document.body.classList.toggle('light-mode');
            const newTheme = isLight ? 'light' : 'dark';
            localStorage.setItem('theme', newTheme);
            
            if (themeLabel) {
                themeLabel.textContent = isLight ? 'Light Mode' : '3D Glassmorphic (Dark)';
            }
        });
    }
});