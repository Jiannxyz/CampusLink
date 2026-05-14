(function () {
    "use strict";

    function qs(sel, root) {
        return (root || document).querySelector(sel);
    }

    function qsa(sel, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }

    function autosizeTextarea(el) {
        if (!el) return;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 480) + "px";
    }

    function updateSubmitState(form) {
        var title = qs("#composer-title", form);
        var content = qs("#composer-content", form);
        var btn = qs("#composer-submit", form);
        if (!btn || !title || !content) return;
        var ok = title.value.trim().length > 0 && content.value.trim().length > 0;
        btn.disabled = !ok;
    }

    function renderPreviews(container, files, fileInput) {
        container.innerHTML = "";
        if (!files || !files.length) {
            container.classList.add("d-none");
            return;
        }
        container.classList.remove("d-none");
        var dt = new DataTransfer();
        for (var i = 0; i < files.length; i++) {
            dt.items.add(files[i]);
        }
        fileInput.files = dt.files;

        files.forEach(function (file, idx) {
            var col = document.createElement("div");
            col.className = "col-6 col-md-4";
            var wrap = document.createElement("div");
            wrap.className = "position-relative rounded-3 overflow-hidden border bg-light feed-preview-tile";
            var img = document.createElement("img");
            img.alt = "";
            img.className = "w-100 object-fit-cover";
            img.style.maxHeight = "140px";
            img.src = URL.createObjectURL(file);
            var rm = document.createElement("button");
            rm.type = "button";
            rm.className = "btn btn-sm btn-dark position-absolute top-0 end-0 m-1 rounded-circle";
            rm.innerHTML = '<i class="bi bi-x-lg"></i>';
            rm.setAttribute("aria-label", "Remove image");
            rm.addEventListener("click", function () {
                URL.revokeObjectURL(img.src);
                var next = new DataTransfer();
                for (var j = 0; j < fileInput.files.length; j++) {
                    if (j !== idx) next.items.add(fileInput.files[j]);
                }
                fileInput.files = next.files;
                renderPreviews(container, Array.prototype.slice.call(fileInput.files), fileInput);
            });
            wrap.appendChild(img);
            wrap.appendChild(rm);
            col.appendChild(wrap);
            container.appendChild(col);
        });
    }

    function wireComposer() {
        var form = qs("#feed-composer-form");
        if (!form) return;

        var fileInput = qs("#composer-files", form);
        var dropzone = qs("#composer-dropzone", form);
        var browseBtn = qs("#composer-browse-btn", form);
        var preview = qs("#composer-preview", form);
        var collapse = qs("#feedComposerCollapse");
        var redirectCompose = qs("#feed-redirect-compose");
        var title = qs("#composer-title", form);
        var content = qs("#composer-content", form);
        var progress = qs("#composer-progress", form);

        function markComposeOpen() {
            if (redirectCompose) redirectCompose.value = "1";
        }

        if (collapse) {
            collapse.addEventListener("shown.bs.collapse", markComposeOpen);
        }
        qsa('[data-bs-target="#feedComposerCollapse"]').forEach(function (btn) {
            btn.addEventListener("click", function () {
                setTimeout(markComposeOpen, 0);
            });
        });

        if (browseBtn && fileInput) {
            browseBtn.addEventListener("click", function () {
                fileInput.click();
            });
        }

        if (dropzone && fileInput) {
            dropzone.addEventListener("click", function () {
                fileInput.click();
            });
            dropzone.addEventListener("dragover", function (e) {
                e.preventDefault();
                dropzone.classList.add("feed-dropzone--active");
            });
            dropzone.addEventListener("dragleave", function () {
                dropzone.classList.remove("feed-dropzone--active");
            });
            dropzone.addEventListener("drop", function (e) {
                e.preventDefault();
                dropzone.classList.remove("feed-dropzone--active");
                var incoming = e.dataTransfer.files;
                var dt = new DataTransfer();
                var existing = fileInput.files ? Array.prototype.slice.call(fileInput.files) : [];
                existing.forEach(function (f) {
                    dt.items.add(f);
                });
                for (var i = 0; i < incoming.length; i++) {
                    if (dt.files.length >= 8) break;
                    dt.items.add(incoming[i]);
                }
                fileInput.files = dt.files;
                renderPreviews(preview, Array.prototype.slice.call(fileInput.files), fileInput);
            });
        }

        if (fileInput && preview) {
            fileInput.addEventListener("change", function () {
                renderPreviews(preview, Array.prototype.slice.call(fileInput.files), fileInput);
            });
        }

        if (title) title.addEventListener("input", function () {
            updateSubmitState(form);
        });
        if (content) {
            content.addEventListener("input", function () {
                autosizeTextarea(content);
                updateSubmitState(form);
            });
            autosizeTextarea(content);
        }
        updateSubmitState(form);

        form.addEventListener("submit", function () {
            if (progress) {
                progress.classList.remove("d-none");
                progress.textContent = "Posting…";
            }
        });
    }

    function wireShareButtons() {
        qsa(".feed-share-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var url = btn.getAttribute("data-share-url");
                if (!url) return;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url).then(function () {
                        btn.classList.add("text-success");
                        var prev = btn.innerHTML;
                        btn.innerHTML = '<i class="bi bi-check2"></i>';
                        setTimeout(function () {
                            btn.innerHTML = prev;
                            btn.classList.remove("text-success");
                        }, 1600);
                    });
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        wireComposer();
        wireShareButtons();
    });
})();
