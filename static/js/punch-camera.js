(function () {
  var modal = document.getElementById("hris-punch-modal");
  if (!modal) return;

  var form = document.getElementById("hris-punch-form");
  var actionInput = document.getElementById("hris-punch-action");
  var photoInput = document.getElementById("hris-punch-photo");
  var video = document.getElementById("hris-punch-video");
  var canvas = document.getElementById("hris-punch-canvas");
  var errorBox = document.getElementById("hris-punch-camera-error");
  var captureBtn = document.getElementById("hris-punch-capture");
  var titleEl = document.getElementById("hris-punch-modal-title");
  var subtitleEl = document.getElementById("hris-punch-modal-subtitle");
  var captureView = document.getElementById("hris-punch-capture-view");
  var confirmView = document.getElementById("hris-punch-confirm-view");
  var confirmPhoto = document.getElementById("hris-punch-confirm-photo");
  var confirmTime = document.getElementById("hris-punch-confirm-time");
  var confirmTitle = document.getElementById("hris-punch-confirm-title");
  var confirmSubtitle = document.getElementById("hris-punch-confirm-subtitle");
  var confirmError = document.getElementById("hris-punch-confirm-error");
  var confirmBtn = document.getElementById("hris-punch-confirm-btn");
  var retakeBtn = document.getElementById("hris-punch-confirm-retake");

  if (
    !form ||
    !actionInput ||
    !photoInput ||
    !video ||
    !canvas ||
    !captureBtn ||
    !captureView ||
    !confirmView ||
    !confirmPhoto ||
    !confirmTime ||
    !confirmBtn
  ) {
    return;
  }

  var redirectUrl = form.getAttribute("data-redirect-url") || "/attendance/";
  var punchUrl = form.getAttribute("action") || "/punch/";
  var stream = null;
  var capturedDataUrl = "";
  var currentAction = "";
  var currentActionLabel = "";

  function getCsrfToken() {
    var input = form.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function showError(message) {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearError() {
    if (!errorBox) return;
    errorBox.textContent = "";
    errorBox.hidden = true;
  }

  function showConfirmError(message) {
    if (!confirmError) return;
    confirmError.textContent = message;
    confirmError.hidden = false;
  }

  function clearConfirmError() {
    if (!confirmError) return;
    confirmError.textContent = "";
    confirmError.hidden = true;
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(function (track) {
        track.stop();
      });
      stream = null;
    }
    video.srcObject = null;
  }

  function formatLocalTime(date) {
    try {
      return new Intl.DateTimeFormat("id-ID", {
        weekday: "long",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(date);
    } catch (_err) {
      return date.toLocaleString("id-ID");
    }
  }

  function showCaptureView() {
    captureView.hidden = false;
    confirmView.hidden = true;
    clearConfirmError();
  }

  function showConfirmView(capturedAt) {
    captureView.hidden = true;
    confirmView.hidden = false;
    clearConfirmError();

    confirmPhoto.src = capturedDataUrl;
    if (confirmTitle) {
      confirmTitle.textContent =
        currentAction === "out" ? "Preview Absen Pulang" : "Preview Absen Masuk";
    }
    if (confirmSubtitle) {
      confirmSubtitle.textContent =
        "Periksa hasil selfie dan waktu sebelum melanjutkan ke rekap absensi.";
    }
    confirmTime.textContent = formatLocalTime(capturedAt);
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Konfirmasi";
    if (retakeBtn) retakeBtn.disabled = false;
  }

  function resetCaptureUi() {
    capturedDataUrl = "";
    photoInput.value = "";
    captureBtn.hidden = false;
    captureBtn.disabled = false;
    captureBtn.textContent = "Ambil Foto";
    showCaptureView();
  }

  function closeModal() {
    stopCamera();
    resetCaptureUi();
    clearError();
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("hris-modal-open");
  }

  function startCamera() {
    clearError();
    resetCaptureUi();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError("Browser tidak mendukung kamera. Gunakan Chrome/Firefox/Safari terbaru.");
      return;
    }

    stopCamera();
    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })
      .then(function (mediaStream) {
        stream = mediaStream;
        video.srcObject = stream;
        video.hidden = false;
        var playPromise = video.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(function () {
            showError("Gagal memutar preview kamera. Klik di area video lalu coba lagi.");
          });
        }
      })
      .catch(function (err) {
        var detail =
          err && err.name === "NotAllowedError"
            ? "Izin kamera ditolak."
            : "Tidak dapat mengakses kamera.";
        showError(detail + " Izinkan permission kamera di browser lalu buka ulang modal.");
      });
  }

  function openModal(action, label) {
    currentAction = action;
    currentActionLabel = label || (action === "out" ? "Clock Out" : "Clock In");
    actionInput.value = action;
    if (titleEl) titleEl.textContent = currentActionLabel + " — Verifikasi Selfie";
    if (subtitleEl) {
      subtitleEl.textContent =
        action === "in"
          ? "Ambil foto wajah sebelum clock in."
          : "Ambil foto wajah sebelum clock out.";
    }
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("hris-modal-open");
    startCamera();
  }

  function capturePhoto() {
    if (!video.videoWidth) {
      showError("Kamera belum siap. Tunggu sebentar lalu coba lagi.");
      return;
    }
    clearError();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    capturedDataUrl = canvas.toDataURL("image/jpeg", 0.85);
    photoInput.value = capturedDataUrl;
    stopCamera();
    showConfirmView(new Date());
  }

  function submitPunch() {
    if (!capturedDataUrl) {
      showConfirmError("Ambil foto terlebih dahulu.");
      return;
    }

    clearConfirmError();
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Memproses…";
    if (retakeBtn) retakeBtn.disabled = true;

    var body = new URLSearchParams();
    body.append("punch_action", actionInput.value);
    body.append("photo", capturedDataUrl);
    body.append("csrfmiddlewaretoken", getCsrfToken());

    fetch(punchUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: body.toString(),
      credentials: "same-origin",
    })
      .then(function (response) {
        return response.text().then(function (text) {
          var payload;
          try {
            payload = text ? JSON.parse(text) : {};
          } catch (_err) {
            payload = {
              ok: false,
              detail:
                "Gagal memproses absensi (HTTP " +
                response.status +
                "). " +
                (text ? text.slice(0, 120) : "Respons kosong."),
            };
          }
          return { response: response, payload: payload };
        });
      })
      .then(function (result) {
        var payload = result.payload || {};
        if (!result.response.ok || !payload.ok) {
          throw new Error(payload.detail || "Gagal memproses absensi.");
        }
        if (payload.when_display) {
          confirmTime.textContent = payload.when_display;
        }
        if (confirmTitle) {
          confirmTitle.textContent = "Absen Berhasil";
        }
        if (confirmSubtitle) {
          confirmSubtitle.textContent = payload.message || "Mengalihkan ke rekap absensi…";
        }
        window.setTimeout(function () {
          closeModal();
          window.location.href = payload.redirect_url || redirectUrl;
        }, 350);
      })
      .catch(function (err) {
        showConfirmError(err && err.message ? err.message : "Gagal memproses absensi.");
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Konfirmasi";
        if (retakeBtn) retakeBtn.disabled = false;
      });
  }

  document.querySelectorAll(".hris-punch-trigger").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (btn.disabled) return;
      openModal(btn.getAttribute("data-action"), btn.getAttribute("data-label"));
    });
  });

  modal.querySelectorAll("[data-punch-close]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });

  captureBtn.addEventListener("click", capturePhoto);
  confirmBtn.addEventListener("click", submitPunch);

  if (retakeBtn) {
    retakeBtn.addEventListener("click", function () {
      startCamera();
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.hidden) {
      closeModal();
    }
  });
})();
