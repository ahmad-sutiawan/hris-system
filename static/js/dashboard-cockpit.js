(function () {
  "use strict";

  var root = document.querySelector("[data-hx-cockpit]");
  if (!root) {
    return;
  }

  document.documentElement.classList.add("hx-live");

  var tip = root.querySelector("[data-hx-tip]");

  function showTip(text, x, y) {
    if (!tip || !text) return;
    tip.textContent = text;
    tip.hidden = false;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function hideTip() {
    if (tip) tip.hidden = true;
  }

  function bindTip(el, fmt) {
    if (!el) return;
    el.addEventListener("mouseenter", function (e) { showTip(fmt(el), e.clientX, e.clientY); });
    el.addEventListener("mousemove", function (e) { showTip(fmt(el), e.clientX, e.clientY); });
    el.addEventListener("mouseleave", hideTip);
    el.addEventListener("focus", function () {
      var r = el.getBoundingClientRect();
      showTip(fmt(el), r.left + r.width / 2, r.top);
    });
    el.addEventListener("blur", hideTip);
  }

  /* Live clock */
  var clockEl = root.querySelector("[data-hx-clock]");
  function tickClock() {
    if (!clockEl) return;
    var now = new Date();
    var h = String(now.getHours()).padStart(2, "0");
    var m = String(now.getMinutes()).padStart(2, "0");
    var s = String(now.getSeconds()).padStart(2, "0");
    clockEl.textContent = h + ":" + m + ":" + s;
    clockEl.setAttribute("datetime", now.toISOString());
  }
  tickClock();
  setInterval(tickClock, 1000);

  /* Count-up animation */
  function countUp(el) {
    var raw = el.getAttribute("data-hx-count");
    if (!raw) return;
    var target = parseFloat(String(raw).replace(/[^\d.-]/g, "")) || 0;
    var decimals = String(raw).indexOf(".") >= 0 ? 1 : 0;
    var dur = 850;
    var t0 = null;

    function frame(t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var val = target * eased;
      el.textContent = decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString("id-ID");
      if (p < 1) requestAnimationFrame(frame);
      else el.textContent = raw;
    }
    requestAnimationFrame(frame);
  }

  root.querySelectorAll("[data-hx-count]").forEach(countUp);

  /* Gauge arcs */
  root.querySelectorAll(".hx-gauge-arc").forEach(function (arc) {
    var target = arc.getAttribute("stroke-dashoffset");
    if (!target) return;
    arc.style.strokeDashoffset = "251.33";
    requestAnimationFrame(function () { arc.style.strokeDashoffset = target; });
  });

  /* Trend lines fade */
  root.querySelectorAll(".hx-trend-line").forEach(function (line, i) {
    line.style.opacity = "0";
    line.style.transition = "opacity 0.65s ease " + i * 0.1 + "s";
    requestAnimationFrame(function () { line.style.opacity = "1"; });
  });

  /* Trend interactivity */
  var trend = root.querySelector("[data-hx-trend]");
  if (trend) {
    var tipBox = trend.querySelector("[data-hx-trend-tip]");
    var zone = trend.querySelector("[data-hx-trend-zone]");
    var svg = trend.querySelector(".hx-trend-svg");
    var vbW = svg && svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal.width : 300;

    trend.querySelectorAll("[data-hx-trend-pt]").forEach(function (hit) {
      hit.addEventListener("mouseenter", function () {
        var label = hit.getAttribute("data-label") || "";
        var value = hit.getAttribute("data-value") || "0";
        var cx = parseFloat(hit.getAttribute("data-x") || hit.getAttribute("cx") || "0");

        root.querySelectorAll(".hx-trend-dot").forEach(function (dot) {
          dot.classList.toggle("is-hover", dot.getAttribute("cx") === hit.getAttribute("cx"));
        });

        if (tipBox) {
          tipBox.querySelector("span").textContent = label;
          tipBox.querySelector("strong").textContent = value;
          tipBox.style.left = (cx / vbW * 100) + "%";
        }
        if (zone) zone.setAttribute("x", String(cx - 10));
      });

      bindTip(hit, function (n) {
        return (n.getAttribute("data-label") || "") + " · " + (n.getAttribute("data-value") || "0") + " timesheet";
      });
    });
  }

  /* Ring legend hover */
  root.querySelectorAll("[data-hx-seg]").forEach(function (seg) {
    seg.addEventListener("mouseenter", function () {
      root.querySelectorAll("[data-hx-seg]").forEach(function (s) { s.classList.remove("is-active"); });
      seg.classList.add("is-active");
    });
    seg.addEventListener("mouseleave", function () { seg.classList.remove("is-active"); });
    bindTip(seg, function (n) {
      return (n.getAttribute("data-label") || "") + " · " + (n.getAttribute("data-value") || "0") + " org";
    });
  });

  /* KPI, gauge, heat, bars, flow, radar */
  root.querySelectorAll("[data-hx-kpi]").forEach(function (el) {
    bindTip(el, function (n) { return n.getAttribute("data-label") + " · " + n.getAttribute("data-value"); });
  });
  root.querySelectorAll("[data-hx-gauge]").forEach(function (el) {
    bindTip(el, function (n) { return n.getAttribute("data-label") + " · " + n.getAttribute("data-value") + " org"; });
  });
  root.querySelectorAll("[data-hx-heat]").forEach(function (el) {
    bindTip(el, function (n) {
      return n.getAttribute("data-label") + " " + n.getAttribute("data-date") + " · " + n.getAttribute("data-value");
    });
  });
  root.querySelectorAll("[data-hx-bar]").forEach(function (el) {
    bindTip(el, function (n) { return n.getAttribute("data-label") + " · " + n.getAttribute("data-value"); });
  });
  root.querySelectorAll("[data-hx-flow]").forEach(function (el) {
    bindTip(el, function (n) { return n.getAttribute("data-label") + " · " + n.getAttribute("data-value"); });
  });
  root.querySelectorAll("[data-hx-radar]").forEach(function (node) {
    node.addEventListener("mouseenter", function () {
      var label = node.getAttribute("data-label");
      root.querySelectorAll("[data-hx-radar-leg]").forEach(function (leg) {
        leg.classList.toggle("is-active", leg.getAttribute("data-hx-radar-leg") === label);
      });
    });
    node.addEventListener("mouseleave", function () {
      root.querySelectorAll("[data-hx-radar-leg]").forEach(function (leg) { leg.classList.remove("is-active"); });
    });
    bindTip(node, function (n) { return n.getAttribute("data-label") + " · " + n.getAttribute("data-value"); });
  });

  /* Stagger panel entrance */
  if ("IntersectionObserver" in window) {
    var panels = root.querySelectorAll(".hx-panel");
    panels.forEach(function (p) {
      p.style.opacity = "0";
      p.style.transform = "translateY(10px)";
      p.style.transition = "opacity 0.5s ease, transform 0.5s ease";
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -4% 0px" });
    panels.forEach(function (p, i) {
      p.style.transitionDelay = i * 0.035 + "s";
      io.observe(p);
    });
  }

  /* Subtle parallax on hero ring */
  var ring = root.querySelector(".hx-ring-visual");
  if (ring && window.matchMedia("(pointer: fine)").matches) {
    root.addEventListener("mousemove", function (e) {
      var rect = root.getBoundingClientRect();
      var x = (e.clientX - rect.left) / rect.width - 0.5;
      var y = (e.clientY - rect.top) / rect.height - 0.5;
      ring.style.transform = "perspective(600px) rotateY(" + x * 6 + "deg) rotateX(" + -y * 6 + "deg)";
    });
    root.addEventListener("mouseleave", function () { ring.style.transform = ""; });
  }
})();
