// Client-side search for Buddhi documentation
(function () {
  let searchIndex = null;
  const modal = document.getElementById("search-modal");
  const input = document.getElementById("search-input");
  const resultsList = document.getElementById("search-results-list");
  const trigger = document.getElementById("search-trigger");
  const closeBtn = document.getElementById("search-close-btn");

  if (!modal || !input || !resultsList) return;

  async function loadIndex() {
    if (searchIndex !== null) return;
    try {
      const res = await fetch("search-index.json");
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
    resultsList.innerHTML = "";
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
    if (!q || !searchIndex) return;

    const matches = searchIndex.filter(item =>
      (item.title && item.title.toLowerCase().includes(q)) ||
      (item.summary && item.summary.toLowerCase().includes(q)) ||
      (item.tags && item.tags.some(t => t.toLowerCase().includes(q)))
    ).slice(0, 10);

    if (matches.length === 0) {
      const li = document.createElement("li");
      li.className = "search-empty";
      li.textContent = "No matching concepts found.";
      resultsList.appendChild(li);
      return;
    }

    matches.forEach(m => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = m.url;
      a.textContent = m.title;
      li.appendChild(a);
      resultsList.appendChild(li);
    });
  });
})();

