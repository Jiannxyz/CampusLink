(function () {
  "use strict";

  function bindPreview(input, img, clearOnEmpty) {
    if (!input || !img) return;
    input.addEventListener("change", function () {
      var f = input.files && input.files[0];
      if (!f) {
        if (clearOnEmpty) {
          img.classList.add("d-none");
          img.removeAttribute("src");
        }
        return;
      }
      var url = URL.createObjectURL(f);
      img.onload = function () {
        URL.revokeObjectURL(url);
      };
      img.src = url;
      img.classList.remove("d-none");
    });
  }

  var pIn = document.getElementById("profilePhotoInput");
  var pPrev = document.getElementById("profilePhotoPreview");
  bindPreview(pIn, pPrev, true);

  var cIn = document.getElementById("coverPhotoInput");
  var cPrev = document.getElementById("coverPhotoPreview");
  var coverCurrent = document.getElementById("coverCurrent");
  var coverPh = document.getElementById("coverPlaceholder");
  if (cIn && cPrev) {
    cIn.addEventListener("change", function () {
      var f = cIn.files && cIn.files[0];
      if (!f) {
        cPrev.classList.add("d-none");
        cPrev.removeAttribute("src");
        return;
      }
      if (coverCurrent) coverCurrent.classList.add("d-none");
      if (coverPh) coverPh.classList.add("d-none");
      var url = URL.createObjectURL(f);
      cPrev.onload = function () {
        URL.revokeObjectURL(url);
      };
      cPrev.src = url;
      cPrev.classList.remove("d-none");
    });
  }
})();
