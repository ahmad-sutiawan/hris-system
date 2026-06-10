(function () {
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
        if (!window.confirm("Keluar dari HRIS-Lite?")) {
          event.preventDefault();
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initNotifications();
    initUserMenu();
  });
})();
