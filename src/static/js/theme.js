/* CampusLink theme: <html data-bs-theme="light|dark"> + localStorage */
(function () {
  "use strict";

  var KEY = "campuslink-theme";

  function apply(theme) {
    var t = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-bs-theme", t);
    try {
      localStorage.setItem(KEY, t);
    } catch (e) {
      /* ignore */
    }
  }

  function readStored() {
    try {
      var s = localStorage.getItem(KEY);
      if (s === "dark" || s === "light") {
        return s;
      }
    } catch (e) {
      /* ignore */
    }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function init() {
    if (!document.documentElement.getAttribute("data-bs-theme")) {
      apply(readStored());
    }
    document.querySelectorAll("[data-cl-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cur = document.documentElement.getAttribute("data-bs-theme") || "light";
        apply(cur === "dark" ? "light" : "dark");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
