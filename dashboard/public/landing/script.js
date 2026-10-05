/* ================================================
   dynavec landing page — script.js
   1. Animated dot-node network background
   2. Benchmark charts (Chart.js)
   3. Cost calculator
   ================================================ */

/* ---- 1. Background node network canvas ---- */
(function () {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Check prefers-reduced-motion for accessibility & mobile battery optimization
  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) return;

  const isMobile = window.innerWidth < 768;
  const NODES = isMobile ? 32 : 70;
  const MAX_DIST = 160;
  const NODE_RADIUS = 2.2;
  const SPEED = 0.35;
  const CORAL = "#e05a3a";
  const DOT_COLOR = "rgba(180,180,200,0.55)";
  const LINE_COLOR = "rgba(180,180,200,";

  let W, H, nodes, dpr;
  let isTabActive = true;

  document.addEventListener("visibilitychange", () => {
    isTabActive = !document.hidden;
    if (isTabActive) requestAnimationFrame(tick);
  });

  function resize() {
    dpr = window.devicePixelRatio || 1;
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function makeNode() {
    const angle = Math.random() * Math.PI * 2;
    const speed = SPEED * (0.4 + Math.random() * 0.6);
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      accent: Math.random() < 0.08,
    };
  }

  function init() {
    resize();
    nodes = Array.from({ length: NODES }, makeNode);
  }

  function tick() {
    if (!isTabActive) return;
    ctx.clearRect(0, 0, W, H);

    nodes.forEach((n) => {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });

    // draw edges
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MAX_DIST) {
          const alpha = (1 - dist / MAX_DIST) * 0.45;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = LINE_COLOR + alpha + ")";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }

    // draw nodes
    nodes.forEach((n) => {
      ctx.beginPath();
      ctx.arc(
        n.x,
        n.y,
        n.accent ? NODE_RADIUS * 1.6 : NODE_RADIUS,
        0,
        Math.PI * 2
      );
      ctx.fillStyle = n.accent ? CORAL : DOT_COLOR;
      ctx.fill();
    });

    requestAnimationFrame(tick);
  }

  window.addEventListener("resize", () => {
    resize(); // re-applies dpr scale transform
    nodes.forEach((n) => {
      n.x = Math.min(n.x, W);
      n.y = Math.min(n.y, H);
    });
  });

  init();
  tick();
})();

/* ---- 2. Benchmark charts (Dark & Light theme aware) ---- */
(function () {
  const chartInstances = {};

  function getChartPalette(isDark) {
    return {
      coral: "#e05a3a",
      coralBg: "#e05a3a22",
      coralFill: "#e05a3acc",
      gray1: isDark ? "#8b949e" : "#9ca3af",
      gray2: isDark ? "#6e7681" : "#c4c9d4",
      gray3: isDark ? "#484f58" : "#d1d5db",
      gray4: isDark ? "#30363d" : "#e5e7eb",
      textColor: isDark ? "#c9d1d9" : "#6a6a6a",
      gridColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)",
      borderColor: isDark ? "#14151a" : "#ffffff",
    };
  }

  function applyChartsTheme(theme) {
    const isDark = theme === "dark";
    const p = getChartPalette(isDark);

    if (typeof Chart !== "undefined") {
      Chart.defaults.color = p.textColor;
    }

    if (chartInstances.matrix) {
      const c = chartInstances.matrix;
      c.options.scales.x.grid.color = p.gridColor;
      c.options.scales.y.grid.color = p.gridColor;
      c.options.scales.x.ticks.color = p.textColor;
      c.options.scales.y.ticks.color = p.textColor;
      c.options.scales.x.title.color = p.textColor;
      c.options.scales.y.title.color = p.textColor;
      c.options.plugins.title.color = p.textColor;
      c.options.plugins.legend.labels.color = p.textColor;
      c.data.datasets[1].backgroundColor = p.gray1;
      c.data.datasets[2].backgroundColor = p.gray2;
      c.data.datasets[3].backgroundColor = p.gray3;
      c.data.datasets[4].backgroundColor = p.gray4;
      c.update();
    }
    if (chartInstances.scale) {
      const c = chartInstances.scale;
      c.options.scales.x.grid.color = p.gridColor;
      c.options.scales.y.grid.color = p.gridColor;
      c.options.scales.x.ticks.color = p.textColor;
      c.options.scales.y.ticks.color = p.textColor;
      c.options.plugins.title.color = p.textColor;
      c.options.plugins.legend.labels.color = p.textColor;
      c.data.datasets[1].borderColor = p.gray1;
      c.data.datasets[2].borderColor = p.gray2;
      c.update();
    }
    if (chartInstances.storage) {
      const c = chartInstances.storage;
      c.options.scales.x.grid.color = p.gridColor;
      c.options.scales.y.grid.color = p.gridColor;
      c.options.scales.x.ticks.color = p.textColor;
      c.options.scales.y.ticks.color = p.textColor;
      c.options.scales.y.title.color = p.textColor;
      c.options.plugins.title.color = p.textColor;
      c.update();
    }
    if (chartInstances.quality) {
      const c = chartInstances.quality;
      c.options.plugins.title.color = p.textColor;
      c.options.plugins.legend.labels.color = p.textColor;
      c.data.datasets[0].borderColor = p.borderColor;
      c.data.datasets[0].backgroundColor = [p.coral, p.gray1, p.gray2, p.gray3, p.gray4];
      c.update();
    }
  }

  window.updateDynavecChartsTheme = applyChartsTheme;

  window.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") return;

    const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
    const isDark = currentTheme === "dark";
    const p = getChartPalette(isDark);

    const font = { family: "'Inter', sans-serif", size: 12 };
    Chart.defaults.font = font;
    Chart.defaults.color = p.textColor;

    // --- bench-matrix: grouped bar — cost by scale at 1536-dim ---
    const matrixCtx = document.getElementById("bench-matrix");
    if (matrixCtx) {
      const scales = ["100K", "1M", "10M", "100M", "1B"];
      chartInstances.matrix = new Chart(matrixCtx, {
        type: "bar",
        data: {
          labels: scales,
          datasets: [
            {
              label: "dynavec",
              data: [3, 3, 8, 50, 469],
              backgroundColor: p.coral,
            },
            {
              label: "Pinecone",
              data: [9, 10, 27, 197, 1897],
              backgroundColor: p.gray1,
            },
            {
              label: "Qdrant",
              data: [160, 160, 960, 8640, 85920],
              backgroundColor: p.gray2,
            },
            {
              label: "Weaviate",
              data: [175, 175, 1050, 9450, 93975],
              backgroundColor: p.gray3,
            },
            {
              label: "OpenSearch",
              data: [701, 701, 877, 8423, 83708],
              backgroundColor: p.gray4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "top",
              labels: { color: p.textColor },
            },
            title: {
              display: true,
              text: "Monthly cost ($/mo) — 1536-dim, 1M queries/mo",
              font: { size: 13 },
              color: p.textColor,
            },
            tooltip: {
              callbacks: {
                label: (ctx) =>
                  ` ${ctx.dataset.label}: $${ctx.parsed.y.toLocaleString()}`,
              },
            },
          },
          scales: {
            y: {
              type: "logarithmic",
              title: { display: true, text: "$/month (log scale)", color: p.textColor },
              ticks: { callback: (v) => "$" + v.toLocaleString(), color: p.textColor },
              grid: { color: p.gridColor },
            },
            x: {
              title: { display: true, text: "Vector count", color: p.textColor },
              ticks: { color: p.textColor },
              grid: { color: p.gridColor },
            },
          },
        },
      });
    }

    // --- bench-scale: line — cost by scale at 768-dim ---
    const scaleCtx = document.getElementById("bench-scale");
    if (scaleCtx) {
      const pts = ["100K", "1M", "10M", "100M", "1B"];
      chartInstances.scale = new Chart(scaleCtx, {
        type: "line",
        data: {
          labels: pts,
          datasets: [
            {
              label: "dynavec",
              data: [2, 2, 5, 32, 295],
              borderColor: p.coral,
              backgroundColor: p.coralBg,
              tension: 0.35,
              fill: true,
            },
            {
              label: "Pinecone",
              data: [9, 10, 27, 197, 1897],
              borderColor: p.gray1,
              backgroundColor: "transparent",
              tension: 0.35,
            },
            {
              label: "Qdrant",
              data: [80, 80, 480, 4320, 42960],
              borderColor: p.gray2,
              backgroundColor: "transparent",
              tension: 0.35,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "top",
              labels: { color: p.textColor },
            },
            title: {
              display: true,
              text: "Cost by scale (768-d)",
              font: { size: 12 },
              color: p.textColor,
            },
          },
          scales: {
            y: {
              type: "logarithmic",
              ticks: { callback: (v) => "$" + v.toLocaleString(), color: p.textColor },
              grid: { color: p.gridColor },
            },
            x: {
              ticks: { color: p.textColor },
              grid: { color: p.gridColor },
            },
          },
        },
      });
    }

    // --- bench-storage: bar — raw storage footprint ---
    const storageCtx = document.getElementById("bench-storage");
    if (storageCtx) {
      chartInstances.storage = new Chart(storageCtx, {
        type: "bar",
        data: {
          labels: ["100K", "1M", "10M", "100M", "1B"],
          datasets: [
            {
              label: "Storage (GiB)",
              data: [0.57, 5.7, 57, 573, 5730],
              backgroundColor: p.coralFill,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            title: {
              display: true,
              text: "Float32 storage footprint (1536-d)",
              font: { size: 12 },
              color: p.textColor,
            },
          },
          scales: {
            y: {
              type: "logarithmic",
              title: { display: true, text: "GiB (log)", color: p.textColor },
              ticks: { callback: (v) => v + " GiB", color: p.textColor },
              grid: { color: p.gridColor },
            },
            x: {
              ticks: { color: p.textColor },
              grid: { color: p.gridColor },
            },
          },
        },
      });
    }

    // --- quality-chart: doughnut — recall/latency score ---
    const qualityCtx = document.getElementById("quality-chart");
    if (qualityCtx) {
      chartInstances.quality = new Chart(qualityCtx, {
        type: "doughnut",
        data: {
          labels: ["dynavec", "Pinecone", "Qdrant", "Weaviate", "OpenSearch"],
          datasets: [
            {
              data: [92, 88, 85, 82, 74],
              backgroundColor: [p.coral, p.gray1, p.gray2, p.gray3, p.gray4],
              borderWidth: 2,
              borderColor: p.borderColor,
            },
          ],
        },
        options: {
          responsive: true,
          cutout: "62%",
          plugins: {
            legend: {
              position: "bottom",
              labels: { boxWidth: 12, color: p.textColor },
            },
            title: {
              display: true,
              text: "Recall ÷ Latency score",
              font: { size: 12 },
              color: p.textColor,
            },
            tooltip: {
              callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}` },
            },
          },
        },
      });
    }
  });
})();

/* ---- 3. Cost calculator v2 ---- */
(function () {
  function init() {
    const slVectors = document.getElementById("sl-vectors");
    const slDim = document.getElementById("sl-dim");
    const slQpm = document.getElementById("sl-qpm");
    const slWpm = document.getElementById("sl-wpm");
    if (!slVectors) return;

    const DIM_OPTS = [384, 768, 1536, 3072];

    function getVectors() {
      return Math.round(Math.pow(10, parseFloat(slVectors.value)));
    }
    function getDim() {
      return DIM_OPTS[parseInt(slDim.value)];
    }
    function getQpm() {
      return Math.round(Math.pow(10, parseFloat(slQpm.value)));
    }
    function getWpm() {
      return Math.round(Math.pow(10, parseFloat(slWpm.value)));
    }

    function fmtN(n) {
      if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + " B";
      if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + " M";
      if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + " K";
      return String(n);
    }
    function fmtUSD(n) {
      if (n >= 1000)
        return "$" + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      return "$" + n.toFixed(2);
    }

    const PRESETS = {
      starter: { vectors: 5, dim: 1, qpm: 5, wpm: 4 },
      growth: { vectors: 6, dim: 2, qpm: 6.7, wpm: 5.7 },
      scale: { vectors: 7, dim: 2, qpm: 7.7, wpm: 6.7 },
    };

    document.querySelectorAll(".calc2__preset").forEach((btn) => {
      btn.addEventListener("click", () => {
        document
          .querySelectorAll(".calc2__preset")
          .forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        const p = PRESETS[btn.dataset.preset];
        slVectors.value = p.vectors;
        slDim.value = p.dim;
        slQpm.value = p.qpm;
        slWpm.value = p.wpm;
        compute();
      });
    });

    function setBar(id, amtId, cost, max) {
      const fill = document.getElementById(id);
      const amt = document.getElementById(amtId);
      if (fill)
        fill.style.width = (max > 0 ? Math.min(cost / max, 1) * 100 : 0) + "%";
      if (amt) amt.textContent = fmtUSD(cost);
    }

    function compute() {
      const vectors = getVectors();
      const dim = getDim();
      const qpm = getQpm();
      const wpm = getWpm();

      const lblV = document.getElementById("lbl-vectors");
      const lblD = document.getElementById("lbl-dim");
      const lblQ = document.getElementById("lbl-qpm");
      const lblW = document.getElementById("lbl-wpm");
      if (lblV) lblV.textContent = fmtN(vectors);
      if (lblD) lblD.textContent = dim;
      if (lblQ) lblQ.textContent = fmtN(qpm);
      if (lblW) lblW.textContent = fmtN(wpm);

      const storedGB = (vectors * dim * 4) / 1e9;
      const storageCost = storedGB * 0.04;
      const readCost = (qpm / 1e6) * 0.04;
      const dynRead = qpm * 0.00000013;
      const dynWrite = wpm * 0.00000065;
      const dvTotal = storageCost + readCost + dynRead + dynWrite;

      const pnTotal =
        storedGB * 0.096 + (qpm / 1e6) * 0.1 + (wpm / 1e6) * 0.5 + 20;
      const saving =
        pnTotal > 0 ? Math.round((1 - dvTotal / pnTotal) * 100) : 0;

      const dvEl = document.getElementById("calc-dv-price");
      const pnEl = document.getElementById("calc-pn-price");
      const svEl = document.getElementById("calc-savings");
      if (dvEl) dvEl.textContent = fmtUSD(dvTotal) + " /mo";
      if (pnEl) pnEl.textContent = "~" + fmtUSD(pnTotal) + " /mo";
      if (svEl)
        svEl.textContent =
          saving > 0
            ? `You save ~${saving}% vs Pinecone`
            : "Similar cost to Pinecone";

      const maxCost = Math.max(storageCost, readCost, dynRead, dynWrite, 0.01);
      setBar("bar-storage", "amt-storage", storageCost, maxCost);
      setBar("bar-reads", "amt-reads", readCost, maxCost);
      setBar("bar-ddb-r", "amt-ddb-r", dynRead, maxCost);
      setBar("bar-ddb-w", "amt-ddb-w", dynWrite, maxCost);
    }

    [slVectors, slDim, slQpm, slWpm].forEach((el) =>
      el.addEventListener("input", compute)
    );
    compute();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

/* ---- 4. Sticky nav ---- */
(function () {
  const nav = document.getElementById("nav");
  if (!nav) return;
  const onScroll = () => nav.classList.toggle("is-stuck", window.scrollY > 10);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
})();

/* ---- 5. Scroll reveal (IntersectionObserver) ---- */
(function () {
  const targets = document.querySelectorAll(
    "[data-reveal], .section__title, .hero__stats"
  );
  if (!targets.length || !("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("is-visible"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-visible");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  targets.forEach((el) => io.observe(el));
})();

/* ---- 6. Tab switching ---- */
(function () {
  const tabsEl = document.querySelector("[data-tabs]");
  if (!tabsEl) return;
  const tabs = tabsEl.querySelectorAll(".tab");
  const panels = tabsEl.querySelectorAll('[role="tabpanel"]');

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        t.classList.remove("is-active");
        t.setAttribute("aria-selected", "false");
      });
      panels.forEach((p) => p.classList.add("is-hidden"));
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.remove("is-hidden");
    });
  });
})();

/* ---- 7. Copy buttons ---- */
(function () {
  document.querySelectorAll(".copy[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.copy).then(() => {
        btn.textContent = "✓ Copied";
        btn.classList.add("is-done");
        setTimeout(() => {
          btn.textContent = "copy";
          btn.classList.remove("is-done");
        }, 1800);
      });
    });
  });
})();

/* ---- 8. YouTube facade ---- */
(function () {
  const facade = document.getElementById("yt-facade");
  if (!facade) return;
  facade.addEventListener("click", (e) => {
    e.preventDefault();
    const iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube.com/embed/UJ9MBALD380?autoplay=1&rel=0";
    iframe.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.setAttribute("allowfullscreen", "");
    iframe.style.cssText =
      "position:absolute;inset:0;width:100%;height:100%;border:0;";
    // Clear thumbnail/play button and drop in the iframe inline
    facade.innerHTML = "";
    facade.style.cursor = "default";
    facade.appendChild(iframe);
  });
  facade.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      facade.click();
    }
  });
})();

/* ---- 9. Contributors grid ---- */
(function () {
  const coreEl = document.getElementById("contrib-core");
  const allEl = document.getElementById("contrib-all");
  if (!coreEl || !allEl) return;

  const CORE_NAMES = [
    "Abhishek Gupta",
    "Sanket Tikhande",
    "Vardhman Gupta",
    "Shivam Gupta",
    "Isha Zaka",
  ];

  // To add a contributor: append their name here.
  // Drop a photo as images/contributors/<name-lowercase-hyphenated>.png — auto-detected.
  const ALL_NAMES = [
    "Abhishek Gupta",
    "Sanket Tikhande",
    "Vardhman Gupta",
    "Shivam Gupta",
    "Isha Zaka",
    "Uzma Khan",
    "Ashish Kumar",
    "Madhav Sharma",
    "Tanmay Kumar",
    "Henil Bhavsar",
    "Mohammad Arshad Ali",
    "vaishnavk09",
    "be-student",
    "redcode333",
    "R3108",
    "AyushhVatsal",
    "ramashishmaurya",
    "Lawliet2004",
    "wang1408",
    "theman6660",
    "osamashabih6960",
  ];

  const KNOWN_PHOTOS = new Set([
    "abhishek-gupta",
    "sanket-tikhande",
    "vardhman-gupta",
    "shivam-gupta",
    "isha-zaka",
    "uzma-khan",
    "ashish-kumar",
    "madhav-sharma",
    "tanmay-kumar",
    "henil-bhavsar",
    "mohammad-arshad-ali",
  ]);

  function nameToPhotoPath(name) {
    const slug = name.trim().toLowerCase().replace(/\s+/g, "-");
    return KNOWN_PHOTOS.has(slug)
      ? "images/contributors/" + slug + ".png"
      : null;
  }

  const PALETTE = [
    "#e8623b",
    "#4f8ef7",
    "#2db87c",
    "#9b67e0",
    "#e8a43b",
    "#e84f7a",
    "#3bbde8",
  ];

  function initialsAvatar(name, idx) {
    const words = name.trim().split(/[\s_\-]+/);
    const initials =
      words.length >= 2
        ? (words[0][0] + words[1][0]).toUpperCase()
        : name.slice(0, 2).toUpperCase();
    const color = PALETTE[idx % PALETTE.length];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
      <rect width="200" height="200" fill="${color}18"/>
      <text x="100" y="115" font-family="Inter,sans-serif" font-size="72" font-weight="700"
            fill="${color}" text-anchor="middle">${initials}</text>
    </svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function makeCard(name, idx, isCore) {
    const photo = nameToPhotoPath(name);

    const card = document.createElement("div");
    card.className = "cg-card" + (isCore ? " cg-card--core" : "");

    const photoWrap = document.createElement("div");
    photoWrap.className = "cg-card__photo";

    const img = document.createElement("img");
    img.src = photo || initialsAvatar(name, idx);
    img.alt = name;
    img.loading = "lazy";
    if (photo) {
      img.onerror = () => {
        img.onerror = null;
        img.src = initialsAvatar(name, idx);
      };
    }

    photoWrap.appendChild(img);

    const info = document.createElement("div");
    info.className = "cg-card__info";

    const nameEl = document.createElement("div");
    nameEl.className = "cg-card__name";
    nameEl.textContent = name;

    info.appendChild(nameEl);

    card.appendChild(photoWrap);
    card.appendChild(info);
    return card;
  }

  const coreSet = new Set(CORE_NAMES);
  CORE_NAMES.forEach((name, i) => coreEl.appendChild(makeCard(name, i, true)));

  const restNames = ALL_NAMES.filter((n) => !coreSet.has(n));
  const INITIAL_SHOW = 5;

  // Render first 5 immediately
  restNames
    .slice(0, INITIAL_SHOW)
    .forEach((name, i) => allEl.appendChild(makeCard(name, i, false)));

  // If there are more, add a "Show more" button
  if (restNames.length > INITIAL_SHOW) {
    const showMoreBtn = document.createElement("button");
    showMoreBtn.className = "contrib-show-more";
    showMoreBtn.textContent = `Show ${
      restNames.length - INITIAL_SHOW
    } more contributors`;
    allEl.after(showMoreBtn);

    showMoreBtn.addEventListener("click", () => {
      restNames
        .slice(INITIAL_SHOW)
        .forEach((name, i) =>
          allEl.appendChild(makeCard(name, INITIAL_SHOW + i, false))
        );
      showMoreBtn.remove();
    });
  }
})();

/* ---- 10. GitHub star count ---- */
(function () {
  fetch("https://api.github.com/repos/codeforstartups/dynavec")
    .then((r) => r.json())
    .then((data) => {
      const count = data.stargazers_count;
      if (!count) return;
      const fmt =
        count >= 1000
          ? (count / 1000).toFixed(1).replace(/\.0$/, "") + "k"
          : String(count);
      document.querySelectorAll("[data-stars]").forEach((el) => {
        el.textContent = fmt;
      });
    })
    .catch(() => {});
})();

/* ---- 11. Enterprise Console Navigation ---- */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('a[href*="tab="]').forEach(function (link) {
      link.addEventListener("click", function (e) {
        if (window.parent && window.parent !== window) {
          e.preventDefault();
          var href = link.getAttribute("href") || "";
          var tab = "playground";
          if (href.indexOf("tab=") !== -1) {
            tab = href.split("tab=")[1].split("&")[0];
          }
          window.parent.postMessage({ type: "NAVIGATE_DASHBOARD", tab: tab }, "*");
        }
      });
    });
  });
})();

/* ---- 12. Mobile navigation toggle & drawer ---- */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("navToggle");
    const menu = document.getElementById("navMobileMenu");
    if (!toggle || !menu) return;

    function openMenu() {
      toggle.classList.add("is-active");
      toggle.setAttribute("aria-expanded", "true");
      menu.classList.add("is-open");
      menu.setAttribute("aria-hidden", "false");
    }

    function closeMenu() {
      toggle.classList.remove("is-active");
      toggle.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
      menu.setAttribute("aria-hidden", "true");
    }

    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      if (menu.classList.contains("is-open")) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    // Close when clicking any link inside the mobile menu
    menu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        closeMenu();
      });
    });

    // Close when clicking outside
    document.addEventListener("click", function (e) {
      if (menu.classList.contains("is-open") && !menu.contains(e.target) && !toggle.contains(e.target)) {
        closeMenu();
      }
    });

    // Close on escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.classList.contains("is-open")) {
        closeMenu();
      }
    });

    // Close when resizing window to desktop
    window.addEventListener("resize", function () {
      if (window.innerWidth > 860 && menu.classList.contains("is-open")) {
        closeMenu();
      }
    });
  });
})();

/* ---- 13. Light / Dark Theme Toggle (Dark by default) ---- */
(function () {
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");

    var label = document.getElementById("themeLabel");
    if (label) label.textContent = theme === "dark" ? "Light" : "Dark";

    var mobileLabel = document.getElementById("mobileThemeLabel");
    if (mobileLabel) mobileLabel.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";

    var btn = document.getElementById("themeToggle");
    if (btn) {
      var nextTheme = theme === "dark" ? "light" : "dark";
      btn.setAttribute("aria-label", "Switch to " + nextTheme + " mode");
      btn.setAttribute("title", "Switch to " + nextTheme + " mode");
    }

    if (typeof window.updateDynavecChartsTheme === "function") {
      window.updateDynavecChartsTheme(theme);
    }
  }

  function initTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem("dynavec-theme");
    } catch (e) {}

    // Default to dark mode unless user previously explicitly selected light
    var theme = stored === "light" ? "light" : "dark";
    applyTheme(theme);

    function onToggle() {
      var current = document.documentElement.getAttribute("data-theme") || "dark";
      var next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      try {
        localStorage.setItem("dynavec-theme", next);
      } catch (e) {}
    }

    var toggleBtn = document.getElementById("themeToggle");
    var mobileToggleBtn = document.getElementById("mobileThemeToggle");

    if (toggleBtn) {
      toggleBtn.addEventListener("click", onToggle);
    }
    if (mobileToggleBtn) {
      mobileToggleBtn.addEventListener("click", onToggle);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTheme);
  } else {
    initTheme();
  }
})();

/* ---- 14. Lightweight Python / Shell Syntax Highlighter ---- */
(function () {
  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function highlightSyntax(rawText) {
    const lines = rawText.split("\n");
    return lines
      .map((line) => {
        let codePart = line;
        let commentPart = "";

        // Find comment start outside quotes
        let inSingle = false;
        let inDouble = false;
        let cIdx = -1;
        for (let i = 0; i < line.length; i++) {
          const ch = line[i];
          if (ch === "'" && !inDouble && (i === 0 || line[i - 1] !== "\\")) {
            inSingle = !inSingle;
          } else if (ch === '"' && !inSingle && (i === 0 || line[i - 1] !== "\\")) {
            inDouble = !inDouble;
          } else if (ch === "#" && !inSingle && !inDouble) {
            cIdx = i;
            break;
          }
        }

        if (cIdx !== -1) {
          codePart = line.substring(0, cIdx);
          commentPart = '<span class="c-comment">' + escapeHtml(line.substring(cIdx)) + "</span>";
        }

        // Tokenize strings safely
        const stringTokens = [];
        codePart = codePart.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, (match) => {
          const token = `___STR_TOKEN_${stringTokens.length}___`;
          stringTokens.push('<span class="c-str">' + escapeHtml(match) + "</span>");
          return token;
        });

        codePart = escapeHtml(codePart);

        // Keywords
        const kwRegex = /\b(from|import|for|in|if|else|elif|return|def|class|with|as|not|and|or|is|True|False|None|lambda|try|except|pip|uv|export)\b/g;
        codePart = codePart.replace(kwRegex, '<span class="c-kw">$1</span>');

        // Functions and classes
        const fnRegex = /\b([a-zA-Z_][a-zA-Z0-9_]*)(?=\s*\()/g;
        codePart = codePart.replace(fnRegex, '<span class="c-fn">$1</span>');

        // Numbers
        const numRegex = /\b(\d+(?:\.\d+)?)\b/g;
        codePart = codePart.replace(numRegex, '<span class="c-num">$1</span>');

        // Reinsert strings
        stringTokens.forEach((strHtml, idx) => {
          codePart = codePart.replace(`___STR_TOKEN_${idx}___`, strHtml);
        });

        return codePart + commentPart;
      })
      .join("\n");
  }

  function applyHighlighting() {
    document.querySelectorAll(".code code").forEach((codeEl) => {
      if (codeEl.dataset.highlighted) return;
      codeEl.dataset.highlighted = "true";
      codeEl.innerHTML = highlightSyntax(codeEl.textContent);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyHighlighting);
  } else {
    applyHighlighting();
  }
})();

/* ---- 15. Hero Stats Count-Up Animation ---- */
(function () {
  function initHeroCounters() {
    const statElements = document.querySelectorAll(".hero__stats .stat__n");
    if (!statElements.length) return;
    let animated = false;

    function runCounters() {
      if (animated) return;
      animated = true;

      statElements.forEach((el) => {
        const text = el.textContent.trim();
        let prefix = "";
        let suffix = "";
        let numStr = text;

        if (numStr.startsWith("$")) {
          prefix = "$";
          numStr = numStr.substring(1);
        }
        if (numStr.endsWith("%")) {
          suffix = "%";
          numStr = numStr.slice(0, -1);
        }

        const target = parseFloat(numStr);
        if (isNaN(target) || target <= 0) return;

        const duration = 1200;
        let startTime = null;

        function step(timestamp) {
          if (!startTime) startTime = timestamp;
          const progress = Math.min((timestamp - startTime) / duration, 1);
          const ease = 1 - Math.pow(1 - progress, 3);
          const current = Math.floor(ease * target);
          el.textContent = prefix + current.toLocaleString() + suffix;
          if (progress < 1) {
            requestAnimationFrame(step);
          } else {
            el.textContent = prefix + target.toLocaleString() + suffix;
          }
        }
        requestAnimationFrame(step);
      });
    }

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              runCounters();
              observer.disconnect();
            }
          });
        },
        { threshold: 0.1 }
      );
      const container = document.querySelector(".hero__stats");
      if (container) observer.observe(container);
      else runCounters();
    } else {
      runCounters();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHeroCounters);
  } else {
    initHeroCounters();
  }
})();

/* ---- 16. Nav Active Section Scroll Spy ---- */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const navLinks = document.querySelectorAll(".nav__links a[href^='#']");
    if (!navLinks.length || !("IntersectionObserver" in window)) return;

    const sections = Array.from(navLinks)
      .map((link) => {
        const id = link.getAttribute("href").replace("#", "");
        return document.getElementById(id);
      })
      .filter(Boolean);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            navLinks.forEach((link) => {
              if (link.getAttribute("href") === "#" + id) {
                link.classList.add("is-active");
              } else {
                link.classList.remove("is-active");
              }
            });
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );

    sections.forEach((sec) => observer.observe(sec));
  });
})();

/* ---- 17. Floating Back to Top Button ---- */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const btt = document.getElementById("backToTop");
    if (!btt) return;

    window.addEventListener(
      "scroll",
      function () {
        if (window.scrollY > 400) {
          btt.classList.add("is-visible");
        } else {
          btt.classList.remove("is-visible");
        }
      },
      { passive: true }
    );

    btt.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
})();


