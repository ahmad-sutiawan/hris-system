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
      panel.classList.toggle("is-open");
    });

    document.addEventListener("click", function () {
      panel.classList.remove("is-open");
    });

    panel.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initNotifications();
  });
})();
