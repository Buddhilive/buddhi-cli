// Client-side search for Buddhi documentation
(function () {
  let searchIndex = null;
  const modal = document.getElementById("search-modal");
  const input = document.getElementById("search-input");
  const resultsList = document.getElementById("search-results-list");
  const trigger = document.getElementById("search-trigger");
  const closeBtn = document.getElementById("search-close-btn");

  if (!modal || !input || !resultsList) return;

  function getBaseUrl() {
    const cssLink = document.querySelector('link[rel="stylesheet"][href*="theme.css"]');
    if (cssLink) {
      const href = cssLink.getAttribute("href") || "";
      return href.replace(/theme\/css\/theme\.css$/, "");
    }
    return "./";
  }

  async function loadIndex() {
    if (searchIndex !== null) return;
    try {
      const baseUrl = getBaseUrl();
      const res = await fetch(baseUrl + "search-index.json");
      if (res.ok) {
        searchIndex = await res.json();
      } else {
        searchIndex = [];
      }
    } catch (e) {
      searchIndex = [];
    }
  }

  function openSearch() {
    modal.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    loadIndex();
    input.focus();
  }

  function closeSearch() {
    modal.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    input.value = "";
    resultsList.innerHTML = '<li role="option" id="search-default-option" class="search-hint" aria-selected="false">Type to search concepts and symbols...</li>';
    trigger.focus();
  }

  if (trigger) trigger.addEventListener("click", openSearch);
  if (closeBtn) closeBtn.addEventListener("click", closeSearch);

  window.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      e.preventDefault();
      openSearch();
    } else if (e.key === "Escape" && !modal.hidden) {
      closeSearch();
    }
  });

  input.addEventListener("input", function () {
    const q = input.value.trim().toLowerCase();
    resultsList.innerHTML = "";
    if (!q || !searchIndex) {
      resultsList.innerHTML = '<li class="search-hint">Type to search concepts and symbols...</li>';
      return;
    }

    const matches = searchIndex.filter(item =>
      (item.title && item.title.toLowerCase().includes(q)) ||
      (item.summary && item.summary.toLowerCase().includes(q)) ||
      (item.kind && item.kind.toLowerCase().includes(q)) ||
      (item.tags && item.tags.some(t => t.toLowerCase().includes(q)))
    ).slice(0, 12);

    if (matches.length === 0) {
      const li = document.createElement("li");
      li.className = "search-hint";
      li.textContent = "No matching concepts or symbols found.";
      resultsList.appendChild(li);
      return;
    }

    const baseUrl = getBaseUrl();
    matches.forEach(m => {
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      const a = document.createElement("a");
      a.className = "search-result-item";
      a.href = baseUrl + m.url;

      const header = document.createElement("div");
      header.className = "search-result-header";

      const title = document.createElement("span");
      title.className = "search-result-title";
      title.textContent = m.title;

      const kind = document.createElement("span");
      kind.className = "search-result-kind";
      kind.textContent = m.kind || "concept";

      header.appendChild(title);
      header.appendChild(kind);
      a.appendChild(header);

      if (m.summary) {
        const desc = document.createElement("p");
        desc.className = "search-result-summary";
        desc.textContent = m.summary;
        a.appendChild(desc);
      }

      li.appendChild(a);
      resultsList.appendChild(li);
    });
  });
})();
