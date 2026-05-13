/* CampusLink — light UX enhancements (Bootstrap 5) */
(function () {
  "use strict";

  var sidebar = document.getElementById("appSidebar");
  if (!sidebar || typeof bootstrap === "undefined") {
    return;
  }

  var oc = bootstrap.Offcanvas.getOrCreateInstance(sidebar);

  sidebar.querySelectorAll(".campus-sidenav-link").forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.matchMedia("(max-width: 991.98px)").matches) {
        oc.hide();
      }
    });
  });
})();
