(() => {
  "use strict";

  // State
  let flows = [];
  let selectedId = null;
  let ws = null;
  let activeTab = "response-headers";
  let filters = { search: "", method: "", status: "" };

  // DOM refs
  const $list = document.getElementById("list-body");
  const $detail = document.getElementById("detail-panel");
  const $search = document.getElementById("search-input");
  const $methodFilter = document.getElementById("method-filter");
  const $statusFilter = document.getElementById("status-filter");
  const $clearBtn = document.getElementById("clear-btn");
  const $connDot = document.getElementById("conn-dot");
  const $count = document.getElementById("flow-count");

  // ── WebSocket ──

  function connectWS() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
      $connDot.classList.add("connected");
      $connDot.title = "Connected";
    };

    ws.onclose = () => {
      $connDot.classList.remove("connected");
      $connDot.title = "Disconnected";
      setTimeout(connectWS, 2000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "new_flow") {
        addFlow(msg.flow);
      }
    };
  }

  // ── Data ──

  function addFlow(flow) {
    flows.unshift(flow);
    if (matchesFilters(flow)) {
      renderFlowRow(flow, true);
    }
    updateCount();
  }

  function matchesFilters(flow) {
    if (filters.method && flow.method !== filters.method) return false;
    if (filters.status) {
      const s = String(flow.status_code || "");
      if (filters.status === "2xx" && !s.startsWith("2")) return false;
      if (filters.status === "3xx" && !s.startsWith("3")) return false;
      if (filters.status === "4xx" && !s.startsWith("4")) return false;
      if (filters.status === "5xx" && !s.startsWith("5")) return false;
    }
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!flow.url.toLowerCase().includes(q) && !flow.host.toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  }

  function updateCount() {
    const visible = flows.filter(matchesFilters).length;
    $count.textContent = `${visible} request${visible !== 1 ? "s" : ""}`;
  }

  // ── List rendering ──

  function renderFlowRow(flow, prepend = false) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.dataset.id = flow.id;

    const sc = flow.status_code || "";
    const statusClass = sc ? `status-${String(sc)[0]}xx` : "";
    const methodClass = `method-${flow.method}`;

    const duration = flow.duration_ms != null ? `${Math.round(flow.duration_ms)}ms` : "—";
    const contentType = (flow.content_type || "").replace("application/", "").replace("text/", "");

    row.innerHTML = `
      <span class="status ${statusClass}">${sc || "..."}</span>
      <span class="method ${methodClass}">${flow.method}</span>
      <span class="path-cell"><span class="host">${escapeHtml(flow.host)}</span>${escapeHtml(flow.path)}</span>
      <span class="type-cell" title="${escapeHtml(flow.content_type || "")}">${escapeHtml(contentType)}</span>
      <span class="time-cell">${duration}</span>
    `;

    row.addEventListener("click", () => selectFlow(flow.id));

    if (prepend) {
      $list.prepend(row);
    } else {
      $list.appendChild(row);
    }
  }

  function renderAllRows() {
    $list.innerHTML = "";
    const filtered = flows.filter(matchesFilters);
    for (const f of filtered) {
      renderFlowRow(f);
    }
    updateCount();
  }

  // ── Detail panel ──

  async function selectFlow(id) {
    selectedId = id;

    document.querySelectorAll(".list-row.selected").forEach((el) => el.classList.remove("selected"));
    const row = document.querySelector(`.list-row[data-id="${id}"]`);
    if (row) row.classList.add("selected");

    try {
      const resp = await fetch(`/api/requests/${id}`);
      if (!resp.ok) return;
      const flow = await resp.json();
      renderDetail(flow);
    } catch (err) {
      console.error("Failed to load detail:", err);
    }
  }

  function renderDetail(flow) {
    const sc = flow.status_code || "";
    const statusClass = sc ? `status-${String(sc)[0]}xx` : "";
    const duration = flow.duration_ms != null ? `${Math.round(flow.duration_ms)}ms` : "—";
    const size = flow.response_size != null ? formatBytes(flow.response_size) : "—";

    $detail.innerHTML = `
      <div class="detail-header">
        <div class="detail-url">
          <span class="method method-${flow.method}">${flow.method}</span>
          <span class="status ${statusClass}">${sc}</span>
          ${escapeHtml(flow.url)}
        </div>
        <div class="detail-meta">
          <span>Duration: ${duration}</span>
          <span>Size: ${size}</span>
          <span>Type: ${escapeHtml(flow.content_type || "—")}</span>
        </div>
      </div>
      <div class="tabs">
        <div class="tab ${activeTab === "response-headers" ? "active" : ""}" data-tab="response-headers">Response Headers</div>
        <div class="tab ${activeTab === "request-headers" ? "active" : ""}" data-tab="request-headers">Request Headers</div>
        <div class="tab ${activeTab === "response-body" ? "active" : ""}" data-tab="response-body">Response Body</div>
        <div class="tab ${activeTab === "request-body" ? "active" : ""}" data-tab="request-body">Request Body</div>
      </div>
      <div class="tab-content" id="tab-content"></div>
    `;

    $detail.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        activeTab = tab.dataset.tab;
        $detail.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        renderTabContent(flow);
      });
    });

    renderTabContent(flow);
  }

  function renderTabContent(flow) {
    const $content = document.getElementById("tab-content");
    if (!$content) return;

    switch (activeTab) {
      case "response-headers":
        $content.innerHTML = renderHeaders(flow.response_headers);
        break;
      case "request-headers":
        $content.innerHTML = renderHeaders(flow.request_headers);
        break;
      case "response-body":
        $content.innerHTML = renderBody(flow.response_body, flow.content_type);
        break;
      case "request-body": {
        const reqCt = flow.request_headers?.["content-type"] || flow.request_headers?.["Content-Type"] || "";
        $content.innerHTML = renderBody(flow.request_body, reqCt);
        break;
      }
    }

    // Bind copy buttons
    $content.querySelectorAll(".copy-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        navigator.clipboard.writeText(btn.dataset.copy).then(() => {
          btn.textContent = "Copied!";
          setTimeout(() => (btn.textContent = "Copy"), 1500);
        });
      });
    });
  }

  function renderHeaders(headers) {
    if (!headers || Object.keys(headers).length === 0) {
      return '<div class="empty-body">No headers</div>';
    }
    let html = '<table class="headers-table">';
    for (const [k, v] of Object.entries(headers)) {
      html += `<tr>
        <td class="header-name">${escapeHtml(k)}</td>
        <td class="header-value">${escapeHtml(String(v))}</td>
      </tr>`;
    }
    html += "</table>";
    return html;
  }

  function renderBody(body, contentType) {
    if (!body) return '<div class="empty-body">No body</div>';
    if (body.startsWith("[binary content:") || body.startsWith("[truncated:")) {
      return `<div class="empty-body">${escapeHtml(body)}</div>`;
    }

    const ct = (contentType || "").toLowerCase();
    const isJson = ct.includes("json") || (body.trimStart().startsWith("{") || body.trimStart().startsWith("["));

    let formatted;
    let rawText = body;

    if (isJson) {
      try {
        const parsed = JSON.parse(body);
        rawText = JSON.stringify(parsed, null, 2);
        formatted = syntaxHighlightJson(rawText);
      } catch {
        formatted = escapeHtml(body);
      }
    } else {
      formatted = escapeHtml(body);
    }

    return `
      <div class="body-actions">
        <button class="copy-btn" data-copy="${escapeAttr(rawText)}">Copy</button>
      </div>
      <div class="body-content">${formatted}</div>
    `;
  }

  function syntaxHighlightJson(json) {
    return escapeHtml(json).replace(
      /("(?:\\.|[^"\\])*")\s*:/g,
      '<span class="json-key">$1</span>:'
    ).replace(
      /:\s*("(?:\\.|[^"\\])*")/g,
      ': <span class="json-string">$1</span>'
    ).replace(
      /:\s*(\d+\.?\d*)/g,
      ': <span class="json-number">$1</span>'
    ).replace(
      /:\s*(true|false)/g,
      ': <span class="json-boolean">$1</span>'
    ).replace(
      /:\s*(null)/g,
      ': <span class="json-null">$1</span>'
    );
  }

  // ── Utilities ──

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function escapeAttr(s) {
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const units = ["B", "KB", "MB"];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 2);
    return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
  }

  // ── Filters ──

  let filterTimeout;
  function onFilterChange() {
    clearTimeout(filterTimeout);
    filterTimeout = setTimeout(() => {
      filters.search = $search.value;
      filters.method = $methodFilter.value;
      filters.status = $statusFilter.value;
      renderAllRows();
    }, 150);
  }

  $search.addEventListener("input", onFilterChange);
  $methodFilter.addEventListener("change", onFilterChange);
  $statusFilter.addEventListener("change", onFilterChange);

  // ── Clear ──

  $clearBtn.addEventListener("click", async () => {
    if (!confirm("Clear all captured requests?")) return;
    try {
      await fetch("/api/requests", { method: "DELETE" });
      flows = [];
      selectedId = null;
      $list.innerHTML = "";
      $detail.innerHTML = '<div class="detail-empty">Select a request to view details</div>';
      updateCount();
    } catch (err) {
      console.error("Failed to clear:", err);
    }
  });

  // ── Panel resize ──

  const $listPanel = document.querySelector(".list-panel");
  const $handle = document.querySelector(".resize-handle");
  let resizing = false;

  $handle.addEventListener("mousedown", (e) => {
    resizing = true;
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!resizing) return;
    const pct = (e.clientX / window.innerWidth) * 100;
    if (pct > 20 && pct < 80) {
      $listPanel.style.width = `${pct}%`;
    }
  });

  document.addEventListener("mouseup", () => {
    resizing = false;
  });

  // ── Initial load ──

  async function loadInitial() {
    try {
      const resp = await fetch("/api/requests?page=1&page_size=500");
      const data = await resp.json();
      flows = data.flows.reverse();
      renderAllRows();
    } catch (err) {
      console.error("Failed to load:", err);
    }
  }

  loadInitial();
  connectWS();
})();
