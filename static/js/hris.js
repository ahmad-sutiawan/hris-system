(function () {
  function initSidebarScrollMemory() {
    var nav = document.querySelector(".hris-nav");
    if (!nav) return;

    var storageKey = "hris-sidebar-scroll";
    var saved = sessionStorage.getItem(storageKey);
    if (saved !== null) {
      var top = parseInt(saved, 10);
      if (!isNaN(top)) {
        nav.scrollTop = top;
        requestAnimationFrame(function () {
          nav.scrollTop = top;
        });
      }
    }

    var persist = function () {
      sessionStorage.setItem(storageKey, String(nav.scrollTop));
    };

    nav.addEventListener("scroll", persist, { passive: true });

    nav.querySelectorAll(".hris-nav-link").forEach(function (link) {
      link.addEventListener("click", persist);
    });
  }

  function initSidebar() {
    var toggle = document.getElementById("hris-menu-toggle");
    var sidebar = document.getElementById("hris-sidebar");
    var backdrop = document.getElementById("hris-sidebar-backdrop");
    if (!toggle || !sidebar || !backdrop) return;

    function close() {
      sidebar.classList.remove("is-open");
      backdrop.classList.remove("is-visible");
    }

    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("is-open");
      backdrop.classList.toggle("is-visible");
    });

    backdrop.addEventListener("click", close);
    sidebar.querySelectorAll(".hris-nav-link").forEach(function (link) {
      link.addEventListener("click", close);
    });
  }

  function initNotifications() {
    var btn = document.getElementById("hris-notif-btn");
    var panel = document.getElementById("hris-notif-panel");
    if (!btn || !panel) return;

    btn.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      closeUserMenu();
      panel.classList.toggle("is-open");
    });

    document.addEventListener("click", function () {
      panel.classList.remove("is-open");
    });

    panel.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  }

  function closeUserMenu() {
    var panel = document.getElementById("hris-user-menu-panel");
    var btn = document.getElementById("hris-user-menu-btn");
    if (panel) panel.classList.remove("is-open");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  function initUserMenu() {
    var btn = document.getElementById("hris-user-menu-btn");
    var panel = document.getElementById("hris-user-menu-panel");
    if (!btn || !panel) return;

    btn.addEventListener("click", function (event) {
      event.stopPropagation();
      var notifPanel = document.getElementById("hris-notif-panel");
      if (notifPanel) notifPanel.classList.remove("is-open");
      var open = panel.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });

    document.addEventListener("click", closeUserMenu);
    panel.addEventListener("click", function (event) {
      event.stopPropagation();
    });

    panel.querySelectorAll(".hris-user-menu-logout, .hris-sidebar-logout-btn").forEach(function (el) {
      el.addEventListener("click", function (event) {
        if (!window.confirm("Keluar dari BPS HRIS?")) {
          event.preventDefault();
        }
      });
    });
  }

  function initSidebarSearch() {
    var input = document.getElementById("hris-sidebar-search");
    var nav = document.getElementById("hris-nav");
    var empty = document.getElementById("hris-sidebar-search-empty");
    if (!input || !nav) return;

    function buildSearchText(link) {
      var parts = [];
      var el = link.parentElement;
      while (el && el !== nav) {
        if (el.classList && el.classList.contains("hris-nav-section")) {
          var label = el.querySelector(":scope > .hris-nav-label");
          if (label) parts.unshift(label.textContent.trim());
        }
        el = el.parentElement;
      }
      parts.push(link.textContent.replace(/\s+/g, " ").trim());
      return parts.join(" ").toLowerCase();
    }

    var links = nav.querySelectorAll(".hris-nav-link");
    links.forEach(function (link) {
      link.dataset.navSearch = buildSearchText(link);
    });

    function filterNav() {
      var query = input.value.trim().toLowerCase();

      links.forEach(function (link) {
        var match = !query || link.dataset.navSearch.indexOf(query) !== -1;
        link.classList.toggle("is-nav-hidden", !match);
      });

      var sections = Array.from(nav.querySelectorAll(".hris-nav-section")).reverse();
      sections.forEach(function (section) {
        if (!query) {
          section.classList.remove("is-nav-hidden");
          return;
        }
        var hasVisible = Array.from(section.querySelectorAll(".hris-nav-link")).some(function (link) {
          return !link.classList.contains("is-nav-hidden");
        });
        section.classList.toggle("is-nav-hidden", !hasVisible);
      });

      if (empty) {
        var anyVisible = Array.from(links).some(function (link) {
          return !link.classList.contains("is-nav-hidden");
        });
        empty.hidden = !query || anyVisible;
      }
    }

    input.addEventListener("input", filterNav);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        input.value = "";
        filterNav();
        input.blur();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSidebarScrollMemory();
    initSidebarSearch();
    initSidebar();
    initNotifications();
    initUserMenu();
  });
})();
