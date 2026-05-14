(function () {
  "use strict";

  function wireBrowse(btnId, inputId) {
    var btn = document.getElementById(btnId);
    var input = document.getElementById(inputId);
    if (!btn || !input) return;
    btn.addEventListener("click", function () {
      input.click();
    });
  }

  function bindProfilePreview(input, previewImg, chromeEl) {
    var lastUrl;
    if (!input || !previewImg) return;
    input.addEventListener("change", function () {
      var f = input.files && input.files[0];
      if (lastUrl) {
        try {
          URL.revokeObjectURL(lastUrl);
        } catch (e) {}
        lastUrl = null;
      }
      if (!f) {
        previewImg.classList.add("d-none");
        previewImg.removeAttribute("src");
        if (chromeEl) chromeEl.classList.remove("d-none");
        return;
      }
      lastUrl = URL.createObjectURL(f);
      previewImg.src = lastUrl;
      previewImg.classList.remove("d-none");
      if (chromeEl) chromeEl.classList.add("d-none");
    });
  }

  function bindCoverPreview(input, previewImg, coverCurrent, coverPh) {
    var lastUrl;
    if (!input || !previewImg) return;
    input.addEventListener("change", function () {
      var f = input.files && input.files[0];
      if (lastUrl) {
        try {
          URL.revokeObjectURL(lastUrl);
        } catch (e) {}
        lastUrl = null;
      }
      if (!f) {
        previewImg.classList.add("d-none");
        previewImg.removeAttribute("src");
        if (coverCurrent) coverCurrent.classList.remove("d-none");
        if (coverPh) coverPh.classList.remove("d-none");
        return;
      }
      lastUrl = URL.createObjectURL(f);
      previewImg.src = lastUrl;
      previewImg.classList.remove("d-none");
      if (coverCurrent) coverCurrent.classList.add("d-none");
      if (coverPh) coverPh.classList.add("d-none");
    });
  }

  var pIn = document.getElementById("profilePhotoInput");
  var pPrev = document.getElementById("profilePhotoPreview");
  var pChrome = document.getElementById("profileAvatarChrome");
  bindProfilePreview(pIn, pPrev, pChrome);
  wireBrowse("profilePhotoBrowseBtn", "profilePhotoInput");

  var cIn = document.getElementById("coverPhotoInput");
  var cPrev = document.getElementById("coverPhotoPreview");
  var coverCurrent = document.getElementById("coverCurrent");
  var coverPh = document.getElementById("coverPlaceholder");
  bindCoverPreview(cIn, cPrev, coverCurrent, coverPh);
})();
