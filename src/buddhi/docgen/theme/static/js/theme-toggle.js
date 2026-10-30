// Theme toggle supporting prefers-color-scheme and localStorage
(function () {
  const toggleBtn = document.getElementById("theme-toggle");
  if (!toggleBtn) return;

  const currentTheme = localStorage.getItem("buddhi_theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  document.documentElement.setAttribute("data-theme", currentTheme);

  toggleBtn.addEventListener("click", function () {
    const active = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", active);
    localStorage.setItem("buddhi_theme", active);
  });
})();

