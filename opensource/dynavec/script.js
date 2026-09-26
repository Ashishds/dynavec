/* dynavec landing — no external dependencies, no tracking. */
(function () {
  "use strict";

  var REPO = "Ashishds/dynavec";
  var UPSTREAM_REPO = "codeforstartups/dynavec";

  /* ---- theme management (dark / light) ---- */
  var html = document.documentElement;
  var themeBtn = document.getElementById("themeToggle");
  var themeIcon = document.getElementById("themeIcon");
  var themeLabel = document.getElementById("themeLabel");

  function getSavedTheme() {
    var saved = localStorage.getItem("dynavec-theme");
    if (saved) return saved;
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      html.classList.add("dark");
      html.setAttribute("data-theme", "dark");
      if (themeIcon) themeIcon.textContent = "○";
      if (themeLabel) themeLabel.textContent = "Light";
    } else {
      html.classList.remove("dark");
      html.removeAttribute("data-theme");
      if (themeIcon) themeIcon.textContent = "◐";
      if (themeLabel) themeLabel.textContent = "Dark";
    }
  }

  var currentTheme = getSavedTheme();
  applyTheme(currentTheme);

  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      currentTheme = currentTheme === "dark" ? "light" : "dark";
      localStorage.setItem("dynavec-theme", currentTheme);
      applyTheme(currentTheme);
    });
  }

  /* ---- sticky nav border on scroll ---- */
  var nav = document.getElementById("nav");
  function onScroll() {
    if (!nav) return;
    nav.classList.toggle("is-stuck", window.scrollY > 8);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---- copy buttons ---- */
  document.querySelectorAll(".copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy") || "";
      navigator.clipboard.writeText(text).then(function () {
        var old = btn.textContent;
        btn.textContent = "copied";
        btn.classList.add("is-done");
        setTimeout(function () {
          btn.textContent = old;
          btn.classList.remove("is-done");
        }, 1400);
      });
    });
  });

  /* ---- tabs ---- */
  var tabsRoot = document.querySelector("[data-tabs]");
  if (tabsRoot) {
    var tabs = tabsRoot.querySelectorAll(".tab");
    var panels = tabsRoot.querySelectorAll(".tabs__panels > .code");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        tabs.forEach(function (t) {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        panels.forEach(function (p) { p.classList.add("is-hidden"); });
        tab.classList.add("is-active");
        tab.setAttribute("aria-selected", "true");
        var target = document.getElementById(tab.getAttribute("data-tab"));
        if (target) target.classList.remove("is-hidden");
      });
    });
  }

  /* ---- live GitHub star count (fetch from upstream repo for accurate count) ---- */
  function formatStars(n) {
    if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "k";
    return String(n);
  }
  fetch("https://api.github.com/repos/" + UPSTREAM_REPO)
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data || data.stargazers_count == null) return;
      var label = formatStars(data.stargazers_count);
      document.querySelectorAll("[data-stars]").forEach(function (el) {
        el.textContent = label;
      });
    })
    .catch(function () { /* offline / rate-limited */ });

  /* ---- canvas node-network ambient background ---- */
  (function () {
    var canvas = document.getElementById("bg-canvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W, H, nodes, raf;
    var NODE_COUNT = 55, LINK_DIST = 140, SPEED = 0.28;

    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }

    function mkNode() {
      return {
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * SPEED,
        vy: (Math.random() - 0.5) * SPEED,
        r: 1.6 + Math.random() * 1.4
      };
    }

    function init() {
      resize();
      nodes = [];
      for (var i = 0; i < NODE_COUNT; i++) nodes.push(mkNode());
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      var isDark = document.documentElement.classList.contains("dark") ||
                   document.documentElement.getAttribute("data-theme") === "dark";
      var nodeColor = isDark ? "rgba(99,120,255,0.55)" : "rgba(80,100,220,0.30)";
      var lineColor = isDark ? "rgba(99,120,255," : "rgba(80,100,220,";

      for (var i = 0; i < nodes.length; i++) {
        var a = nodes[i];
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > W) a.vx *= -1;
        if (a.y < 0 || a.y > H) a.vy *= -1;

        ctx.beginPath();
        ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
        ctx.fillStyle = nodeColor;
        ctx.fill();

        for (var j = i + 1; j < nodes.length; j++) {
          var b = nodes[j];
          var dx = a.x - b.x, dy = a.y - b.y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < LINK_DIST) {
            var alpha = (1 - dist / LINK_DIST) * (isDark ? 0.22 : 0.12);
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = lineColor + alpha + ")";
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    }

    init();
    draw();
    window.addEventListener("resize", function () {
      cancelAnimationFrame(raf);
      init();
      draw();
    }, { passive: true });
  })();

  /* ---- minimal grayscale Python highlighter ---- */
  var KW = /\b(from|import|for|in|as|def|return|if|else|elif|not|and|or|None|True|False|with|class|lambda|print|is)\b/g;
  function highlight(text) {
    return text.split("\n").map(function (line) {
      var inStr = null, ci = -1;
      for (var i = 0; i < line.length; i++) {
        var ch = line[i];
        if (inStr) { if (ch === inStr) inStr = null; }
        else if (ch === "'" || ch === '"') inStr = ch;
        else if (ch === "#") { ci = i; break; }
      }
      var code = line, comment = "";
      if (ci >= 0) { code = line.slice(0, ci); comment = line.slice(ci); }

      var strs = [];
      code = code.replace(/(['"])(?:\\.|(?!\1).)*\1/g, function (m) {
        strs.push(m); return " " + (strs.length - 1) + " ";
      });
      code = code.replace(KW, '<span class="c-kw">$1</span>');
      code = code.replace(/ (\d+) /g, function (m, idx) {
        return '<span class="c-str">' + strs[idx] + "</span>";
      });
      if (comment) comment = '<span class="c-comment">' + comment + "</span>";
      return code + comment;
    }).join("\n");
  }

  document.querySelectorAll(".tabs__panels .code code, .code--sm code").forEach(function (el) {
    if (el.textContent.indexOf("<") === -1) {
      el.innerHTML = highlight(el.textContent);
    }
  });

  /* ---- interactive cost calculator ---- */
  var VEC_STEPS = [
    { label: "100K", n: 100000 },
    { label: "500K", n: 500000 },
    { label: "1M", n: 1000000 },
    { label: "5M", n: 5000000 },
    { label: "10M", n: 10000000 },
    { label: "50M", n: 50000000 },
    { label: "100M", n: 100000000 },
    { label: "500M", n: 500000000 },
    { label: "1B", n: 1000000000 }
  ];

  var Q_STEPS = [
    { label: "100K / mo", n: 100000 },
    { label: "500K / mo", n: 500000 },
    { label: "1M / mo", n: 1000000 },
    { label: "5M / mo", n: 5000000 },
    { label: "10M / mo", n: 10000000 }
  ];

  var vecSlider = document.getElementById("calcVectors");
  var qSlider = document.getElementById("calcQueries");
  var vecDisplay = document.getElementById("calcVecDisplay");
  var qDisplay = document.getElementById("calcQDisplay");
  var savingsAmount = document.getElementById("calcSavingsAmount");

  if (vecSlider && qSlider) {
    function updateCalc() {
      var vIdx = parseInt(vecSlider.value, 10);
      var qIdx = parseInt(qSlider.value, 10);
      var vStep = VEC_STEPS[vIdx] || VEC_STEPS[2];
      var qStep = Q_STEPS[qIdx] || Q_STEPS[2];

      if (vecDisplay) vecDisplay.textContent = vStep.label + " vectors";
      if (qDisplay) qDisplay.textContent = qStep.label;

      var v = vStep.n;
      var q = qStep.n;

      // Pricing model (1536-dim vectors):
      // S3 Vectors: ~$0.023/GB/mo storage (~6KB/vec) + $0.0004/1K queries
      // DynamoDB: on-demand reads ($0.25/1M reads)
      var dynaCost = Math.max(3, Math.round((v * 1536 * 4 / (1024 * 1024 * 1024) * 0.023) + (q / 1000000 * 1.5)));

      // Pinecone standard/serverless: storage ($0.33/GB) + read units ($8.25/1M)
      var pineCost = Math.max(10, Math.round((v * 1536 * 4 / (1024 * 1024 * 1024) * 0.33) + (q / 1000000 * 8.25)));

      // Dedicated / cluster DBs (RAM heavy baseline)
      var qdrantCost = Math.max(160, Math.round(v <= 1000000 ? 160 : (v / 1000000) * 85));
      var opensearchCost = Math.max(701, Math.round(v <= 1000000 ? 701 : (v / 1000000) * 83));
      var weaviateCost = Math.max(175, Math.round(v <= 1000000 ? 175 : (v / 1000000) * 93));

      var maxCost = Math.max(dynaCost, pineCost, qdrantCost, opensearchCost, weaviateCost);

      function setRow(prefix, cost) {
        var costEl = document.getElementById(prefix + "Cost");
        var barEl = document.getElementById(prefix + "Bar");
        if (costEl) costEl.textContent = "$" + cost.toLocaleString();
        if (barEl) {
          var pct = Math.max(4, Math.round((cost / maxCost) * 100));
          barEl.style.width = pct + "%";
        }
      }

      setRow("dyna", dynaCost);
      setRow("pine", pineCost);
      setRow("qdrant", qdrantCost);
      setRow("open", opensearchCost);
      setRow("weav", weaviateCost);

      if (savingsAmount) {
        var diff = pineCost - dynaCost;
        var annual = diff * 12;
        savingsAmount.textContent = "$" + annual.toLocaleString() + " / year";
      }
    }

    vecSlider.addEventListener("input", updateCalc);
    qSlider.addEventListener("input", updateCalc);
    updateCalc();
  }
})();
