/* Landing — scroll reveal for .cl-reveal */
(function () {
  "use strict";

  var els = document.querySelectorAll(".cl-reveal");
  if (!els.length) {
    return;
  }

  function revealAll() {
    els.forEach(function (el) {
      el.classList.add("cl-reveal-visible");
    });
  }

  if (!("IntersectionObserver" in window)) {
    revealAll();
    return;
  }

  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add("cl-reveal-visible");
          io.unobserve(en.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -32px 0px" }
  );

  els.forEach(function (el) {
    io.observe(el);
  });
})();
