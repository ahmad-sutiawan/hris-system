(function () {
  "use strict";

  var deck = document.querySelector(".hris-neo-deck");
  if (!deck) {
    return;
  }

  document.documentElement.classList.add("hris-neo-live");

  var tooltip = deck.querySelector("[data-neo-tooltip]");

  function showTooltip(text, x, y) {
    if (!tooltip || !text) {
      return;
    }
    tooltip.textContent = text;
    tooltip.hidden = false;
    tooltip.style.left = x + "px";
    tooltip.style.top = y + "px";
  }

  function hideTooltip() {
    if (tooltip) {
      tooltip.hidden = true;
    }
  }

  function bindTooltip(el, formatter) {
    el.addEventListener("mouseenter", function (event) {
      showTooltip(formatter(el), event.clientX, event.clientY);
    });
    el.addEventListener("mousemove", function (event) {
      showTooltip(formatter(el), event.clientX, event.clientY);
    });
    el.addEventListener("mouseleave", hideTooltip);
    el.addEventListener("focus", function () {
      var rect = el.getBoundingClientRect();
      showTooltip(formatter(el), rect.left + rect.width / 2, rect.top);
    });
    el.addEventListener("blur", hideTooltip);
  }

  /* Gauge arc animation */
  deck.querySelectorAll(".hris-neo-gauge-arc").forEach(function (arc) {
    var target = arc.getAttribute("stroke-dashoffset");
    if (!target) {
      return;
    }
    arc.style.strokeDashoffset = "251.33";
    requestAnimationFrame(function () {
      arc.style.strokeDashoffset = target;
    });
  });

  /* Trend line fade-in */
  deck.querySelectorAll(".hris-neo-trend-line").forEach(function (line, index) {
    line.style.opacity = "0";
    line.style.transition = "opacity 0.7s ease " + index * 0.12 + "s";
    requestAnimationFrame(function () {
      line.style.opacity = "1";
    });
  });

  /* Counter animation for KPI values */
  function animateCount(el) {
    var raw = el.getAttribute("data-neo-count");
    if (!raw) {
      return;
    }
    var target = parseFloat(String(raw).replace(/[^\d.-]/g, "")) || 0;
    var decimals = String(raw).indexOf(".") >= 0 ? 1 : 0;
    var start = 0;
    var duration = 900;
    var startTime = null;

    function frame(time) {
      if (!startTime) {
        startTime = time;
      }
      var progress = Math.min((time - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = start + (target - start) * eased;
      el.textContent = decimals
        ? current.toFixed(decimals)
        : Math.round(current).toLocaleString("id-ID");
      if (progress < 1) {
        requestAnimationFrame(frame);
      } else {
        el.textContent = raw;
      }
    }
    requestAnimationFrame(frame);
  }

  deck.querySelectorAll("[data-neo-count]").forEach(animateCount);

  /* Interactive trend chart */
  var trendWrap = deck.querySelector("[data-neo-trend]");
  if (trendWrap) {
    var callout = trendWrap.querySelector("[data-neo-trend-callout]");
    var zone = trendWrap.querySelector("[data-neo-trend-zone]");
    var svg = trendWrap.querySelector(".hris-neo-trend-svg");
    var hits = trendWrap.querySelectorAll(".hris-neo-trend-hit");

    hits.forEach(function (hit) {
      hit.addEventListener("mouseenter", function () {
        var label = hit.getAttribute("data-label") || "";
        var value = hit.getAttribute("data-value") || "0";
        var cx = parseFloat(hit.getAttribute("cx") || "0");

        deck.querySelectorAll(".hris-neo-trend-dot").forEach(function (dot) {
          dot.classList.toggle("is-hover", dot.getAttribute("cx") === hit.getAttribute("cx"));
        });

        if (callout) {
          callout.querySelector("span").textContent = label;
          callout.querySelector("strong").textContent = value;
          if (svg && svg.viewBox && svg.viewBox.baseVal) {
            var pct = (cx / svg.viewBox.baseVal.width) * 100;
            callout.style.left = pct + "%";
          }
        }
        if (zone) {
          zone.setAttribute("x", String(cx - 10));
        }
      });

      bindTooltip(hit, function (node) {
        return (node.getAttribute("data-label") || "") + " · " + (node.getAttribute("data-value") || "0");
      });
    });
  }

  /* Heat matrix tooltips */
  deck.querySelectorAll("[data-neo-heat]").forEach(function (cell) {
    bindTooltip(cell, function (node) {
      var label = node.getAttribute("data-label") || "";
      var date = node.getAttribute("data-date") || "";
      var value = node.getAttribute("data-value") || "0";
      return label + " " + date + " · " + value + " timesheet";
    });
  });

  /* Radar node highlight */
  deck.querySelectorAll("[data-neo-radar-node]").forEach(function (node) {
    node.addEventListener("mouseenter", function () {
      var label = node.getAttribute("data-label");
      deck.querySelectorAll("[data-neo-radar-leg]").forEach(function (leg) {
        leg.classList.toggle("is-active", leg.getAttribute("data-label") === label);
      });
    });
    node.addEventListener("mouseleave", function () {
      deck.querySelectorAll("[data-neo-radar-leg]").forEach(function (leg) {
        leg.classList.remove("is-active");
      });
    });
    bindTooltip(node, function (n) {
      return (n.getAttribute("data-label") || "") + " · " + (n.getAttribute("data-value") || "0");
    });
  });

  /* KPI & gauge tooltips */
  deck.querySelectorAll("[data-neo-kpi]").forEach(function (kpi) {
    bindTooltip(kpi, function (node) {
      return (node.getAttribute("data-label") || "") + " · " + (node.getAttribute("data-value") || "0");
    });
  });

  deck.querySelectorAll("[data-neo-gauge]").forEach(function (gauge) {
    bindTooltip(gauge, function (node) {
      return (node.getAttribute("data-label") || "") + " · " + (node.getAttribute("data-value") || "0") + " org";
    });
  });

  /* Stagger panel reveal on scroll */
  if ("IntersectionObserver" in window) {
    var panels = deck.querySelectorAll(".hris-neo-panel");
    panels.forEach(function (panel) {
      panel.style.opacity = "0";
      panel.style.transform = "translateY(8px)";
      panel.style.transition = "opacity 0.45s ease, transform 0.45s ease";
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = "1";
            entry.target.style.transform = "translateY(0)";
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -5% 0px" }
    );

    panels.forEach(function (panel, index) {
      panel.style.transitionDelay = index * 0.04 + "s";
      observer.observe(panel);
    });
  }
})();
