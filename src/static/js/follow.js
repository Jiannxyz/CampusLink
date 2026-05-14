/* Follow / unfollow AJAX for .cl-follow-wrap */
(function () {
  "use strict";

  function postJson(url) {
    return fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (body) {
        return { ok: r.ok, status: r.status, body: body };
      });
    });
  }

  function setWrapState(wrap, state, followersCount) {
    wrap.setAttribute("data-cl-follow-state", state || "none");
    var doBtn = wrap.querySelector('[data-cl-follow-action="follow"]');
    var undoBtn = wrap.querySelector('[data-cl-follow-action="unfollow"]');
    var pend = wrap.querySelector(".cl-follow-pending");
    if (state === "accepted") {
      if (doBtn) {
        doBtn.hidden = true;
      }
      if (undoBtn) {
        undoBtn.hidden = false;
      }
      if (pend) {
        pend.classList.add("d-none");
      }
    } else if (state === "pending") {
      if (doBtn) {
        doBtn.hidden = true;
      }
      if (undoBtn) {
        undoBtn.hidden = true;
      }
      if (pend) {
        pend.classList.remove("d-none");
      }
    } else {
      if (doBtn) {
        doBtn.hidden = false;
      }
      if (undoBtn) {
        undoBtn.hidden = true;
      }
      if (pend) {
        pend.classList.add("d-none");
      }
    }
    if (followersCount != null) {
      document.querySelectorAll('[data-cl-follow-count="' + uid + '"]').forEach(function (el) {
        el.textContent = String(followersCount);
      });
    }
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".cl-follow-btn");
    if (!btn) {
      return;
    }
    var wrap = btn.closest(".cl-follow-wrap");
    if (!wrap) {
      return;
    }
    var uid = wrap.getAttribute("data-cl-follow-target");
    if (!uid) {
      return;
    }
    var action = btn.getAttribute("data-cl-follow-action");
    var url =
      action === "unfollow"
        ? "/profile/" + encodeURIComponent(uid) + "/unfollow"
        : "/profile/" + encodeURIComponent(uid) + "/follow";
    btn.disabled = true;
    postJson(url)
      .then(function (res) {
        if (res.ok && res.body && res.body.ok) {
          setWrapState(wrap, res.body.follow_state || (res.body.following ? "accepted" : "none"), res.body.followers);
        }
      })
      .finally(function () {
        btn.disabled = false;
      });
    ev.preventDefault();
  });
})();
