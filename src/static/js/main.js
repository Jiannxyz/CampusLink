/* CampusLink — light UX enhancements (Bootstrap 5) */
(function () {
  "use strict";

  var nav = document.querySelector("header.cl-topnav");
  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 12) {
        nav.classList.add("cl-topnav--dense");
      } else {
        nav.classList.remove("cl-topnav--dense");
      }
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

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
