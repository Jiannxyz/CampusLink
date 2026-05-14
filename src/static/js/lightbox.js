/* Fullscreen-style image lightbox (Bootstrap modal) */
(function () {
  "use strict";

  var modalEl = document.getElementById("clLightboxModal");
  var imgEl = document.getElementById("clLightboxImg");
  if (!modalEl || !imgEl || typeof bootstrap === "undefined") {
    return;
  }

  var modal = bootstrap.Modal.getOrCreateInstance(modalEl, { keyboard: true });
  var urls = [];
  var index = 0;
  var prevBtn = modalEl.querySelector(".cl-lightbox-prev");
  var nextBtn = modalEl.querySelector(".cl-lightbox-next");
  var loader = modalEl.querySelector(".cl-lightbox-loader");

  function showIndex(i) {
    if (!urls.length) {
      return;
    }
    index = (i + urls.length) % urls.length;
    if (loader) {
      loader.classList.add("is-active");
    }
    imgEl.classList.remove("is-loaded");
    var src = urls[index];
    imgEl.onload = function () {
      imgEl.onload = null;
      if (loader) {
        loader.classList.remove("is-active");
      }
      imgEl.classList.add("is-loaded");
    };
    imgEl.src = src;
    if (prevBtn) {
      prevBtn.classList.toggle("d-none", urls.length < 2);
    }
    if (nextBtn) {
      nextBtn.classList.toggle("d-none", urls.length < 2);
    }
  }

  function openFromList(list, start) {
    urls = list.slice();
    showIndex(start || 0);
    modal.show();
  }

  function parseGalleryJson(raw) {
    try {
      var data = JSON.parse(raw);
      return Array.isArray(data) ? data.filter(Boolean) : [];
    } catch (e) {
      return [];
    }
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (!(t instanceof Element)) {
      return;
    }
    var single = t.closest("[data-cl-lightbox-src]");
    if (single) {
      ev.preventDefault();
      var u = single.getAttribute("data-cl-lightbox-src");
      if (u) {
        openFromList([u], 0);
      }
      return;
    }
    var cell = t.closest(".feed-gallery-cell");
    if (cell) {
      var article = cell.closest("[data-feed-gallery]");
      if (!article) {
        return;
      }
      var list = parseGalleryJson(article.getAttribute("data-feed-gallery") || "[]");
      if (!list.length) {
        return;
      }
      var imgs = article.querySelectorAll(".feed-gallery-cell img");
      var idx = 0;
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].contains(t) || imgs[i] === t) {
          idx = i;
          break;
        }
      }
      ev.preventDefault();
      openFromList(list, idx);
    }
  });

  if (prevBtn) {
    prevBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      showIndex(index - 1);
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      showIndex(index + 1);
    });
  }

  modalEl.addEventListener("hidden.bs.modal", function () {
    imgEl.removeAttribute("src");
    urls = [];
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && modalEl.classList.contains("show")) {
      modal.hide();
    }
  });
})();
