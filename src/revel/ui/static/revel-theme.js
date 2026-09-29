(function () {
  var key = "revel-theme";
  function apply(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    try { localStorage.setItem(key, theme); } catch (e) {}
    var btn = document.getElementById("revel-theme-toggle");
    if (btn) btn.textContent = theme === "dark" ? "Light" : "Dark";
  }
  function initial() {
    try {
      var saved = localStorage.getItem(key);
      if (saved === "light" || saved === "dark") return saved;
    } catch (e) {}
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }
  apply(initial());
  document.addEventListener("click", function (ev) {
    if (ev.target && ev.target.id === "revel-theme-toggle") {
      var next = document.documentElement.getAttribute("data-bs-theme") === "dark"
        ? "light" : "dark";
      apply(next);
    }
  });
  var path = location.pathname;
  document.querySelectorAll(".revel-nav .nav-link").forEach(function (a) {
    if (a.getAttribute("href") === path || (path === "/" && a.getAttribute("href") === "/ui/dashboard")) {
      a.classList.add("active");
    }
  });
})();
