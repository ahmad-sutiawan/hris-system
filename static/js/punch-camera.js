(function () {
  var modal = document.getElementById("hris-punch-modal");
  if (!modal) return;

  var form = document.getElementById("hris-punch-form");
  var actionInput = document.getElementById("hris-punch-action");
  var photoInput = document.getElementById("hris-punch-photo");
  var video = document.getElementById("hris-punch-video");
  var preview = document.getElementById("hris-punch-preview");
  var canvas = document.getElementById("hris-punch-canvas");
  var errorBox = document.getElementById("hris-punch-camera-error");
  var captureBtn = document.getElementById("hris-punch-capture");
  var retakeBtn = document.getElementById("hris-punch-retake");
  var submitBtn = document.getElementById("hris-punch-submit");
  var titleEl = document.getElementById("hris-punch-modal-title");
  var subtitleEl = document.getElementById("hris-punch-modal-subtitle");

  if (!form || !actionInput || !photoInput || !video || !canvas || !captureBtn || !submitBtn) {
    return;
  }

  var stream = null;
  var capturedDataUrl = "";

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

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(function (track) {
        track.stop();
      });
      stream = null;
    }
    video.srcObject = null;
  }

  function resetCaptureUi() {
    capturedDataUrl = "";
    photoInput.value = "";
    if (preview) {
      preview.hidden = true;
      preview.removeAttribute("src");
    }
    video.hidden = false;
    captureBtn.hidden = false;
    if (retakeBtn) retakeBtn.hidden = true;
    submitBtn.hidden = true;
    submitBtn.disabled = false;
    submitBtn.textContent = "Konfirmasi & Absen";
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
        var detail = err && err.name === "NotAllowedError"
          ? "Izin kamera ditolak."
          : "Tidak dapat mengakses kamera.";
        showError(detail + " Izinkan permission kamera di browser lalu buka ulang modal.");
      });
  }

  function openModal(action, label) {
    actionInput.value = action;
    if (titleEl) titleEl.textContent = label + " — Verifikasi Selfie";
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
    if (preview) {
      preview.src = capturedDataUrl;
      preview.hidden = false;
    }
    video.hidden = true;
    stopCamera();
    captureBtn.hidden = true;
    if (retakeBtn) retakeBtn.hidden = false;
    submitBtn.hidden = false;
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

  if (retakeBtn) {
    retakeBtn.addEventListener("click", function () {
      startCamera();
    });
  }

  submitBtn.addEventListener("click", function () {
    if (!capturedDataUrl) {
      showError("Ambil foto terlebih dahulu.");
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Memproses…";
    form.submit();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.hidden) {
      closeModal();
    }
  });
})();
