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

  function setStatus(el, message, tone) {
    if (!el) return;
    if (!message) {
      el.classList.add("d-none");
      el.textContent = "";
      el.classList.remove("text-success", "text-danger", "text-muted");
      return;
    }
    el.classList.remove("d-none", "text-success", "text-danger", "text-muted");
    if (tone === "success") el.classList.add("text-success");
    else if (tone === "danger") el.classList.add("text-danger");
    else el.classList.add("text-muted");
    el.textContent = message;
  }

  function bindProfilePreview(input, previewImg, chromeEl, statusEl, removeCheckbox) {
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
        previewImg.classList.remove("is-visible");
        if (chromeEl) chromeEl.classList.remove("d-none");
        setStatus(statusEl, "", null);
        return;
      }
      if (removeCheckbox) removeCheckbox.checked = false;
      lastUrl = URL.createObjectURL(f);
      previewImg.src = lastUrl;
      previewImg.classList.remove("d-none");
      requestAnimationFrame(function () {
        previewImg.classList.add("is-visible");
      });
      if (chromeEl) chromeEl.classList.add("d-none");
      setStatus(statusEl, "Preview ready — save to apply.", "muted");
    });
  }

  function bindCoverPreview(input, previewImg, coverCurrent, coverPh, statusEl, removeCheckbox) {
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
        previewImg.classList.remove("is-visible");
        previewImg.removeAttribute("src");
        if (coverCurrent) {
          coverCurrent.classList.remove("d-none");
          coverCurrent.classList.add("is-visible");
        }
        if (coverPh) coverPh.classList.remove("d-none");
        setStatus(statusEl, "", null);
        return;
      }
      if (removeCheckbox) removeCheckbox.checked = false;
      lastUrl = URL.createObjectURL(f);
      previewImg.src = lastUrl;
      previewImg.classList.remove("d-none");
      requestAnimationFrame(function () {
        previewImg.classList.add("is-visible");
        if (coverCurrent) coverCurrent.classList.remove("is-visible");
      });
      if (coverCurrent) coverCurrent.classList.add("d-none");
      if (coverPh) coverPh.classList.add("d-none");
      setStatus(statusEl, "Cover preview ready — save to apply.", "muted");
    });
  }

  var form = document.getElementById("profileEditForm");
  var submitBtn = document.getElementById("profileEditSubmit");
  if (form && submitBtn) {
    form.addEventListener("submit", function () {
      submitBtn.disabled = true;
      var label = submitBtn.querySelector(".profile-edit-submit-label");
      var spinner = submitBtn.querySelector(".profile-edit-submit-spinner");
      if (label) label.textContent = "Saving…";
      if (spinner) spinner.classList.remove("d-none");
    });
  }

  var removeProfile = document.getElementById("removeProfilePhoto");
  var removeCover = document.getElementById("removeCoverPhoto");

  var pIn = document.getElementById("profilePhotoInput");
  var pPrev = document.getElementById("profilePhotoPreview");
  var pChrome = document.getElementById("profileAvatarChrome");
  var pStatus = document.getElementById("profilePhotoUploadStatus");
  bindProfilePreview(pIn, pPrev, pChrome, pStatus, removeProfile);
  wireBrowse("profilePhotoBrowseBtn", "profilePhotoInput");

  var cIn = document.getElementById("coverPhotoInput");
  var cPrev = document.getElementById("coverPhotoPreview");
  var coverCurrent = document.getElementById("coverCurrent");
  var coverPh = document.getElementById("coverPlaceholder");
  var cStatus = document.getElementById("coverPhotoUploadStatus");
  bindCoverPreview(cIn, cPrev, coverCurrent, coverPh, cStatus, removeCover);

  if (coverCurrent) coverCurrent.classList.add("is-visible");
})();
