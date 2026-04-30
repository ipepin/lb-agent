const root = document.querySelector("#app");
const projectDialog = document.querySelector("#project-dialog");
const emailDialog = document.querySelector("#email-dialog");
const taskDialog = document.querySelector("#task-dialog");
const taskFromEmailDialog = document.querySelector("#task-from-email-dialog");
const messageDialog = document.querySelector("#message-dialog");
const passwordDialog = document.querySelector("#password-dialog");

const NAV_ITEMS = [
  ["dashboard", "Přehled", "Souhrn systému"],
  ["inbox", "Nezpracované", "Co čeká na rozhodnutí"],
  ["conversations", "Konverzace", "Vlákna e-mailů"],
  ["emails", "E-maily", "Všechny přijaté zprávy"],
  ["projects", "Zakázky", "Hlavní pracovní prostor"],
  ["tasks", "Úkoly", "Přidělené a otevřené"],
  ["users", "Uživatelé", "Přístupy a role"],
  ["workers", "Pracovníci", "Lidé a sazby"],
  ["worklogs", "Výkazy", "Hodiny a proplacení"],
  ["workerPortal", "Pro pracovníky", "Jednoduchý zápis práce"],
  ["archive", "Archiv", "Odložené položky"],
];

const ROLE_VIEWS = {
  owner: NAV_ITEMS.map(([key]) => key),
  admin: ["dashboard", "projects", "tasks", "workers", "worklogs"],
  worker: ["workerPortal"],
};

const PROJECT_SECTION_TABS = [
  ["overview", "Přehled"],
  ["emails", "E-maily"],
  ["documents", "Dokumenty"],
  ["tasks", "Úkoly"],
  ["worklogs", "Hodiny"],
];

const PROJECT_STATUS_LABELS = {
  new: "Nová",
  offer: "Cenová nabídka",
  planned: "Naplánovaná",
  waiting: "Čekající",
  in_progress: "Rozpracovaná",
  done: "Dokončená",
  closed: "Uzavřená",
  archived: "Archivovaná",
};

const PRIORITY_LABELS = {
  low: "Nízká",
  normal: "Normální",
  high: "Vysoká",
  urgent: "Urgentní",
};

const EMAIL_CATEGORY_LABELS = {
  uncategorized: "Neroztříděné",
  task: "Úkol",
  invoice: "Faktura",
  calendar: "Kalendář",
  new_order: "Zakázka",
  newsletter: "Newsletter",
  marketing: "Marketing",
  bank: "Banka",
  notification: "Notifikace",
  general: "Evidované",
};

const TASK_STATUS_LABELS = {
  pending: "Čeká",
  waiting: "Čeká na potvrzení",
  planned: "Naplánováno",
  in_progress: "Rozpracováno",
  scheduled: "Zaneseno v kalendáři",
  done: "Hotovo",
  archived: "Archivováno",
};

const PAYMENT_STATUS_LABELS = {
  paid: "Proplaceno",
  unpaid: "Neproplaceno",
};

const state = {
  currentUser: null,
  authReady: false,
  activeView: "dashboard",
  message: null,
  dashboard: null,
  inbox: { emails: [], tasks: [] },
  archive: { emails: [], tasks: [] },
  conversations: [],
  conversationDetail: null,
  emails: [],
  tasks: [],
  users: [],
  projects: [],
  projectDetail: null,
  projectSection: "overview",
  invoices: [],
  workers: [],
  worklogs: [],
  worklogSummary: [],
  selectedConversationId: null,
  selectedEmailId: null,
  selectedTaskId: null,
  selectedUserId: null,
  selectedProjectId: null,
  selectedInvoiceId: null,
  selectedWorkerId: null,
  selectedWorklogId: null,
  selectedWorklogSummaryKey: null,
  modalTaskProjectId: null,
  modalTaskEmailId: null,
  selectedArchiveKey: null,
  selectedInboxKey: null,
  modalEmailId: null,
  selectedEmailIds: new Set(),
  selectedTaskIds: new Set(),
  emailSearch: "",
  emailCategoryFilter: "all",
  worklogWorkerFilter: "",
  worklogProjectFilter: "",
  worklogPaymentFilter: "all",
  projectAutosaveStatus: "idle",
  calendarMonth: null,
  selectedCalendarDate: null,
  calendarMode: "month",
};

let projectAutosaveTimer = null;

const BROKEN_CZECH_REPLACEMENTS = [
  ["Â·", "·"],
  ["â€¦", "…"],
  ["Ã¡", "á"],
  ["Ã", "Á"],
  ["Ăˇ", "á"],
  ["Ă", "Á"],
  ["Ã©", "é"],
  ["Ã‰", "É"],
  ["Ă©", "é"],
  ["Ă‰", "É"],
  ["Ã­", "í"],
  ["Ã", "Í"],
  ["Ă­", "í"],
  ["Ă", "Í"],
  ["Ã³", "ó"],
  ["Ã“", "Ó"],
  ["Ăł", "ó"],
  ["Ă“", "Ó"],
  ["Ãº", "ú"],
  ["Ãš", "Ú"],
  ["Ăş", "ú"],
  ["Ăš", "Ú"],
  ["Ã½", "ý"],
  ["Ã", "Ý"],
  ["Ă˝", "ý"],
  ["Ă", "Ý"],
  ["Ä›", "ě"],
  ["Ä", "ě"],
  ["Ä", "Ě"],
  ["ÄŤ", "č"],
  ["Ä", "č"],
  ["ÄŚ", "Č"],
  ["ÄŒ", "Č"],
  ["Ä", "ď"],
  ["Ä", "Ď"],
  ["Ĺ™", "ř"],
  ["Ĺ", "Ř"],
  ["Å™", "ř"],
  ["Å", "Ř"],
  ["Ĺž", "ž"],
  ["Ĺ˝", "Ž"],
  ["Å¾", "ž"],
  ["Å½", "Ž"],
  ["Ĺ¡", "š"],
  ["Ĺ ", "Š"],
  ["Å¡", "š"],
  ["Å ", "Š"],
  ["ĹŻ", "ů"],
  ["Ĺ¯", "ů"],
  ["Ĺ®", "Ů"],
  ["Å¯", "ů"],
  ["Å®", "Ů"],
  ["Ĺ", "ň"],
  ["Ĺˆ", "Ň"],
  ["Å", "ň"],
  ["Å", "ň"],
  ["PĹ™", "Př"],
  ["pĹ™", "př"],
  ["PÅ™", "Př"],
  ["pÅ™", "př"],
  ["PĹŻ", "Pů"],
  ["pĹŻ", "pů"],
  ["PÅ¯", "Pů"],
  ["pÅ¯", "pů"],
  ["DoplĹ", "Doplň"],
];

function normalizeCzechText(value) {
  let text = String(value ?? "");
  for (const [broken, fixed] of BROKEN_CZECH_REPLACEMENTS) {
    text = text.split(broken).join(fixed);
  }
  return text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDate(value, withTime = true) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  const options = withTime
    ?{ day: "numeric", month: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "numeric", month: "numeric", year: "numeric" };
  return new Intl.DateTimeFormat("cs-CZ", options).format(date).replace(",", "");
}

function formatNumber(value, digits = 0) {
  return new Intl.NumberFormat("cs-CZ", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value || 0));
}

function formatCurrency(value) {
  return `${formatNumber(value || 0, 2)} Kč`;
}

function formatHours(value) {
  return `${formatNumber(value || 0, 2)} h`;
}

function toDateKey(value = null) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function monthStartKey(value = null) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return toDateKey();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
}

function parseDateKey(value) {
  if (!value) return null;
  const [year, month, day] = String(value).split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

function shiftMonthKey(value, delta) {
  const current = parseDateKey(value) || new Date();
  return monthStartKey(new Date(current.getFullYear(), current.getMonth() + delta, 1));
}

function getWeekStartKey(value = null) {
  const current = parseDateKey(value) || new Date();
  return toDateKey(addDays(current, -((current.getDay() + 6) % 7)));
}

function shiftDateKey(value, days) {
  return toDateKey(addDays(parseDateKey(value) || new Date(), days));
}

function formatMonthLabel(value) {
  const date = parseDateKey(value) || new Date();
  return new Intl.DateTimeFormat("cs-CZ", { month: "long", year: "numeric" }).format(date);
}

function isSameMonth(dateKey, monthKey) {
  return String(dateKey || "").slice(0, 7) === String(monthKey || "").slice(0, 7);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function parseDecimal(value) {
  if (value === null || value === undefined) return 0;
  const normalized = String(value).trim().replace(/\s+/g, "").replace(",", ".");
  if (!normalized) return 0;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ?parsed : 0;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `Chyba ${response.status}`;
    const rawText = await response.text();
    if (rawText) {
      try {
        const payload = JSON.parse(rawText);
        detail = payload.detail || payload.message || rawText || detail;
      } catch {
        detail = rawText || detail;
      }
    }
    throw new Error(detail);
  }
  return response.json();
}

function showMessage(type, text) {
  const dialog = messageDialog;
  if (!dialog) return;
  const normalizedType = ["ok", "error", "info"].includes(type) ? type : "info";
  const titleMap = {
    ok: "Hotovo",
    error: "Chyba",
    info: "Informace",
  };
  const iconMap = {
    ok: "✓",
    error: "!",
    info: "i",
  };
  dialog.innerHTML = normalizeCzechText(`
    <div class="modal-card message-dialog-card">
      <div class="message-dialog-body">
        <div class="message-dialog-head">
          <div class="message-dialog-icon ${escapeHtml(normalizedType)}">${escapeHtml(iconMap[normalizedType])}</div>
          <div class="message-dialog-copy">
            <h3 class="message-dialog-title ${escapeHtml(normalizedType)}">${escapeHtml(titleMap[normalizedType])}</h3>
            <p class="message-dialog-text">${escapeHtml(text)}</p>
          </div>
        </div>
        <div class="message-dialog-actions">
          <button type="button" class="button button-primary" data-close-message-dialog>OK</button>
        </div>
      </div>
    </div>
  `);
  if (dialog.open) {
    dialog.close();
  }
  dialog.showModal();
}

function getProjectName(projectId) {
  const project = state.projects.find((item) => item.id === projectId);
  return project ?project.name : "-";
}

function getWorkerName(workerId) {
  const worker = state.workers.find((item) => item.id === workerId);
  return worker ?worker.full_name : "-";
}

function getWorkerPayoutRate(workerId) {
  const worker = state.workers.find((item) => item.id === Number(workerId));
  if (!worker) return null;
  const payoutRate = parseDecimal(worker.payout_rate);
  if (payoutRate > 0) return payoutRate;
  const hourlyRate = parseDecimal(worker.hourly_rate);
  if (hourlyRate > 0) return hourlyRate;
  return null;
}

function getWorklogPayoutAmount(item) {
  if (!item) return 0;
  if (item.payout_amount !== null && item.payout_amount !== undefined && item.payout_amount !== "") {
    return Number(item.payout_amount) || 0;
  }
  const rate = getWorkerPayoutRate(item.worker_id);
  if (!rate) return 0;
  return Math.round((Number(item.hours || 0) * Number(rate) + Number(item.material_cost || 0)) * 100) / 100;
}

function getProjectStatusLabel(status) {
  return PROJECT_STATUS_LABELS[status] || status || "-";
}

function getPriorityLabel(priority) {
  return PRIORITY_LABELS[priority] || priority || "-";
}

function getEmailCategoryLabel(category) {
  return EMAIL_CATEGORY_LABELS[category] || category || "-";
}

function getTaskStatusLabel(status) {
  return TASK_STATUS_LABELS[status] || status || "-";
}

function getPaymentStatusLabel(status) {
  return PAYMENT_STATUS_LABELS[status] || status || "-";
}

function getTaskCalendarStatusLabel(event) {
  if (!event) return "Bez kalendáře";
  if (event.external_event_id) return "Zapsáno v Google Kalendáři";
  return "Uloženo jen lokálně";
}

function getPriorityClass(priority) {
  const normalized = String(priority || "normal");
  if (normalized === "urgent") return "urgent";
  if (normalized === "high") return "high";
  if (normalized === "low") return "low";
  return "normal";
}

function getPriorityColorLabel(priority) {
  const normalized = String(priority || "normal");
  if (normalized === "urgent") return "Urgentní";
  if (normalized === "high") return "Vysoká";
  if (normalized === "low") return "Nízká";
  return "Normální";
}

function truncateText(value, maxLength = 28) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function getCalendarDisplayName(event, maxLength = 28) {
  const taskTitle = String(event?.task_title || event?.title || "").trim();
  if (!taskTitle) return "Bez názvu";
  return truncateText(taskTitle, maxLength);
}

function getCalendarFullLabel(event) {
  return String(event?.task_title || event?.title || "").trim() || "Bez názvu";
}

function updateWorklogPayoutSuggestion(form, force = false) {
  if (!(form instanceof HTMLFormElement)) return;
  if (form.id === "project-worklog-form") return;
  if (!["worker-portal-form"].includes(form.id)) return;

  const workerId = form.querySelector('[name="worker_id"]')?.value || "";
  const hours = parseDecimal(form.querySelector('[name="hours"]')?.value || 0);
  const rateInput = form.querySelector('[name="rate"]');
  const materialInput = form.querySelector('[name="material_cost"]');
  const payoutInput = form.querySelector('[name="payout_amount"]');
  if (!(materialInput instanceof HTMLInputElement)) return;
  if (!(payoutInput instanceof HTMLInputElement)) return;

  const defaultRate = getWorkerPayoutRate(workerId);
  if (rateInput instanceof HTMLInputElement) {
    const shouldAutofillRate = force || rateInput.dataset.autoRate !== "false" || !rateInput.value;
    if (defaultRate !== null && shouldAutofillRate) {
      rateInput.value = String(parseDecimal(defaultRate));
      rateInput.dataset.autoRate = "true";
    }
  }

  const rate = rateInput instanceof HTMLInputElement ?parseDecimal(rateInput.value) : parseDecimal(defaultRate || 0);
  const material = parseDecimal(materialInput.value || 0);
  const shouldAutofillPayout = force || payoutInput.dataset.autoPayout !== "false" || !payoutInput.value;

  if (!rate || !hours || !shouldAutofillPayout) {
    if ((!rate || !hours) && shouldAutofillPayout) {
      payoutInput.value = "";
    }
    return;
  }

  payoutInput.value = String(Math.round((hours * rate + material) * 100) / 100);
  payoutInput.dataset.autoPayout = "true";
}

function updateProjectWorklogRowPayout(row, force = false) {
  if (!(row instanceof HTMLElement)) return;
  const workerInput = row.querySelector('[name^="worker_id_"]');
  const hoursInput = row.querySelector('[name^="hours_"]');
  const rateInput = row.querySelector('[name^="rate_"]');
  const materialInput = row.querySelector('[name^="material_cost_"]');
  const payoutInput = row.querySelector('[name^="payout_amount_"]');
  if (!(workerInput instanceof HTMLSelectElement)) return;
  if (!(hoursInput instanceof HTMLInputElement)) return;
  if (!(rateInput instanceof HTMLInputElement)) return;
  if (!(materialInput instanceof HTMLInputElement)) return;
  if (!(payoutInput instanceof HTMLInputElement)) return;

  const defaultRate = getWorkerPayoutRate(workerInput.value);
  const shouldAutofillRate = rateInput.dataset.autoRate !== "false" || !rateInput.value;
  if (defaultRate !== null && shouldAutofillRate) {
    rateInput.value = String(parseDecimal(defaultRate));
    rateInput.dataset.autoRate = "true";
  }

  const rate = parseDecimal(rateInput.value);
  const hours = parseDecimal(hoursInput.value);
  const material = parseDecimal(materialInput.value || 0);

  if (!workerInput.value || !rate || !hours) {
    if (!workerInput.value || !hours) {
      payoutInput.value = "";
    }
    return;
  }

  payoutInput.value = String(Math.round((hours * rate + material) * 100) / 100);
  payoutInput.dataset.autoPayout = "true";
}

function emailStateClass(email) {
  if (email.status === "confirmed" || email.category !== "uncategorized") return "ok";
  return "attention";
}

function taskStateClass(task) {
  if (task.status === "done" || task.status === "archived") return "ok";
  return "attention";
}

function invoiceStateClass(invoice) {
  if (invoice.status === "paid" || invoice.status === "archived") return "ok";
  return "attention";
}

function worklogStateClass(item) {
  return item.payment_status === "paid" ?"ok" : "attention";
}

function getCurrentRole() {
  return state.currentUser?.role || null;
}

function getVisibleNavItems() {
  const role = getCurrentRole();
  if (!role) return [];
  const allowedViews = new Set(ROLE_VIEWS[role] || []);
  return NAV_ITEMS.filter(([key]) => allowedViews.has(key));
}

function getCounts() {
  const dashboardCounts = state.dashboard?.counts || {};
  return {
    dashboard: 0,
    inbox: (state.inbox.emails?.length || 0) + (state.inbox.tasks?.length || 0) || dashboardCounts.unprocessed_emails || 0,
    conversations: state.conversations.length,
    emails: state.emails.length || dashboardCounts.emails || 0,
    projects: state.projects.length || dashboardCounts.active_projects || 0,
    tasks: state.tasks.filter((item) => item.status !== "archived").length || dashboardCounts.open_tasks || 0,
    users: state.users.length || 0,
    invoices: state.invoices.length || dashboardCounts.pending_invoices || 0,
    workers: state.workers.length || dashboardCounts.workers || 0,
    worklogs: state.worklogs.length || dashboardCounts.work_logs || 0,
    workerPortal: state.workers.length || dashboardCounts.workers || 0,
    archive: (state.archive.emails?.length || 0) + (state.archive.tasks?.length || 0),
  };
}

function getViewMeta() {
  const map = {
    dashboard: ["Přehled", "Souhrn zakázek, práce, financí a nevyřízených položek."],
    inbox: ["Nezpracované", "Rychlá triáž nových e-mailů a otevřených úkolů."],
    conversations: ["Konverzace", "Vlákna e-mailů podle Gmail konverzací."],
    emails: ["E-maily", "Kompletní seznam přijatých zpráv s hromadnou triáží."],
    projects: ["Zakázky", "Jedna zakázka jako kompaktní pracovní prostor."],
    tasks: ["Úkoly", "Otevřené i hotové úkoly navázané na zakázky a e-maily."],
    users: ["Uživatelé", "Správa přístupů, rolí a navázání na pracovníky."],
    workers: ["Pracovníci", "Karta pracovníka, sazby a rozpad práce po zakázkách."],
    worklogs: ["Výkazy", "Tabulkový přehled hodin, nákladů a proplacení."],
    workerPortal: ["Pro pracovníky", "Jednoduchý zápis práce bez zbytečného balastu."],
    archive: ["Archiv", "Odložené e-maily a hotové nebo archivované úkoly."],
  };
  return map[state.activeView] || ["LB-AGENT", ""];
}

function getInboxItems() {
  const emailItems = (state.inbox.emails || []).map((item) => ({ kind: "email", id: item.id, sort: item.received_at, item }));
  const taskItems = (state.inbox.tasks || []).map((item) => ({ kind: "task", id: item.id, sort: item.due_date || item.created_at, item }));
  return [...emailItems, ...taskItems].sort((a, b) => (b.sort || "").localeCompare(a.sort || ""));
}

function getArchiveItems() {
  const emailItems = (state.archive.emails || []).map((item) => ({ kind: "email", key: `email:${item.id}`, sort: item.received_at, item }));
  const taskItems = (state.archive.tasks || []).map((item) => ({ kind: "task", key: `task:${item.id}`, sort: item.completed_at || item.created_at, item }));
  return [...emailItems, ...taskItems].sort((a, b) => (b.sort || "").localeCompare(a.sort || ""));
}

function normalizeSearchText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function getFilteredEmails() {
  const terms = normalizeSearchText(state.emailSearch).split(" ").filter(Boolean);
  return state.emails.filter((email) => {
    const haystack = normalizeSearchText([
      email.subject,
      email.sender,
      email.body,
      email.summary,
      (email.attachments || []).map((attachment) => attachment.name || attachment.path || "").join(" "),
      (email.projects || []).map((project) => project.name || "").join(" "),
    ].join(" "));
    const inSearch = !terms.length || terms.every((term) => haystack.includes(term));
    const categoryOk = state.emailCategoryFilter === "all"
      || (state.emailCategoryFilter === "unresolved" && email.category === "uncategorized")
      || email.category === state.emailCategoryFilter;
    return inSearch && categoryOk;
  });
}

function getFilteredWorklogs() {
  return state.worklogs.filter((item) => {
    const workerOk = !state.worklogWorkerFilter || String(item.worker_id) === state.worklogWorkerFilter;
    const projectOk = !state.worklogProjectFilter || String(item.project_id) === state.worklogProjectFilter;
    const paymentOk = state.worklogPaymentFilter === "all" || item.payment_status === state.worklogPaymentFilter;
    return workerOk && projectOk && paymentOk;
  });
}

function buildMessage() {
  return "";
}

function renderSidebar() {
  const counts = getCounts();
  const navItems = getVisibleNavItems();
  return `
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-kicker">LB-AGENT</span>
        <h1>VedenĂ­ zakĂˇzek</h1>
        <p>KompaktnĂ­ provoznĂ­ systĂ©m nad e-maily, zakĂˇzkami, Ăşkoly a vĂ˝kazy prĂˇce.</p>
      </div>
      <div class="sidebar-actions">
        <button type="button" class="button button-primary" data-refresh>Obnovit data</button>
        <a class="button button-secondary" href="/docs" target="_blank" rel="noreferrer">API</a>
      </div>
      <nav class="sidebar-nav">
        ${navItems.map(([key, title, subtitle]) => `
          <button type="button" class="nav-button ${state.activeView === key ?"is-active" : ""}" data-view="${key}">
            <span class="nav-button-main">
              <span class="nav-button-title">${escapeHtml(title)}</span>
              <span class="nav-button-subtitle">${escapeHtml(subtitle)}</span>
            </span>
            <span class="nav-count">${counts[key] ?? 0}</span>
          </button>
        `).join("")}
      </nav>
    </aside>
  `;
}

function renderTopbar() {
  const [title, text] = getViewMeta();
  const extraButtons = [];
  if (state.activeView === "projects") {
    extraButtons.push(`<button type="button" class="button button-primary" data-open-project-dialog>NovĂˇ zakĂˇzka</button>`);
  }
  return `
    <header class="topbar">
      <div class="page-heading">
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(text)}</p>
      </div>
      <div class="topbar-actions">
        <span class="selection-chip">${escapeHtml(state.currentUser?.full_name || "")} · ${escapeHtml(state.currentUser?.role || "")}</span>
        ${extraButtons.join("")}
        <button type="button" class="button button-secondary" data-open-password-dialog>Změnit heslo</button>
        <button type="button" class="button button-secondary" data-logout>Odhlásit</button>
        <button type="button" class="button button-secondary" data-refresh>Obnovit</button>
      </div>
    </header>
  `;
}

function renderStatsGrid(cards) {
  return `
    <div class="stats-grid">
      ${cards.map((card) => `
        <div class="stat-card">
          <span class="stat-label">${escapeHtml(card.label)}</span>
          <strong class="stat-value">${escapeHtml(card.value)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function renderSummaryStrip(cards) {
  return `
    <div class="summary-strip">
      ${cards.map((card) => `
        <div class="summary-card">
          <span class="summary-card-label">${escapeHtml(card.label)}</span>
          <strong class="summary-card-value">${escapeHtml(card.value)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function renderEmpty(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function renderListItem({ key, title, meta, subtitle, selected = false, stateClass = "", checkbox = "" }) {
  return `
    <button type="button" class="list-item ${stateClass} ${selected ?"is-selected" : ""}" data-select-item="${escapeHtml(key)}">
      <div class="list-item-head">
        <span>${meta || ""}</span>
        ${checkbox}
      </div>
      <div class="list-item-title">${title}</div>
      ${subtitle ?`<div class="list-item-meta">${subtitle}</div>` : ""}
    </button>
  `;
}

function renderDataTable(columns, rows, emptyText) {
  if (!rows.length) return renderEmpty(emptyText);
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>${columns.map((col) => `<th>${escapeHtml(col)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderPhotoThumb(doc) {
  return `
    <a class="photo-thumb" href="${escapeHtml(doc.url)}" target="_blank" rel="noreferrer">
      <img src="${escapeHtml(doc.url)}" alt="${escapeHtml(doc.title || doc.name || "Fotografie")}">
      <span>${escapeHtml(doc.title || doc.name || "Fotografie")}</span>
    </a>
  `;
}

function renderProjectLogbook(detail) {
  const photos = (detail.documents || []).filter((doc) => doc.document_type === "photo");
  const worklogs = [...(detail.work_logs || [])].sort((a, b) => String(b.work_date || "").localeCompare(String(a.work_date || "")));
  if (!worklogs.length) return renderEmpty("Zat?m bez zapsan? pr?ce.");
  return `
    <div class="logbook-list">
      ${worklogs.map((log) => {
        const logPhotos = photos.filter((doc) => Number(doc.worker_id || 0) === Number(log.worker_id || 0) && String(doc.work_date || "") === String(log.work_date || ""));
        return `
          <div class="logbook-entry ${worklogStateClass(log)}">
            <div class="logbook-entry-head">
              <div>
                <strong>${escapeHtml(getWorkerName(log.worker_id))}</strong>
                <span class="logbook-meta">${formatDate(log.work_date, false)} ? ${formatHours(log.hours)} ? Materi?l ${formatCurrency(log.material_cost)} ? K v?plat? ${formatCurrency(getWorklogPayoutAmount(log))}</span>
              </div>
              <span class="chip">${escapeHtml(getPaymentStatusLabel(log.payment_status))}</span>
            </div>
            ${log.notes ? `<div class="logbook-note">${escapeHtml(log.notes)}</div>` : ""}
            <div class="logbook-photos">
              ${logPhotos.length ? logPhotos.map((doc) => renderPhotoThumb(doc)).join("") : `<span class="field-note">Bez fotografi? k tomuto dni.</span>`}
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderTimeline(projectDetail) {
  const timeline = [];
  for (const item of projectDetail?.timeline_events || []) {
    const statusLabels = {
      new: "Nová",
      offer: "Cenová nabídka",
      planned: "Naplánovaná",
      waiting: "Čekající",
      in_progress: "Rozpracovaná",
      done: "Dokončená",
      closed: "Uzavřená",
      archived: "Archivovaná",
    };
    let text = item.title;
    if (item.event_type === "project_status" && item.details.includes("->")) {
      const [fromRaw, toRaw] = item.details.split("->").map((part) => part.trim());
      text = `Stav změněn z „${statusLabels[fromRaw] || fromRaw}“ na „${statusLabels[toRaw] || toRaw}“`;
    } else if (item.details) {
      text = `${item.title} · ${item.details}`;
    }
    timeline.push({ at: item.created_at, type: "Zakázka", text });
  }
  for (const email of projectDetail?.emails || []) {
    timeline.push({ at: email.received_at, type: "E-mail", text: `${email.subject} Â· ${email.sender}` });
  }
  for (const task of projectDetail?.tasks || []) {
    timeline.push({ at: task.due_date || task.created_at, type: "Ăškol", text: `${task.title} Â· ${getTaskStatusLabel(task.status)}` });
  }
  for (const invoice of projectDetail?.invoices || []) {
    timeline.push({ at: invoice.created_at, type: "Faktura", text: `${invoice.invoice_number || invoice.supplier} Â· ${formatCurrency(invoice.amount)}` });
  }
  for (const worklog of projectDetail?.work_logs || []) {
    timeline.push({ at: worklog.work_date, type: "PrĂˇce", text: `${getWorkerName(worklog.worker_id)} Â· ${formatHours(worklog.hours)}` });
  }
  const ordered = timeline.sort((a, b) => (b.at || "").localeCompare(a.at || "")).slice(0, 12);
  if (!ordered.length) return renderEmpty("ZatĂ­m bez ÄŤasovĂ© osy.");
  return `
    <div class="timeline-list">
      ${ordered.map((item) => `
        <div class="timeline-row">
          <div class="timeline-type">${escapeHtml(item.type)}<br><span style="font-weight:400;color:var(--muted)">${formatDate(item.at, !/^\d{4}-\d{2}-\d{2}$/.test(item.at || ""))}</span></div>
          <div class="timeline-text">${escapeHtml(item.text)}</div>
        </div>
      `).join("")}
    </div>
  `;
}

function getDashboardCalendarEvents() {
  const events = [];
  for (const task of state.tasks || []) {
    for (const event of task.calendar_events || []) {
      const startKey = toDateKey(event.starts_at);
      const endKey = toDateKey(event.ends_at || event.starts_at);
      if (!startKey) continue;
      events.push({
        id: event.id,
        title: event.title,
        starts_at: event.starts_at,
        ends_at: event.ends_at || event.starts_at,
        startKey,
        endKey: endKey || startKey,
        status: event.status,
        task_id: task.id,
        task_title: task.title,
        task_status: task.status,
        priority: task.priority || "normal",
        project_id: task.project_id,
        project_name: task.project?.name || getProjectName(task.project_id),
        workers: task.workers || [],
        external_event_id: event.external_event_id,
        attendee_emails: event.attendee_emails || [],
      });
    }
  }
  return events.sort((a, b) => String(a.starts_at || "").localeCompare(String(b.starts_at || "")));
}

function eventOverlapsDate(event, dateKey) {
  return event.startKey <= dateKey && event.endKey >= dateKey;
}

function getCalendarMonthMatrix(monthKey) {
  const monthStart = parseDateKey(monthKey) || new Date();
  const firstVisible = addDays(monthStart, -((monthStart.getDay() + 6) % 7));
  const weeks = [];
  for (let week = 0; week < 6; week += 1) {
    const days = [];
    for (let day = 0; day < 7; day += 1) {
      const current = addDays(firstVisible, week * 7 + day);
      days.push({
        key: toDateKey(current),
        day: current.getDate(),
        inMonth: current.getMonth() === monthStart.getMonth(),
      });
    }
    weeks.push(days);
  }
  return weeks;
}

function getCalendarDayEvents(dateKey) {
  return getDashboardCalendarEvents()
    .filter((event) => eventOverlapsDate(event, dateKey))
    .sort((a, b) => {
      const priorityRank = { urgent: 0, high: 1, normal: 2, low: 3 };
      const byPriority = (priorityRank[a.priority] ?? 9) - (priorityRank[b.priority] ?? 9);
      if (byPriority !== 0) return byPriority;
      return String(a.starts_at || "").localeCompare(String(b.starts_at || ""));
    });
}

function getCalendarWeekDays(selectedDateKey) {
  const weekStart = parseDateKey(getWeekStartKey(selectedDateKey)) || new Date();
  return Array.from({ length: 7 }, (_, index) => {
    const current = addDays(weekStart, index);
    return {
      key: toDateKey(current),
      day: current.getDate(),
      weekday: new Intl.DateTimeFormat("cs-CZ", { weekday: "short" }).format(current),
    };
  });
}

function renderCalendarMonthGrid(monthKey, selectedDateKey) {
  const todayKey = toDateKey();
  const weeks = getCalendarMonthMatrix(monthKey);
  const weekDays = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"];
  return `
    <div class="calendar-grid-shell">
      <div class="calendar-weekdays">
        ${weekDays.map((label) => `<span>${label}</span>`).join("")}
      </div>
      <div class="calendar-grid">
        ${weeks.map((week) => week.map((day) => {
          const events = getCalendarDayEvents(day.key);
          const visible = events.slice(0, 1);
          const moreCount = Math.max(events.length - visible.length, 0);
          return `
            <button
              type="button"
              class="calendar-day ${day.inMonth ? "" : "is-outside"} ${day.key === todayKey ? "is-today" : ""} ${day.key === selectedDateKey ? "is-selected" : ""}"
              data-calendar-date="${day.key}"
            >
              <div class="calendar-day-head">
                <span class="calendar-day-number">${day.day}</span>
                ${events.length ? `<span class="calendar-day-count">${events.length}</span>` : ""}
              </div>
              <div class="calendar-day-events">
                ${visible.map((event) => `
                  <span class="calendar-event-pill ${getPriorityClass(event.priority)} ${event.startKey !== event.endKey ? "is-range" : ""}" title="${escapeHtml(getCalendarFullLabel(event))}">
                    ${escapeHtml(getCalendarDisplayName(event, 24))}
                  </span>
                `).join("")}
                ${moreCount ? `<span class="calendar-day-more">+${moreCount} další akce</span>` : ""}
              </div>
            </button>
          `;
        }).join("")).join("")}
      </div>
    </div>
  `;
}

function renderCalendarWeekGrid(selectedDateKey) {
  const todayKey = toDateKey();
  const weekDays = getCalendarWeekDays(selectedDateKey);
  return `
    <div class="calendar-week-shell">
      ${weekDays.map((day) => {
        const events = getCalendarDayEvents(day.key);
        return `
          <button
            type="button"
            class="calendar-week-day ${day.key === todayKey ? "is-today" : ""} ${day.key === selectedDateKey ? "is-selected" : ""}"
            data-calendar-date="${day.key}"
          >
            <div class="calendar-week-day-head">
              <span class="calendar-week-day-label">${escapeHtml(day.weekday)}</span>
              <span class="calendar-week-day-number">${day.day}</span>
            </div>
            <div class="calendar-week-day-body">
              ${events.length ? events.map((event) => `
                <span class="calendar-event-pill ${getPriorityClass(event.priority)} ${event.startKey !== event.endKey ? "is-range" : ""}" title="${escapeHtml(getCalendarFullLabel(event))}">
                  ${escapeHtml(getCalendarDisplayName(event, 26))}
                </span>
              `).join("") : `<span class="calendar-week-empty">Volno</span>`}
            </div>
          </button>
        `;
      }).join("")}
    </div>
  `;
}

function renderCalendarAgenda(selectedDateKey) {
  const events = getCalendarDayEvents(selectedDateKey);
  if (!events.length) {
    return `
      <div class="calendar-agenda-empty">
        <strong>Na tento den není nic naplánované.</strong>
        <span>Můžeš dál pracovat se zakázkami a úkoly, ale v kalendáři je volno.</span>
      </div>
    `;
  }
  return `
    <div class="calendar-agenda-list">
      ${events.map((event) => `
        <article class="calendar-agenda-item ${getPriorityClass(event.priority)}">
          <div class="calendar-agenda-head">
            <div>
              <strong>${escapeHtml(getCalendarDisplayName(event, 46))}</strong>
              <div class="calendar-agenda-meta">
                ${escapeHtml(formatDate(event.starts_at))}
                ${event.startKey !== event.endKey ? ` – ${escapeHtml(formatDate(event.ends_at))}` : ""}
              </div>
            </div>
            <span class="chip priority ${getPriorityClass(event.priority)}">${escapeHtml(getPriorityColorLabel(event.priority))}</span>
          </div>
          <div class="calendar-agenda-row">
            <span><strong>Stav:</strong> ${escapeHtml(getTaskStatusLabel(event.task_status))}</span>
            <span><strong>Kalendář:</strong> ${escapeHtml(event.external_event_id ? "Google Kalendář" : "Jen lokálně")}</span>
          </div>
          <div class="calendar-agenda-row">
            <span><strong>Pracovníci:</strong> ${escapeHtml((event.workers || []).map((worker) => worker.full_name).join(", ") || "Bez přiřazení")}</span>
          </div>
          <div class="calendar-agenda-actions">
            <button type="button" class="button button-secondary" data-open-task="${event.task_id}">Otevřít úkol</button>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

function renderProjectOptions(selectedId = null) {
  return [`<option value="">Vyber zakázku</option>`]
    .concat(state.projects.map((project) => `<option value="${project.id}" ${project.id === selectedId ?"selected" : ""}>${escapeHtml(project.name)}</option>`))
    .join("");
}

function renderWorkerOptions(selectedId = null) {
  return [`<option value="">Bez pracovníka</option>`]
    .concat(
      state.workers.map(
        (worker) =>
          `<option value="${worker.id}" ${worker.id === selectedId ?"selected" : ""}>${escapeHtml(worker.full_name)}</option>`,
      ),
    )
    .join("");
}

function renderWorkerMultiOptions(selectedIds = []) {
  const selectedSet = new Set((selectedIds || []).map(Number));
  return state.workers
    .map(
      (worker) =>
        `<option value="${worker.id}" ${selectedSet.has(worker.id) ?"selected" : ""}>${escapeHtml(worker.full_name)}</option>`,
    )
    .join("");
}

function getTaskWorkerNames(task) {
  const ids = (task?.worker_ids || []).map(Number).filter(Boolean);
  if (!ids.length && task?.assigned_worker_id) {
    ids.push(Number(task.assigned_worker_id));
  }
  const names = ids
    .map((workerId) => getWorkerName(workerId))
    .filter((name) => name && name !== "-");
  return names.length ? names.join(", ") : "-";
}

function renderProjectStatusOptions(selectedStatus = "new") {
  return Object.entries(PROJECT_STATUS_LABELS)
    .map(([value, label]) => `<option value="${value}" ${value === selectedStatus ?"selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function renderPriorityOptions(selectedPriority = "normal") {
  return Object.entries(PRIORITY_LABELS)
    .map(([value, label]) => `<option value="${value}" ${value === selectedPriority ?"selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function renderTaskStatusOptions(selectedStatus = "pending") {
  return Object.entries(TASK_STATUS_LABELS)
    .filter(([value]) => value !== "archived")
    .map(([value, label]) => `<option value="${value}" ${value === selectedStatus ?"selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function renderWorkerStatusOptions(selectedStatus = "active") {
  return [
    ["active", "Aktivní"],
    ["inactive", "Neaktivní"],
  ]
    .map(([value, label]) => `<option value="${value}" ${value === selectedStatus ?"selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function toDateTimeLocal(value) {
  if (!value) return "";
  const directMatch = String(value).trim().match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/);
  if (directMatch) {
    return `${directMatch[1]}T${directMatch[2]}`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function renderEmailDetail(email) {
  if (!email) return renderEmpty("Vyber e-mail ze seznamu.");
  const assignedProjects = email.projects?.length
    ?email.projects.map((project) => `<span class="chip">${escapeHtml(project.name)}</span>`).join("")
    : `<span class="selection-chip">Bez pĹ™iĹ™azenĂ© zakĂˇzky</span>`;
  const attachments = email.attachments?.length
    ?email.attachments.map((attachment) => `<a class="button button-secondary" href="${escapeHtml(attachment.url)}" target="_blank">${escapeHtml(attachment.name)}</a>`).join(" ")
    : `<span class="selection-chip">Bez pĹ™Ă­loh</span>`;
  return `
    <div class="detail-shell">
      <div class="hero-card">
        <div>
          <p class="hero-kicker">E-mail</p>
          <h3 class="hero-title">${escapeHtml(email.subject || "Bez pĹ™edmÄ›tu")}</h3>
          <p class="hero-subtitle">${escapeHtml(email.sender)} Â· ${formatDate(email.received_at)}</p>
        </div>
        <div class="hero-side">
          <span class="status-pill">${escapeHtml(getEmailCategoryLabel(email.category))}</span>
          <span class="chip">${escapeHtml(email.status || "pending")}</span>
          <span class="chip">${escapeHtml(getPriorityLabel(email.priority))}</span>
        </div>
      </div>
      <div class="toolbar">
        <button type="button" class="button button-primary" data-email-action="create_project" data-email-id="${escapeHtml(email.id)}">NovĂˇ zakĂˇzka</button>
        <button type="button" class="button button-secondary" data-email-action="create_task" data-email-id="${escapeHtml(email.id)}">Na úkol</button>
        <button type="button" class="button button-secondary" data-email-action="mark_invoice" data-email-id="${escapeHtml(email.id)}">Faktura</button>
        <button type="button" class="button button-secondary" data-email-action="ignore" data-email-id="${escapeHtml(email.id)}">Ignorovat</button>
        <button type="button" class="button button-secondary" data-email-action="return_unprocessed" data-email-id="${escapeHtml(email.id)}">VrĂˇtit do neroztĹ™Ă­dÄ›nĂ˝ch</button>
        <button type="button" class="button button-danger" data-email-action="archive" data-email-id="${escapeHtml(email.id)}">Archivovat</button>
        <button type="button" class="button button-danger" data-delete-email="${escapeHtml(email.id)}">Smazat</button>
      </div>
      <div class="toolbar">
        <select id="email-project-select">
          ${renderProjectOptions(email.project_ids?.[0] || email.project_id)}
        </select>
        <button type="button" class="button button-secondary" data-email-action="assign_project" data-email-id="${escapeHtml(email.id)}">PĹ™idat k zakĂˇzce</button>
        ${assignedProjects}
      </div>
      <div class="detail-grid">
        <div class="detail-item"><span class="detail-item-label">PlnĂˇ adresa odesĂ­latele</span><span class="detail-item-value">${escapeHtml(email.sender)}</span></div>
        <div class="detail-item"><span class="detail-item-label">PĹ™ijato</span><span class="detail-item-value">${formatDate(email.received_at)}</span></div>
        <div class="detail-item"><span class="detail-item-label">Kategorie</span><span class="detail-item-value">${escapeHtml(getEmailCategoryLabel(email.category))}</span></div>
        <div class="detail-item"><span class="detail-item-label">ZakĂˇzek</span><span class="detail-item-value">${email.projects?.length || 0}</span></div>
      </div>
      <div class="section-card">
        <div class="panel-header"><div><h4>PĹ™Ă­lohy</h4></div></div>
        <div class="toolbar">${attachments}</div>
      </div>
      <div class="section-card">
        <div class="panel-header"><div><h4>Text e-mailu</h4></div></div>
        <pre class="text-block">${escapeHtml(email.body || "")}</pre>
      </div>
    </div>
  `;
}

function renderTaskDetail(task) {
  if (!task) return renderEmpty("Vyber Ăşkol ze seznamu.");
  const project = state.projects.find((item) => item.id === task.project_id) || null;
  const sourceEmail = task.source_email || state.emails.find((email) => email.id === task.source_email_id) || null;
  const workerIds = (task.worker_ids || []).length ? task.worker_ids : (task.assigned_worker_id ? [task.assigned_worker_id] : []);
  const workerEmails = workerIds
    .map((workerId) => state.workers.find((item) => item.id === workerId)?.email || "")
    .filter(Boolean);
  const recipients = [project?.contact_email, ...workerEmails].filter(Boolean);
  const latestCalendarEvent = task.latest_calendar_event || null;
  const calendarInvitees = latestCalendarEvent?.attendee_emails?.length ?latestCalendarEvent.attendee_emails.join(", ") : "-";
  const taskTimeline = (task.timeline || []).length
    ?task.timeline.map((entry) => `
        <div class="timeline-row">
          <div class="timeline-type">${escapeHtml(entry.kind || "Úkol")}<br><span style="font-weight:400;color:var(--muted)">${formatDate(entry.at, true)}</span></div>
          <div class="timeline-text"><strong>${escapeHtml(entry.title || "-")}</strong>${entry.details ?`<br>${escapeHtml(entry.details)}` : ""}</div>
        </div>
      `).join("")
    : `<div class="empty-state">Úkol zatím nemá historii.</div>`;
  return `
    <div class="detail-shell">
      <div class="hero-card">
        <div>
          <p class="hero-kicker">Ăškol</p>
          <h3 class="hero-title">${escapeHtml(task.title)}</h3>
          <p class="hero-subtitle">${escapeHtml(task.description || "Bez popisu")}</p>
        </div>
        <div class="hero-side">
          <span class="status-pill">${escapeHtml(getTaskStatusLabel(task.status))}</span>
          <span class="chip">${escapeHtml(getPriorityLabel(task.priority))}</span>
        </div>
      </div>
      <div class="toolbar">
        <button type="button" class="button button-primary" data-task-action="complete" data-task-id="${task.id}">DokonÄŤit</button>
        <button type="button" class="button button-secondary" data-task-action="create_calendar_event" data-task-id="${task.id}">Do kalendĂˇĹ™e</button>
        <button type="button" class="button button-secondary" data-task-email="${task.id}">Poslat e-mailem</button>
        <button type="submit" form="task-update-form" class="button button-primary">Uložit změny</button>
        <button type="button" class="button button-danger" data-task-action="archive" data-task-id="${task.id}">Archivovat</button>
        <button type="button" class="button button-danger" data-delete-task="${task.id}">Smazat</button>
      </div>
      <form id="task-update-form" class="compact-form" data-task-id="${task.id}">
        <div class="row">
          <input name="title" value="${escapeHtml(task.title)}" placeholder="Název úkolu" required>
          <select name="priority">${renderPriorityOptions(task.priority || "normal")}</select>
        </div>
        <div class="row">
          <input name="due_date" type="datetime-local" value="${escapeHtml(toDateTimeLocal(task.due_date))}">
          <select name="project_id">${renderProjectOptions(task.project_id)}</select>
        </div>
        <div class="row">
          <select name="status">${renderTaskStatusOptions(task.status || "pending")}</select>
          <select name="assigned_worker_ids" multiple size="4">${renderWorkerMultiOptions(workerIds)}</select>
        </div>
        <div class="row">
          <input name="estimated_hours" type="number" min="0" step="0.5" placeholder="Odhad hodin" value="${task.estimated_hours ?? ""}">
          <div></div>
        </div>
        <textarea name="description" rows="5" placeholder="Popis úkolu">${escapeHtml(task.description || "")}</textarea>
        ${renderSummaryStrip([
          { label: "Stav", value: getTaskStatusLabel(task.status) },
          { label: "Zakázka", value: project?.name || "Bez zakázky" },
          { label: "Pracovníci", value: getTaskWorkerNames(task) },
          { label: "Kalendář", value: getTaskCalendarStatusLabel(latestCalendarEvent) },
        ])}
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-item-label">E-maily pro notifikaci</span><span class="detail-item-value">${escapeHtml(recipients.join(", ") || "-")}</span></div>
          <div class="detail-item"><span class="detail-item-label">Pozvaní do kalendáře</span><span class="detail-item-value">${escapeHtml(calendarInvitees)}</span></div>
          <div class="detail-item"><span class="detail-item-label">Poslední kalendářová událost</span><span class="detail-item-value">${latestCalendarEvent ?`${escapeHtml(latestCalendarEvent.title)} · ${formatDate(latestCalendarEvent.starts_at)}` : "-"}</span></div>
          <div class="detail-item"><span class="detail-item-label">Odhad hodin</span><span class="detail-item-value">${task.estimated_hours ?? "-"}</span></div>
        </div>
        ${sourceEmail ?`
          <div class="section-card">
            <div class="panel-header"><div><h4>Zdrojový e-mail</h4></div></div>
            <div class="detail-grid">
              <div class="detail-item"><span class="detail-item-label">Předmět</span><span class="detail-item-value">${escapeHtml(sourceEmail.subject)}</span></div>
              <div class="detail-item"><span class="detail-item-label">Odesílatel</span><span class="detail-item-value">${escapeHtml(sourceEmail.sender)}</span></div>
              <div class="detail-item"><span class="detail-item-label">Přijato</span><span class="detail-item-value">${formatDate(sourceEmail.received_at)}</span></div>
              <div class="detail-item"><span class="detail-item-label">Akce</span><span class="detail-item-value"><button type="button" class="button button-secondary button-small" data-open-email="${escapeHtml(sourceEmail.id)}">Otevřít e-mail</button></span></div>
            </div>
          </div>
        ` : ""}
        <div class="section-card">
          <div class="panel-header"><div><h4>Historie úkolu</h4></div></div>
          <div class="timeline-list">${taskTimeline}</div>
        </div>
        <div class="toolbar">
          <span class="selection-chip">Úkol můžeš upravit přímo tady.</span>
          <span class="toolbar-spacer"></span>
          <button type="submit" class="button button-primary">Uložit změny</button>
        </div>
      </form>
    </div>
  `;
}

function openTaskEmailDraft(task) {
  if (!task) {
    showMessage("error", "NejdĹ™Ă­v vyber Ăşkol.");
    return;
  }
  const project = state.projects.find((item) => item.id === task.project_id) || null;
  const workerIds = (task.worker_ids || []).length ? task.worker_ids : (task.assigned_worker_id ? [task.assigned_worker_id] : []);
  const recipients = [project?.contact_email, ...workerIds.map((workerId) => state.workers.find((item) => item.id === workerId)?.email || "")]
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index);

  if (!recipients.length) {
    showMessage("error", "U Ăşkolu nenĂ­ kam e-mail poslat. DoplĹ e-mail zakĂˇzky nebo pracovnĂ­ka.");
    return;
  }

  const bodyParts = [
    `Úkol: ${task.title}`,
    `Zakázka: ${getProjectName(task.project_id)}`,
    `Termín: ${task.due_date ? formatDate(task.due_date) : "-"}`,
    `Pracovníci: ${getTaskWorkerNames(task)}`,
    "",
    task.description || "",
  ];
  const mailto = `mailto:${recipients.join(",")}?subject=${encodeURIComponent(`Úkol: ${task.title}`)}&body=${encodeURIComponent(bodyParts.join("\n"))}`;
  window.location.href = mailto;
}

function renderInvoiceDetail(invoice) {
  if (!invoice) return renderEmpty("Vyber fakturu ze seznamu.");
  const sourceEmail = state.emails.find((email) => email.id === invoice.source_email_id);
  return `
    <div class="detail-shell">
      <div class="hero-card">
        <div>
          <p class="hero-kicker">Faktura</p>
          <h3 class="hero-title">${escapeHtml(invoice.invoice_number || invoice.supplier || "Bez ÄŤĂ­sla")}</h3>
          <p class="hero-subtitle">${escapeHtml(invoice.supplier || "-")}</p>
        </div>
        <div class="hero-side">
          <span class="status-pill">${escapeHtml(invoice.status || "detected")}</span>
          <span class="chip">${escapeHtml(getProjectName(invoice.project_id))}</span>
        </div>
      </div>
      ${renderSummaryStrip([
        { label: "CelkovĂˇ ÄŤĂˇstka", value: formatCurrency(invoice.amount) },
        { label: "Splatnost", value: formatDate(invoice.due_date) },
        { label: "ZakĂˇzka", value: getProjectName(invoice.project_id) },
      ])}
      ${invoice.attachment_path ?`<div class="section-card"><a class="button button-secondary" href="${escapeHtml(invoice.attachment_path)}" target="_blank">OtevĹ™Ă­t PDF</a></div>` : ""}
      ${sourceEmail ?`<div class="section-card"><div class="panel-header"><div><h4>PĹŻvodnĂ­ e-mail</h4></div></div><pre class="text-block">${escapeHtml(`${sourceEmail.subject}\n${sourceEmail.sender}\n\n${sourceEmail.body}`)}</pre></div>` : ""}
    </div>
  `;
}

function renderProjectWorkspace() {
  const detail = state.projectDetail;
  if (!detail) return renderEmpty("Vyber zakĂˇzku ze seznamu nebo zaloĹľ novou.");
  const project = detail.item;
  const finance = detail.finance;
  const sectionTabs = PROJECT_SECTION_TABS.map(([key, label]) => `
    <button type="button" class="section-tab ${state.projectSection === key ?"is-active" : ""}" data-project-section="${key}">${escapeHtml(label)}</button>
  `).join("");

  let sectionBody = "";
  if (state.projectSection === "overview") {
    sectionBody = `
      <div class="section-card">
        <div class="panel-header">
          <div>
            <h4>Kontakty a nastavenĂ­</h4>
            <p>UloĹľenĂ­ probĂ­hĂˇ automaticky po zmÄ›nÄ› pole.</p>
          </div>
          <span class="autosave-badge autosave-${state.projectAutosaveStatus}">
            ${
              state.projectAutosaveStatus === "saving"
                ?"UklĂˇdĂˇmâ€¦"
                : state.projectAutosaveStatus === "saved"
                  ?"UloĹľeno"
                  : state.projectAutosaveStatus === "error"
                    ?"Chyba uloĹľenĂ­"
                    : "AutomatickĂ© uklĂˇdĂˇnĂ­"
            }
          </span>
        </div>
        <form id="project-update-form" class="compact-form is-dense" data-project-id="${project.id}">
          <div class="row">
            <input name="name" value="${escapeHtml(project.name)}" placeholder="NĂˇzev zakĂˇzky" required>
            <input name="code" value="${escapeHtml(project.code || "")}" placeholder="KĂłd zakĂˇzky">
          </div>
          <div class="row">
            <select name="status">${renderProjectStatusOptions(project.status)}</select>
            <select name="priority">${renderPriorityOptions(project.priority)}</select>
          </div>
          <div class="row">
            <input name="customer_name" value="${escapeHtml(project.customer_name || "")}" placeholder="ZĂˇkaznĂ­k">
            <input name="contact_person" value="${escapeHtml(project.contact_person || "")}" placeholder="KontaktnĂ­ osoba">
          </div>
          <div class="row">
            <input name="contact_email" value="${escapeHtml(project.contact_email || "")}" placeholder="E-mail">
            <input name="contact_phone" value="${escapeHtml(project.contact_phone || "")}" placeholder="Telefon">
          </div>
          <div class="row">
            <input name="planned_start_at" value="${escapeHtml(toDateTimeLocal(project.planned_start_at))}" type="datetime-local">
            <input name="planned_end_at" value="${escapeHtml(toDateTimeLocal(project.planned_end_at))}" type="datetime-local">
          </div>
          <textarea name="address" rows="2" placeholder="Adresa realizace">${escapeHtml(project.address || "")}</textarea>
          <div class="row row-textareas">
            <textarea name="description" rows="3" placeholder="Popis zakĂˇzky">${escapeHtml(project.description || "")}</textarea>
            <textarea name="notes" rows="3" placeholder="PoznĂˇmky k zakĂˇzce">${escapeHtml(project.notes || "")}</textarea>
          </div>
          <textarea name="internal_notes" rows="2" placeholder="InternĂ­ poznĂˇmky">${escapeHtml(project.internal_notes || "")}</textarea>
        </form>
      </div>
    `;
  }
  if (state.projectSection === "emails") {
    sectionBody = renderDataTable(
      ["PĹ™ijato", "OdesĂ­latel", "PĹ™edmÄ›t", "Kategorie", "Akce"],
      (detail.emails || []).map((email) => `
        <tr class="is-clickable ${emailStateClass(email)}" data-open-email="${escapeHtml(email.id)}">
          <td>${formatDate(email.received_at)}</td>
          <td>${escapeHtml(email.sender)}</td>
          <td>${escapeHtml(email.subject)}</td>
          <td>${escapeHtml(getEmailCategoryLabel(email.category))}</td>
          <td><button class="button button-secondary" type="button" data-open-email="${escapeHtml(email.id)}">OtevĹ™Ă­t</button></td>
        </tr>
      `),
      "ZakĂˇzka zatĂ­m nemĂˇ pĹ™iĹ™azenĂ© e-maily.",
    );
  }
  if (state.projectSection === "documents") {
    sectionBody = `
      <div class="section-card">
        <div class="panel-header"><div><h4>NahrĂˇt dokument nebo fotku</h4></div></div>
        <form id="project-document-form" class="compact-form" data-project-id="${project.id}" enctype="multipart/form-data">
          <div class="row">
            <input name="title" placeholder="NĂˇzev dokumentu">
            <select name="document_type">
              <option value="general">Dokument</option>
              <option value="photo">Fotografie</option>
              <option value="invoice">Faktura</option>
            </select>
          </div>
          <div class="row">
            <select name="worker_id"><option value="">Bez pracovnĂ­ka</option>${renderWorkerOptions()}</select>
            <input type="file" name="file" required>
          </div>
          <div class="toolbar"><button class="button button-primary" type="submit">NahrĂˇt dokument</button></div>
        </form>
      </div>
      ${renderDataTable(
        ["NĂˇzev", "Typ", "Vazba", "Soubor"],
        (detail.documents || []).map((doc) => `
          <tr>
            <td>${escapeHtml(doc.title || doc.name)}</td>
            <td>${escapeHtml(doc.document_type)}</td>
            <td>${escapeHtml(getWorkerName(doc.worker_id) || "-")}</td>
            <td><a class="button button-secondary" href="${escapeHtml(doc.url)}" target="_blank">OtevĹ™Ă­t</a></td>
          </tr>
        `),
        "ZatĂ­m bez dokumentĹŻ.",
      )}
    `;
  }
  if (state.projectSection === "tasks") {
    sectionBody = `
      <div class="section-card">
        <div class="panel-header">
          <div><h4>Úkoly k zakázce</h4><p>Nový úkol otevře kompaktní dialog místo trvalého formuláře.</p></div>
          <button class="button button-primary" type="button" data-open-task-dialog="${project.id}">Přidat úkol</button>
        </div>
      </div>
      ${renderDataTable(
        ["Název", "Termín", "Stav", "Pracovníci", "Akce"],
        (detail.tasks || []).map((task) => `
          <tr class="${taskStateClass(task)}">
            <td>${escapeHtml(task.title)}</td>
            <td>${formatDate(task.due_date)}</td>
            <td>${escapeHtml(getTaskStatusLabel(task.status))}</td>
            <td>${escapeHtml(getTaskWorkerNames(task))}</td>
            <td><button class="button button-secondary" type="button" data-open-task="${task.id}">OtevĹ™Ă­t</button></td>
          </tr>
        `),
        "ZatĂ­m bez ĂşkolĹŻ.",
      )}
    `;
  }
  if (state.projectSection === "worklogs") {
    sectionBody = `
      <div class="section-card">
        <div class="panel-header"><div><h4>Zapsat práci více pracovníkům</h4><p>Jedno datum, společná poznámka a více řádků pracovníků najednou.</p></div></div>
        <form id="project-worklog-form" class="compact-form" data-project-id="${project.id}">
          <div class="row">
            <input name="work_date" type="date" required>
            <textarea name="notes" rows="2" placeholder="Společná poznámka k práci"></textarea>
          </div>
          <div class="worklog-entry-grid worklog-entry-grid-head">
            <span>Pracovník</span>
            <span>Hodiny</span>
            <span>Sazba</span>
            <span>Materiál</span>
            <span>K výplatě</span>
          </div>
          ${Array.from({ length: 5 }, (_, index) => `
            <div class="worklog-entry-grid project-worklog-entry" data-row-index="${index}">
              <select name="worker_id_${index}">
                <option value="">Vyber pracovníka</option>
                ${renderWorkerOptions()}
              </select>
              <input name="hours_${index}" type="text" inputmode="decimal" placeholder="0">
              <input name="rate_${index}" type="text" inputmode="decimal" placeholder="Sazba" data-auto-rate="true">
              <input name="material_cost_${index}" type="text" inputmode="decimal" placeholder="0" value="0">
              <input name="payout_amount_${index}" type="text" inputmode="decimal" placeholder="Auto" data-auto-payout="true" readonly>
            </div>
          `).join("")}
          <div class="toolbar">
            <span class="selection-chip">K výplatě = hodiny × sazba + materiál.</span>
            <span class="toolbar-spacer"></span>
            <button class="button button-primary" type="submit">Zapsat hodiny</button>
          </div>
        </form>
      </div>
      ${renderDataTable(
        ["Datum", "Pracovník", "Hodiny", "Materiál", "K výplatě", "Proplaceno", "Akce"],
        (detail.work_logs || []).map((log) => `
          <tr class="${worklogStateClass(log)}">
            <td>${formatDate(log.work_date, false)}</td>
            <td>${escapeHtml(getWorkerName(log.worker_id))}</td>
            <td>${formatHours(log.hours)}</td>
            <td>${formatCurrency(log.material_cost)}</td>
            <td>${formatCurrency(getWorklogPayoutAmount(log))}</td>
            <td><input type="checkbox" data-worklog-paid-toggle="${log.id}" ${log.payment_status === "paid" ?"checked" : ""}></td>
            <td><button type="button" class="button button-danger button-small" data-delete-worklog="${log.id}">Smazat</button></td>
          </tr>
        `),
        "ZatĂ­m bez zapsanĂ˝ch hodin.",
      )}
    `;
  }

  return `
    <div class="detail-shell">
      <div class="hero-card">
        <div>
          <p class="hero-kicker">ZakĂˇzka</p>
          <h3 class="hero-title">${escapeHtml(project.name)}</h3>
          <p class="hero-subtitle">${escapeHtml(project.description || project.customer_name || "Bez popisu")}</p>
        </div>
        <div class="hero-side">
          <span class="status-pill">${escapeHtml(getProjectStatusLabel(project.status))}</span>
          <span class="chip">${escapeHtml(getPriorityLabel(project.priority))}</span>
          <span class="chip">${escapeHtml(project.customer_name || "Bez zĂˇkaznĂ­ka")}</span>
        </div>
      </div>
      <div class="toolbar">
        <button type="button" class="button button-danger" data-delete-project="${project.id}">Smazat zakĂˇzku</button>
      </div>
      ${renderSummaryStrip([
        { label: "PĹ™iĹ™azenĂ© e-maily", value: detail.emails?.length || 0 },
        { label: "Ăškoly", value: detail.tasks?.length || 0 },
        { label: "Dokumenty", value: detail.documents?.length || 0 },
        { label: "OdpracovĂˇno", value: formatHours(finance.labor_hours) },
        { label: "Stav", value: getProjectStatusLabel(project.status) },
      ])}
      <div class="timeline-card">
        <div class="panel-header"><div><h4>ÄŚasovĂˇ osa</h4><p>PoslednĂ­ dÄ›nĂ­ kolem zakĂˇzky, e-mailĹŻ, ĂşkolĹŻ, faktur a hodin.</p></div></div>
        ${renderTimeline(detail)}
      </div>
      <div class="section-tabs">${sectionTabs}</div>
      <div class="section-body">${sectionBody}</div>
    </div>
  `;
}

function renderDashboardView() {
  const counts = state.dashboard?.counts || {};
  const finance = state.dashboard?.finance || {};
  const totalHours = state.worklogs.reduce((sum, item) => sum + Number(item.hours || 0), 0);
  const monthKey = state.calendarMonth || monthStartKey();
  const selectedDateKey = state.selectedCalendarDate || toDateKey();
  const allEvents = getDashboardCalendarEvents();
  const visibleMonthEvents = allEvents.filter((event) => isSameMonth(event.startKey, monthKey) || isSameMonth(event.endKey, monthKey) || (event.startKey < monthKey && event.endKey > monthKey));
  const visibleWeekEvents = allEvents.filter((event) => {
    const weekStart = getWeekStartKey(selectedDateKey);
    const weekEnd = shiftDateKey(weekStart, 6);
    return event.startKey <= weekEnd && event.endKey >= weekStart;
  });
  const upcomingEvents = [...allEvents]
    .filter((event) => event.endKey >= toDateKey())
    .sort((a, b) => String(a.starts_at || "").localeCompare(String(b.starts_at || "")))
    .slice(0, 4);
  const calendarLabel = state.calendarMode === "week" ? "Akce v týdnu" : "Akce v měsíci";
  const calendarCount = state.calendarMode === "week" ? visibleWeekEvents.length : visibleMonthEvents.length;
  return `
    <section class="view">
      ${renderStatsGrid([
        { label: "Nezpracované e-maily", value: counts.unprocessed_emails || 0 },
        { label: "Otevřené úkoly", value: counts.open_tasks || 0 },
        { label: calendarLabel, value: calendarCount },
        { label: "K výplatě", value: formatCurrency(finance.unpaid_payout_total) },
      ])}
      <div class="dashboard-calendar-layout">
        <div class="panel dashboard-calendar-panel">
          <div class="panel-header dashboard-calendar-header">
            <div>
              <h3>Plán akcí</h3>
              <p>Velký přehled všech naplánovaných jednodenních i vícedenních akcí. Barvy odpovídají prioritě úkolu.</p>
            </div>
            <div class="calendar-nav">
              <div class="calendar-mode-toggle">
                <button type="button" class="button button-secondary ${state.calendarMode === "month" ? "is-active" : ""}" data-calendar-mode="month">Měsíc</button>
                <button type="button" class="button button-secondary ${state.calendarMode === "week" ? "is-active" : ""}" data-calendar-mode="week">Týden</button>
              </div>
              <button type="button" class="button button-secondary" data-calendar-nav="prev">←</button>
              <strong class="calendar-month-label">${
                state.calendarMode === "week"
                  ? `${escapeHtml(formatDate(getWeekStartKey(selectedDateKey), false))} – ${escapeHtml(formatDate(shiftDateKey(getWeekStartKey(selectedDateKey), 6), false))}`
                  : escapeHtml(formatMonthLabel(monthKey))
              }</strong>
              <button type="button" class="button button-secondary" data-calendar-nav="next">→</button>
              <button type="button" class="button button-primary" data-calendar-nav="today">Dnes</button>
            </div>
          </div>
          ${state.calendarMode === "week" ? renderCalendarWeekGrid(selectedDateKey) : renderCalendarMonthGrid(monthKey, selectedDateKey)}
        </div>
        <div class="dashboard-side-column">
          <div class="panel">
            <div class="panel-header">
              <div>
                <h3>${escapeHtml(new Intl.DateTimeFormat("cs-CZ", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(parseDateKey(selectedDateKey) || new Date()))}</h3>
                <p>Denní agenda s rychlým přechodem na konkrétní úkol.</p>
              </div>
            </div>
            ${renderCalendarAgenda(selectedDateKey)}
          </div>
          <div class="panel">
            <div class="panel-header"><div><h3>Souhrn práce a výplat</h3><p>Krátký provozní přehled bez zbytečného balastu.</p></div></div>
            ${renderSummaryStrip([
              { label: "Výkazů práce", value: counts.work_logs || 0 },
              { label: "Odpracováno", value: formatHours(totalHours) },
              { label: "Vyplaceno", value: formatCurrency(finance.paid_payout_total) },
              { label: "Materiál", value: formatCurrency(finance.material_total) },
            ])}
          </div>
          <div class="panel">
            <div class="panel-header"><div><h3>Nejbližší akce</h3><p>Co tě čeká v příštích dnech.</p></div></div>
            <div class="calendar-upcoming-list">
              ${upcomingEvents.length ? upcomingEvents.map((event) => `
                <button type="button" class="calendar-upcoming-item ${getPriorityClass(event.priority)}" data-open-task="${event.task_id}" title="${escapeHtml(getCalendarFullLabel(event))}">
                  <strong>${escapeHtml(getCalendarDisplayName(event, 34))}</strong>
                  ${event.task_title ? `<small>${escapeHtml(truncateText(event.task_title, 30))}</small>` : ""}
                  <span>${escapeHtml(formatDate(event.starts_at))}</span>
                </button>
              `).join("") : renderEmpty("Zatím bez dalších naplánovaných akcí.")}
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderInboxView() {
  const items = getInboxItems();
  const selected = items.find((entry) => `${entry.kind}:${entry.id}` === state.selectedInboxKey) || items[0] || null;
  const list = items.map((entry) => {
    const key = `${entry.kind}:${entry.id}`;
    if (entry.kind === "email") {
      return renderListItem({
        key,
        title: escapeHtml(entry.item.subject || "Bez pĹ™edmÄ›tu"),
        meta: `${formatDate(entry.item.received_at)} Â· ${escapeHtml(getEmailCategoryLabel(entry.item.category))}`,
        subtitle: escapeHtml(entry.item.sender),
        selected: state.selectedInboxKey === key || (!state.selectedInboxKey && key === `${selected?.kind}:${selected?.id}`),
        stateClass: emailStateClass(entry.item),
      });
    }
    return renderListItem({
      key,
      title: escapeHtml(entry.item.title),
      meta: `${formatDate(entry.item.due_date || entry.item.created_at)} Â· ${escapeHtml(getTaskStatusLabel(entry.item.status))}`,
      subtitle: escapeHtml(getProjectName(entry.item.project_id)),
      selected: state.selectedInboxKey === key || (!state.selectedInboxKey && key === `${selected?.kind}:${selected?.id}`),
      stateClass: taskStateClass(entry.item),
    });
  }).join("");

  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Fronta k rozhodnutĂ­</h3><p>NeroztĹ™Ă­dÄ›nĂ© e-maily a otevĹ™enĂ© Ăşkoly pohromadÄ›.</p></div></div>
        <div class="content-split">
          <div class="list-panel">
            <div class="selection-chip">PoloĹľek: ${items.length}</div>
            <div class="list-stack">${list || renderEmpty("Nic neÄŤekĂˇ na zpracovĂˇnĂ­.")}</div>
          </div>
          <div class="detail-panel">
            ${selected ?(selected.kind === "email" ?renderEmailDetail(selected.item) : renderTaskDetail(selected.item)) : renderEmpty("Nic k zobrazenĂ­.")}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderConversationDetail(detail) {
  if (!detail) return renderEmpty("Vyber konverzaci ze seznamu.");
  const emailIds = detail.emails.map((item) => item.id).join(",");
  const participants = (detail.item.participants || []).join(", ");
  return `
    <div class="detail-shell">
      <div class="hero-card">
        <div>
          <p class="hero-kicker">Konverzace</p>
          <h3 class="hero-title">${escapeHtml(detail.item.subject || "Bez pĹ™edmÄ›tu")}</h3>
          <p class="hero-subtitle">${escapeHtml(participants)}</p>
        </div>
        <div class="hero-side">
          <span class="status-pill">${detail.item.email_count} zprĂˇv</span>
          <span class="chip">${escapeHtml(getProjectName(detail.item.project_id))}</span>
        </div>
      </div>
      <div class="toolbar">
        <select id="conversation-project-select">${renderProjectOptions(detail.item.project_id)}</select>
        <button type="button" class="button button-secondary" data-conversation-assign="${escapeHtml(emailIds)}">PĹ™iĹ™adit celĂ© vlĂˇkno</button>
        <button type="button" class="button button-primary" data-create-project-from-email="${escapeHtml(detail.emails[0]?.id || "")}">VytvoĹ™it zakĂˇzku z vlĂˇkna</button>
      </div>
      ${detail.emails.map((email) => `
        <div class="section-card">
          <div class="panel-header"><div><h4>${escapeHtml(email.subject || "Bez pĹ™edmÄ›tu")}</h4><p>${escapeHtml(email.sender)} Â· ${formatDate(email.received_at)}</p></div></div>
          <pre class="text-block">${escapeHtml(email.body || "")}</pre>
        </div>
      `).join("")}
    </div>
  `;
}

function renderConversationsView() {
  const detail = state.conversationDetail;
  const list = state.conversations.map((conv) => renderListItem({
    key: `conversation:${conv.id}`,
    title: escapeHtml(conv.subject || "Bez pĹ™edmÄ›tu"),
    meta: `${formatDate(conv.latest_received_at)} Â· ${conv.email_count} zprĂˇv`,
    subtitle: escapeHtml((conv.participants || []).join(", ")),
    selected: conv.id === state.selectedConversationId,
    stateClass: conv.status === "confirmed" ?"ok" : "attention",
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Konverzace</h3><p>VlĂˇkna podle Gmail threadĹŻ, ne jednotlivĂ© izolovanĂ© e-maily.</p></div></div>
        <div class="content-split">
          <div class="list-panel"><div class="list-stack">${list || renderEmpty("Ĺ˝ĂˇdnĂ© konverzace.")}</div></div>
          <div class="detail-panel">${renderConversationDetail(detail)}</div>
        </div>
      </div>
    </section>
  `;
}

function renderEmailsView() {
  const emails = getFilteredEmails();
  const selected = emails.find((email) => email.id === state.selectedEmailId) || emails[0] || null;
  const hasBulkSelection = state.selectedEmailIds.size > 0;
  const list = emails.map((email) => renderListItem({
    key: `email:${email.id}`,
    title: escapeHtml(email.subject || "Bez předmětu"),
    meta: `${formatDate(email.received_at)} · ${escapeHtml(getEmailCategoryLabel(email.category))}`,
    subtitle: escapeHtml(email.sender),
    selected: selected?.id === email.id,
    stateClass: emailStateClass(email),
    checkbox: `<input type="checkbox" data-select-email="${escapeHtml(email.id)}" ${state.selectedEmailIds.has(email.id) ?"checked" : ""}>`,
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Všechny e-maily</h3><p>Kompletní seznam přijatých zpráv s hromadnou triáží.</p></div></div>
        <div class="toolbar">
          <input id="email-search" value="${escapeHtml(state.emailSearch)}" placeholder="Hledat v předmětu, odesílateli nebo textu">
          <select id="email-category-filter">
            <option value="all" ${state.emailCategoryFilter === "all" ? "selected" : ""}>Vše</option>
            <option value="unresolved" ${state.emailCategoryFilter === "unresolved" ? "selected" : ""}>Jen neroztříděné</option>
            ${Object.entries(EMAIL_CATEGORY_LABELS).map(([value, label]) => `<option value="${value}" ${state.emailCategoryFilter === value ?"selected" : ""}>${escapeHtml(label)}</option>`).join("")}
          </select>
          <span class="selection-chip">Vybráno: ${state.selectedEmailIds.size}</span>
          ${hasBulkSelection ?`
            <span class="toolbar-spacer"></span>
            <span class="selection-chip">Hromadné akce</span>
            <select id="bulk-email-project-select">${renderProjectOptions()}</select>
            <button type="button" class="button button-secondary" data-bulk-email-action="create_task">Na úkol</button>
            <button type="button" class="button button-secondary" data-bulk-email-action="assign_project">K zakázce</button>
            <button type="button" class="button button-secondary" data-bulk-email-action="mark_invoice">Faktura</button>
            <button type="button" class="button button-secondary" data-bulk-email-action="ignore">Ignorovat</button>
            <button type="button" class="button button-secondary" data-bulk-email-action="return_unprocessed">Vrátit</button>
            <button type="button" class="button button-danger" data-bulk-email-action="archive">Archivovat</button>
          ` : ""}
        </div>
        <div class="content-split">
          <div class="list-panel"><div class="list-stack">${list || renderEmpty("Žádné e-maily pro tento filtr.")}</div></div>
          <div class="detail-panel">${renderEmailDetail(selected)}</div>
        </div>
      </div>
    </section>
  `;
}

function renderProjectsView() {
  const list = state.projects.map((project) => renderListItem({
    key: `project:${project.id}`,
    title: escapeHtml(project.name),
    meta: `${escapeHtml(getProjectStatusLabel(project.status))} Â· ${escapeHtml(getPriorityLabel(project.priority))}`,
    subtitle: escapeHtml(project.customer_name || project.address || "Bez zĂˇkaznĂ­ka"),
    selected: project.id === state.selectedProjectId,
    stateClass: ["done", "closed", "archived"].includes(project.status) ?"ok" : "attention",
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>ZakĂˇzky</h3><p>ZakĂˇzka je hlavnĂ­ pracovnĂ­ prostor. E-maily, dokumenty, Ăşkoly i hodiny jsou pod jednou stĹ™echou.</p></div></div>
        <div class="content-split">
          <div class="list-panel">
            <div class="toolbar"><span class="selection-chip">ZakĂˇzek: ${state.projects.length}</span><span class="toolbar-spacer"></span><button type="button" class="button button-primary" data-open-project-dialog>NovĂˇ zakĂˇzka</button></div>
            <div class="list-stack">${list || renderEmpty("ZatĂ­m ĹľĂˇdnĂ© zakĂˇzky.")}</div>
          </div>
          <div class="detail-panel">${renderProjectWorkspace()}</div>
        </div>
      </div>
    </section>
  `;
}

function renderTasksView() {
  const selected = state.tasks.find((item) => item.id === state.selectedTaskId) || state.tasks[0] || null;
  const list = state.tasks.map((task) => renderListItem({
    key: `task:${task.id}`,
    title: escapeHtml(task.title),
    meta: `${formatDate(task.due_date)} Â· ${escapeHtml(getTaskStatusLabel(task.status))}`,
    subtitle: escapeHtml(getProjectName(task.project_id)),
    selected: selected?.id === task.id,
    stateClass: taskStateClass(task),
    checkbox: `<input type="checkbox" data-select-task="${task.id}" ${state.selectedTaskIds.has(task.id) ?"checked" : ""}>`,
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Ăškoly</h3><p>HromadnĂ© dokonÄŤenĂ­, archivace i pĹ™iĹ™azenĂ­ k zakĂˇzce.</p></div></div>
        <div class="toolbar">
          <button class="button button-primary" type="button" data-open-task-dialog>Přidat úkol</button>
          <span class="selection-chip">Nový úkol se otevře v dialogu a nezvětšuje layout stránky.</span>
          <span class="toolbar-spacer"></span>
          <span class="selection-chip">VybrĂˇno: ${state.selectedTaskIds.size}</span>
          <select id="bulk-task-project-select">${renderProjectOptions()}</select>
          <button type="button" class="button button-secondary" data-bulk-task-action="assign_project">K zakĂˇzce</button>
          <button type="button" class="button button-primary" data-bulk-task-action="complete">DokonÄŤit</button>
          <button type="button" class="button button-danger" data-bulk-task-action="archive">Archivovat</button>
        </div>
        <div class="content-split">
          <div class="list-panel"><div class="list-stack">${list || renderEmpty("Ĺ˝ĂˇdnĂ© Ăşkoly.")}</div></div>
          <div class="detail-panel">${renderTaskDetail(selected)}</div>
        </div>
      </div>
    </section>
  `;
}

function renderInvoicesView() {
  const selected = state.invoices.find((item) => item.id === state.selectedInvoiceId) || state.invoices[0] || null;
  const list = state.invoices.map((invoice) => renderListItem({
    key: `invoice:${invoice.id}`,
    title: escapeHtml(invoice.invoice_number || invoice.supplier || "Faktura"),
    meta: `${formatDate(invoice.created_at)} Â· ${formatCurrency(invoice.amount)}`,
    subtitle: escapeHtml(getProjectName(invoice.project_id)),
    selected: selected?.id === invoice.id,
    stateClass: invoiceStateClass(invoice),
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Faktury</h3><p>JednoduchĂ˝ pĹ™ehled ÄŤĂˇstek, splatnosti a vazby na zdrojovĂ˝ e-mail.</p></div></div>
        <div class="content-split">
          <div class="list-panel"><div class="list-stack">${list || renderEmpty("Ĺ˝ĂˇdnĂ© faktury.")}</div></div>
          <div class="detail-panel">${renderInvoiceDetail(selected)}</div>
        </div>
      </div>
    </section>
  `;
}

function renderWorkersView() {
  const selected = state.workers.find((worker) => worker.id === state.selectedWorkerId) || state.workers[0] || null;
  const list = state.workers.map((worker) => renderListItem({
    key: `worker:${worker.id}`,
    title: escapeHtml(worker.full_name),
    meta: `${escapeHtml(worker.role || "Pracovnik")} · ${escapeHtml(worker.status || "active")}`,
    subtitle: escapeHtml(worker.email || worker.phone || "Bez kontaktu"),
    selected: selected?.id === worker.id,
    stateClass: worker.status === "active" ?"attention" : "ok",
  })).join("");
  const summary = selected
    ?state.worklogSummary.filter((item) => item.worker_id === selected.id)
    : [];
  const totalHours = summary.reduce((sum, item) => sum + Number(item.hours || 0), 0);
  const totalPaid = summary.reduce((sum, item) => sum + Number(item.paid_total || 0), 0);
  const totalUnpaid = summary.reduce((sum, item) => sum + Number(item.unpaid_total || 0), 0);
  const totalPayout = summary.reduce((sum, item) => sum + Number(item.payout_total || 0), 0);
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Pracovníci</h3><p>Karta pracovníka, sazby a přehled práce po zakázkách.</p></div></div>
        <div class="content-split">
          <div class="list-panel">
            <div class="section-card">
              <form id="worker-form" class="compact-form">
                <div class="row">
                  <input name="full_name" placeholder="Jméno pracovníka" required>
                  <input name="role" placeholder="Role">
                </div>
                <div class="row">
                  <input name="email" placeholder="E-mail">
                  <input name="phone" placeholder="Telefon">
                </div>
                <div class="row">
                  <input name="hourly_rate" type="text" inputmode="decimal" placeholder="Hodinová sazba">
                  <input name="payout_rate" type="text" inputmode="decimal" placeholder="Výplatní sazba">
                </div>
                <div class="toolbar"><button class="button button-primary" type="submit">Přidat pracovníka</button></div>
              </form>
            </div>
            <div class="list-stack">${list || renderEmpty("Zatím žádní pracovníci.")}</div>
          </div>
          <div class="detail-panel">
            ${selected ?`
              <div class="detail-shell">
                <div class="hero-card">
                  <div>
                    <p class="hero-kicker">Pracovník</p>
                    <h3 class="hero-title">${escapeHtml(selected.full_name)}</h3>
                    <p class="hero-subtitle">${escapeHtml(selected.role || "Bez role")} · ${escapeHtml(selected.email || selected.phone || "Bez kontaktu")}</p>
                  </div>
                  <div class="hero-side">
                    <span class="chip">${selected.hourly_rate ?`${formatCurrency(selected.hourly_rate)}/h` : "Bez hodinové sazby"}</span>
                    <span class="chip">${selected.payout_rate ?`${formatCurrency(selected.payout_rate)}/h` : "Bez výplatní sazby"}</span>
                  </div>
                </div>
                <div class="toolbar">
                  <button type="button" class="button button-danger" data-delete-worker="${selected.id}">Smazat pracovníka</button>
                </div>
                <div class="section-card">
                  <div class="panel-header"><div><h4>Upravit pracovníka</h4><p>Změň kontakt, sazby nebo stav pracovníka.</p></div></div>
                  <form id="worker-update-form" class="compact-form" data-worker-id="${selected.id}">
                    <div class="row">
                      <input name="full_name" value="${escapeHtml(selected.full_name || "")}" placeholder="Jméno pracovníka" required>
                      <input name="role" value="${escapeHtml(selected.role || "")}" placeholder="Role">
                    </div>
                    <div class="row">
                      <input name="email" value="${escapeHtml(selected.email || "")}" placeholder="E-mail">
                      <input name="phone" value="${escapeHtml(selected.phone || "")}" placeholder="Telefon">
                    </div>
                    <div class="row">
                      <input name="hourly_rate" type="text" inputmode="decimal" value="${escapeHtml(selected.hourly_rate ?? "")}" placeholder="Hodinová sazba">
                      <input name="payout_rate" type="text" inputmode="decimal" value="${escapeHtml(selected.payout_rate ?? "")}" placeholder="Výplatní sazba">
                    </div>
                    <div class="row">
                      <select name="status">${renderWorkerStatusOptions(selected.status || "active")}</select>
                    </div>
                    <div class="toolbar"><button class="button button-primary" type="submit">Uložit změny</button></div>
                  </form>
                </div>
                ${renderSummaryStrip([
                  { label: "Odpracováno celkem", value: formatHours(totalHours) },
                  { label: "Vyplaceno celkem", value: formatCurrency(totalPaid) },
                  { label: "Neproplaceno", value: formatCurrency(totalUnpaid) },
                  { label: "Celkem k výplatě", value: formatCurrency(totalPayout) },
                ])}
                ${renderDataTable(
                  ["Zakázka", "Hodiny", "Celkem", "Proplaceno", "Neproplaceno"],
                  summary.map((item) => `
                    <tr>
                      <td>${escapeHtml(item.project_name)}</td>
                      <td>${formatHours(item.hours)}</td>
                      <td>${formatCurrency(item.payout_total)}</td>
                      <td>${formatCurrency(item.paid_total)}</td>
                      <td>${formatCurrency(item.unpaid_total)}</td>
                    </tr>
                  `),
                  "Pracovník zatím nemá zapsanou práci.",
                )}
              </div>
            ` : renderEmpty("Vyber pracovníka ze seznamu.")}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderWorklogsView() {
  const items = getFilteredWorklogs();
  const totalHours = items.reduce((sum, item) => sum + Number(item.hours || 0), 0);
  const totalPayout = items.reduce((sum, item) => sum + getWorklogPayoutAmount(item), 0);
  const unpaid = items.reduce((sum, item) => sum + (item.payment_status === "paid" ?0 : getWorklogPayoutAmount(item)), 0);
  const paid = items.reduce((sum, item) => sum + (item.payment_status === "paid" ?getWorklogPayoutAmount(item) : 0), 0);
  const projectId = state.worklogProjectFilter ? Number(state.worklogProjectFilter) : null;
  const projectSummaries = projectId
    ? state.worklogSummary.filter((item) => item.project_id === projectId && (!state.worklogWorkerFilter || String(item.worker_id) === state.worklogWorkerFilter))
    : [];
  const selectedSummary = projectSummaries.find((item) => `${item.project_id}:${item.worker_id}` === state.selectedWorklogSummaryKey)
    || projectSummaries[0]
    || null;
  const summaryWorkerItems = selectedSummary
    ? items.filter((item) => item.project_id === selectedSummary.project_id && item.worker_id === selectedSummary.worker_id)
    : [];
  const selected = items.find((item) => item.id === state.selectedWorklogId) || items[0] || null;
  const focusWorkerId = selectedSummary
    ? selectedSummary.worker_id
    : state.worklogWorkerFilter
      ? Number(state.worklogWorkerFilter)
      : selected?.worker_id || null;
  const workerItems = selectedSummary
    ? summaryWorkerItems
    : focusWorkerId
      ? items.filter((item) => item.worker_id === focusWorkerId)
      : [];
  const workerHours = workerItems.reduce((sum, item) => sum + Number(item.hours || 0), 0);
  const workerPayout = workerItems.reduce((sum, item) => sum + getWorklogPayoutAmount(item), 0);
  const workerUnpaid = workerItems.reduce((sum, item) => sum + (item.payment_status === "paid" ? 0 : getWorklogPayoutAmount(item)), 0);
  const workerPaid = workerItems.reduce((sum, item) => sum + (item.payment_status === "paid" ? getWorklogPayoutAmount(item) : 0), 0);
  return `
    <section class="view">
      ${renderSummaryStrip([
        { label: "Zobrazené výkazy", value: items.length },
        { label: "Odpracované hodiny", value: formatHours(totalHours) },
        { label: "Celkem k výplatě", value: formatCurrency(totalPayout) },
        { label: "Neproplaceno", value: formatCurrency(unpaid) },
        { label: "Proplaceno", value: formatCurrency(paid) },
      ])}
      <div class="panel">
        <div class="panel-header"><div><h3>Výkazy práce</h3><p>Tabulkový přehled, filtry a detail bez zbytečně velkých karet.</p></div></div>
        <div class="toolbar">
          <select id="worklog-worker-filter"><option value="">Všichni pracovníci</option>${renderWorkerOptions(Number(state.worklogWorkerFilter) || null)}</select>
          <select id="worklog-project-filter"><option value="">Všechny zakázky</option>${renderProjectOptions(Number(state.worklogProjectFilter) || null)}</select>
          <select id="worklog-payment-filter">
            <option value="all" ${state.worklogPaymentFilter === "all" ?"selected" : ""}>Vše</option>
            <option value="unpaid" ${state.worklogPaymentFilter === "unpaid" ?"selected" : ""}>Jen neproplacené</option>
            <option value="paid" ${state.worklogPaymentFilter === "paid" ?"selected" : ""}>Jen proplacené</option>
          </select>
        </div>
        ${projectId ? `
          ${renderSummaryStrip([
            { label: "Zakázka", value: getProjectName(projectId) },
            { label: "Pracovníků", value: projectSummaries.length },
            { label: "Celkem hodin", value: formatHours(projectSummaries.reduce((sum, item) => sum + Number(item.hours || 0), 0)) },
            { label: "Celkem k výplatě", value: formatCurrency(projectSummaries.reduce((sum, item) => sum + Number(item.payout_total || 0), 0)) },
          ])}
          ${renderDataTable(
            ["Pracovník", "Zápisů", "Hodiny", "K výplatě", "Neproplaceno", "Proplaceno"],
            projectSummaries.map((item) => `
              <tr class="is-clickable ${selectedSummary && selectedSummary.worker_id === item.worker_id && selectedSummary.project_id === item.project_id ? "is-selected-row" : ""}" data-worklog-summary="${item.project_id}:${item.worker_id}">
                <td>${escapeHtml(item.worker_name)}</td>
                <td>${escapeHtml(item.entry_count)}</td>
                <td>${formatHours(item.hours)}</td>
                <td>${formatCurrency(item.payout_total)}</td>
                <td>${formatCurrency(item.unpaid_total)}</td>
                <td>${formatCurrency(item.paid_total)}</td>
              </tr>
            `),
            "Pro tuto zakázku zatím nejsou zapsané žádné hodiny.",
          )}
        ` : renderDataTable(
          ["Datum", "Pracovník", "Zakázka", "Hodiny", "Vedlejší výdaj", "K výplatě", "Proplaceno", "Akce"],
          items.map((item) => `
            <tr class="is-clickable ${worklogStateClass(item)}" data-worklog-id="${item.id}">
              <td>${formatDate(item.work_date, false)}</td>
              <td>${escapeHtml(getWorkerName(item.worker_id))}</td>
              <td>${escapeHtml(getProjectName(item.project_id))}</td>
              <td>${formatHours(item.hours)}</td>
              <td>${formatCurrency(item.material_cost)}</td>
              <td>${formatCurrency(getWorklogPayoutAmount(item))}</td>
              <td><input type="checkbox" data-worklog-paid-toggle="${item.id}" ${item.payment_status === "paid" ?"checked" : ""}></td>
              <td><button type="button" class="button button-danger button-small" data-delete-worklog="${item.id}">Smazat</button></td>
            </tr>
          `),
          "Žádné výkazy pro tento filtr.",
        )}
      </div>
      <div class="panel">
        <div class="panel-header"><div><h3>${projectId ? "Rozpad práce pracovníka" : "Práce pracovníka"}</h3><p>${projectId ? "Po kliknutí na pracovníka vidíš jednotlivé dny, kdy na zakázce dělal." : "Přehled všech zapsaných hodin vybraného pracovníka včetně stavu proplacení."}</p></div></div>
        ${focusWorkerId ? `
          ${renderSummaryStrip([
            { label: "Pracovník", value: getWorkerName(focusWorkerId) },
            { label: "Zakázka", value: selectedSummary ? getProjectName(selectedSummary.project_id) : "Všechny zakázky" },
            { label: "Zápisů", value: workerItems.length },
            { label: "Odpracováno", value: formatHours(workerHours) },
            { label: "Celkem k výplatě", value: formatCurrency(workerPayout) },
            { label: "Neproplaceno", value: formatCurrency(workerUnpaid) },
            { label: "Proplaceno", value: formatCurrency(workerPaid) },
          ])}
          ${selectedSummary ? `
            <div class="toolbar">
              ${workerUnpaid > 0
                ? `<button type="button" class="button button-primary" data-project-worklog-pay="${selectedSummary.project_id}" data-worker-id="${selectedSummary.worker_id}" data-paid="true">Proplatit celou zakázku</button>`
                : `<button type="button" class="button button-secondary" data-project-worklog-pay="${selectedSummary.project_id}" data-worker-id="${selectedSummary.worker_id}" data-paid="false">Vrátit celou zakázku na neproplaceno</button>`}
            </div>
          ` : ""}
          ${renderDataTable(
            ["Datum", "Zakázka", "Hodiny", "Vedlejší výdaj", "K výplatě", "Stav", "Akce"],
            workerItems.map((item) => `
              <tr class="${worklogStateClass(item)}">
                <td>${formatDate(item.work_date, false)}</td>
                <td>${escapeHtml(getProjectName(item.project_id))}</td>
                <td>${formatHours(item.hours)}</td>
                <td>${formatCurrency(item.material_cost)}</td>
                <td>${formatCurrency(getWorklogPayoutAmount(item))}</td>
                <td>${escapeHtml(getPaymentStatusLabel(item.payment_status))}</td>
                <td><button type="button" class="button button-danger button-small" data-delete-worklog="${item.id}">Smazat</button></td>
              </tr>
            `),
            selectedSummary
              ? "Vybraný pracovník zatím nemá na této zakázce žádné zapsané dny."
              : "Vybraný pracovník zatím nemá žádné výkazy pro tento filtr.",
          )}
        ` : renderEmpty(projectId ? "Vyber nahoře zakázku a klikni na konkrétního pracovníka." : "Vyber pracovníka filtrem nahoře nebo klikni na některý výkaz.")}
      </div>
    </section>
  `;
}

function renderWorkerPortalView() {
  const latestLogs = [...state.worklogs].sort((a, b) => (b.work_date || "").localeCompare(a.work_date || "")).slice(0, 8);
  const defaultWorkerId = state.currentUser?.worker_id || "";
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Jednoduchý zápis práce</h3><p>Pracovník vidí všechny zakázky, zapíše hodiny a vedlejší výdaj. K výplatě se dopočítá automaticky podle profilu.</p></div></div>
        <form id="worker-portal-form" class="compact-form">
          <div class="row">
            <select name="worker_id" required><option value="">Vyber pracovníka</option>${renderWorkerOptions()}</select>
            <select name="project_id" required>${renderProjectOptions()}</select>
          </div>
          <div class="row">
            <input name="work_date" type="date" required>
            <input name="hours" type="text" inputmode="decimal" placeholder="Hodiny" required>
          </div>
          <div class="row">
            <input name="material_cost" type="text" inputmode="decimal" placeholder="Vedlejší výdaj Kč" value="0">
            <input name="rate" type="hidden" data-auto-rate="true">
          </div>
          <div class="row">
            <input name="payout_amount" type="text" inputmode="decimal" placeholder="K výplatě Kč" data-auto-payout="true" readonly>
            <div class="field-note">K výplatě = hodiny × sazba z profilu + vedlejší výdaj.</div>
          </div>
          <textarea name="notes" rows="3" placeholder="Krátká poznámka k odvedené práci"></textarea>
          <div class="toolbar"><button class="button button-primary" type="submit">Zapsat práci</button></div>
        </form>
      </div>
      <div class="panel">
        <div class="panel-header"><div><h3>Poslední zápisy</h3></div></div>
        ${renderDataTable(
          ["Datum", "Pracovník", "Zakázka", "Hodiny", "Stav"],
          latestLogs.map((item) => `
            <tr>
              <td>${formatDate(item.work_date, false)}</td>
              <td>${escapeHtml(getWorkerName(item.worker_id))}</td>
              <td>${escapeHtml(getProjectName(item.project_id))}</td>
              <td>${formatHours(item.hours)}</td>
              <td>${escapeHtml(getPaymentStatusLabel(item.payment_status))}</td>
            </tr>
          `),
          "Zatím bez zápisů práce.",
        )}
      </div>
    </section>
  `;
}

function renderArchiveView() {
  const items = getArchiveItems();
  const selected = items.find((item) => item.key === state.selectedArchiveKey) || items[0] || null;
  const list = items.map((entry) => renderListItem({
    key: entry.key,
    title: escapeHtml(entry.kind === "email" ?entry.item.subject : entry.item.title),
    meta: `${entry.kind === "email" ?"E-mail" : "Ăškol"} Â· ${formatDate(entry.sort)}`,
    subtitle: escapeHtml(entry.kind === "email" ?entry.item.sender : getProjectName(entry.item.project_id)),
    selected: selected?.key === entry.key,
    stateClass: "ok",
  })).join("");
  const detail = selected?.kind === "email"
    ?renderEmailDetail({ ...selected.item, status: "archived" })
    : selected?.kind === "task"
      ?renderTaskDetail(selected.item)
      : renderEmpty("Archiv je prĂˇzdnĂ˝.");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Archiv</h3><p>OdloĹľenĂ© e-maily a hotovĂ© nebo archivovanĂ© Ăşkoly.</p></div></div>
        <div class="content-split">
          <div class="list-panel"><div class="list-stack">${list || renderEmpty("Archiv je prĂˇzdnĂ˝.")}</div></div>
          <div class="detail-panel">
            ${selected ?detail : renderEmpty("Archiv je prĂˇzdnĂ˝.")}
            ${selected ?`<div class="toolbar">${selected.kind === "email" ?`<button type="button" class="button button-secondary" data-email-action="restore" data-email-id="${escapeHtml(selected.item.id)}">Obnovit e-mail</button>` : `<button type="button" class="button button-secondary" data-task-action="reopen" data-task-id="${selected.item.id}">Obnovit Ăşkol</button>`}</div>` : ""}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderCurrentView() {
  switch (state.activeView) {
    case "dashboard": return renderDashboardView();
    case "inbox": return renderInboxView();
    case "conversations": return renderConversationsView();
    case "emails": return renderEmailsView();
    case "projects": return renderProjectsView();
    case "tasks": return renderTasksView();
    case "users": return renderUsersView();
    case "invoices": return renderInvoicesView();
    case "workers": return renderWorkersView();
    case "worklogs": return renderWorklogsView();
    case "workerPortal": return renderWorkerPortalView();
    case "archive": return renderArchiveView();
    default: return renderDashboardView();
  }
}

function renderProjectDialog() {
  if (!projectDialog) return;
  projectDialog.innerHTML = normalizeCzechText(`
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h3>NovĂˇ zakĂˇzka</h3>
          <p>RychlĂ© zaloĹľenĂ­. Detail doplnĂ­Ĺˇ potom pĹ™Ă­mo v kartÄ› zakĂˇzky.</p>
        </div>
        <button class="button button-secondary" type="button" data-close-project-dialog>ZavĹ™Ă­t</button>
      </div>
      <form id="project-form" class="dialog-form">
        <div class="row">
          <input name="name" placeholder="NĂˇzev zakĂˇzky" required>
          <input name="customer_name" placeholder="ZĂˇkaznĂ­k">
        </div>
        <div class="row">
          <input name="contact_person" placeholder="KontaktnĂ­ osoba">
          <input name="contact_email" placeholder="E-mail">
        </div>
        <div class="row">
          <input name="contact_phone" placeholder="Telefon">
          <input name="code" placeholder="KĂłd zakĂˇzky">
        </div>
        <div class="row">
          <select name="priority">${renderPriorityOptions("normal")}</select>
          <select name="status">${renderProjectStatusOptions("new")}</select>
        </div>
        <textarea name="address" rows="2" placeholder="Adresa realizace"></textarea>
        <textarea name="description" rows="3" placeholder="StruÄŤnĂ˝ popis zakĂˇzky"></textarea>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" data-close-project-dialog>ZruĹˇit</button>
          <button class="button button-primary" type="submit">VytvoĹ™it zakĂˇzku</button>
        </div>
      </form>
    </div>
  `);
}

function renderEmailDialog() {
  if (!emailDialog) return;
  const email = state.emails.find((item) => item.id === state.modalEmailId)
    || state.projectDetail?.emails?.find((item) => item.id === state.modalEmailId)
    || null;

  if (!email) {
    emailDialog.innerHTML = "";
    return;
  }

  emailDialog.innerHTML = normalizeCzechText(`
    <div class="modal-card modal-card-wide">
      <div class="modal-header">
        <div>
          <h3>Detail e-mailu</h3>
          <p>${escapeHtml(email.subject || "Bez pĹ™edmÄ›tu")}</p>
        </div>
        <button class="button button-secondary" type="button" data-close-email-dialog>ZavĹ™Ă­t</button>
      </div>
      ${renderEmailDetail(email)}
    </div>
  `);
}

function renderTaskDialog() {
  if (!taskDialog) return;
  const projectId = state.modalTaskProjectId ?Number(state.modalTaskProjectId) : null;
  const project = projectId ?state.projects.find((item) => item.id === projectId) || null : null;

  taskDialog.innerHTML = normalizeCzechText(`
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h3>${project ? "Přidat úkol k zakázce" : "Přidat úkol"}</h3>
          <p>${project ? escapeHtml(project.name) : "Nový úkol můžeš rovnou navázat na zakázku a pracovníky."}</p>
        </div>
        <button class="button button-secondary" type="button" data-close-task-dialog>Zavřít</button>
      </div>
      <form id="${project ? "project-task-form" : "task-form"}" class="dialog-form" ${project ? `data-project-id="${project.id}"` : ""}>
        ${project ? "" : `
          <div class="row">
            <input name="title" placeholder="Název úkolu" required>
            <select name="project_id">${renderProjectOptions()}</select>
          </div>
        `}
        ${project ? `
          <div class="row">
            <input name="title" placeholder="Název úkolu" required>
            <input name="due_date" type="datetime-local">
          </div>
        ` : `
          <div class="row">
            <input name="due_date" type="datetime-local">
            <select name="priority">${renderPriorityOptions("normal")}</select>
          </div>
        `}
        ${project ? `
          <div class="row">
            <select name="priority">${renderPriorityOptions("normal")}</select>
            <select name="assigned_worker_ids" multiple size="4">${renderWorkerMultiOptions()}</select>
          </div>
        ` : `
          <div class="row">
            <select name="assigned_worker_ids" multiple size="4">${renderWorkerMultiOptions()}</select>
            <input name="estimated_hours" type="number" min="0" step="0.5" placeholder="Odhad hodin">
          </div>
        `}
        ${project ? `
          <div class="row">
            <input name="estimated_hours" type="number" step="0.25" min="0" placeholder="Odhad hodin">
            <div></div>
          </div>
        ` : ""}
        <textarea name="description" rows="4" placeholder="Popis úkolu"></textarea>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" data-close-task-dialog>Zrušit</button>
          <button class="button button-primary" type="submit">Přidat úkol</button>
        </div>
      </form>
    </div>
  `);
}

function renderTaskFromEmailDialog() {
  if (!taskFromEmailDialog) return;
  const email = state.emails.find((item) => item.id === state.modalTaskEmailId)
    || state.projectDetail?.emails?.find((item) => item.id === state.modalTaskEmailId)
    || null;

  if (!email) {
    taskFromEmailDialog.innerHTML = "";
    return;
  }

  const defaultProjectId = email.project_ids?.[0] || email.project_id || null;
  taskFromEmailDialog.innerHTML = normalizeCzechText(`
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h3>Vytvořit úkol z e-mailu</h3>
          <p>${escapeHtml(email.subject || "Bez předmětu")}</p>
        </div>
        <button class="button button-secondary" type="button" data-close-task-from-email-dialog>Zavřít</button>
      </div>
      <form id="task-from-email-form" class="dialog-form" data-email-id="${escapeHtml(email.id)}">
        <div class="row">
          <input name="title" value="${escapeHtml(email.subject || "")}" placeholder="Název úkolu" required>
          <select name="priority">${renderPriorityOptions(email.priority || "normal")}</select>
        </div>
        <div class="row">
          <input name="due_date" type="datetime-local" placeholder="Termín splnění">
          <select name="project_id">${renderProjectOptions(defaultProjectId)}</select>
        </div>
        <div class="row">
          <select name="assigned_worker_ids" multiple size="4">${renderWorkerMultiOptions()}</select>
          <input name="estimated_hours" type="number" step="0.5" min="0" placeholder="Odhad hodin">
        </div>
        <textarea name="description" rows="8" placeholder="Popis úkolu">${escapeHtml(email.body || "")}</textarea>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" data-close-task-from-email-dialog>Zrušit</button>
          <button class="button button-primary" type="submit">Vytvořit úkol</button>
        </div>
      </form>
    </div>
  `);
}

function renderPasswordDialog() {
  if (!passwordDialog) return;
  passwordDialog.innerHTML = normalizeCzechText(`
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h3>Změna hesla</h3>
          <p>Zadej současné a nové heslo.</p>
        </div>
        <button class="button button-secondary" type="button" data-close-password-dialog>Zavřít</button>
      </div>
      <form id="password-form" class="dialog-form">
        <input name="current_password" type="password" placeholder="Současné heslo" required autocomplete="current-password">
        <input name="new_password" type="password" placeholder="Nové heslo" required autocomplete="new-password">
        <div class="modal-actions">
          <button class="button button-secondary" type="button" data-close-password-dialog>Zrušit</button>
          <button class="button button-primary" type="submit">Uložit heslo</button>
        </div>
      </form>
    </div>
  `);
}

function renderUsersView() {
  const selected = state.users.find((item) => item.id === state.selectedUserId) || state.users[0] || null;
  const list = state.users.map((user) => renderListItem({
    key: `user:${user.id}`,
    title: escapeHtml(user.full_name),
    meta: `${escapeHtml(user.role)} · ${escapeHtml(user.status)}`,
    subtitle: escapeHtml(user.email || "Bez loginu"),
    selected: selected?.id === user.id,
    stateClass: user.status === "active" ? "attention" : "ok",
  })).join("");
  return `
    <section class="view">
      <div class="panel">
        <div class="panel-header"><div><h3>Uživatelé</h3><p>Vlastník spravuje přístupy, role a vazby na pracovníky.</p></div></div>
        <div class="content-split">
          <div class="list-panel">
            <div class="section-card">
              <form id="user-form" class="compact-form">
                <div class="row">
                  <input name="full_name" placeholder="Jméno uživatele" required>
                  <input name="email" placeholder="Login" required>
                </div>
                <div class="row">
                  <input name="password" type="password" placeholder="Heslo" required>
                  <select name="role">
                    <option value="owner">Vlastník</option>
                    <option value="admin">Admin</option>
                    <option value="worker">Pracovník</option>
                  </select>
                </div>
                <div class="row">
                  <select name="worker_id">${renderWorkerOptions(selected?.worker_id || null)}</select>
                  <select name="status">
                    <option value="active">Aktivní</option>
                    <option value="inactive">Neaktivní</option>
                  </select>
                </div>
                <div class="toolbar"><button class="button button-primary" type="submit">Přidat uživatele</button></div>
              </form>
            </div>
            <div class="list-stack">${list || renderEmpty("Zatím žádní uživatelé.")}</div>
          </div>
          <div class="detail-panel">
            ${selected ? `
              <div class="detail-shell">
                <div class="hero-card">
                  <div>
                    <p class="hero-kicker">Uživatel</p>
                    <h3 class="hero-title">${escapeHtml(selected.full_name)}</h3>
                    <p class="hero-subtitle">${escapeHtml(selected.email)} · ${escapeHtml(selected.role)}</p>
                  </div>
                  <div class="hero-side">
                    <span class="chip">${escapeHtml(selected.status)}</span>
                    ${selected.worker ? `<span class="chip">${escapeHtml(selected.worker.full_name)}</span>` : ""}
                  </div>
                </div>
                <div class="toolbar">
                  <button type="button" class="button button-danger" data-delete-user="${selected.id}">Smazat uživatele</button>
                </div>
                <form id="user-update-form" class="compact-form" data-user-id="${selected.id}">
                  <div class="row">
                    <input name="full_name" value="${escapeHtml(selected.full_name || "")}" placeholder="Jméno uživatele" required>
                    <input name="email" value="${escapeHtml(selected.email || "")}" placeholder="Login" required>
                  </div>
                  <div class="row">
                    <input name="password" type="password" placeholder="Nové heslo (volitelné)">
                    <select name="role">
                      <option value="owner" ${selected.role === "owner" ? "selected" : ""}>Vlastník</option>
                      <option value="admin" ${selected.role === "admin" ? "selected" : ""}>Admin</option>
                      <option value="worker" ${selected.role === "worker" ? "selected" : ""}>Pracovník</option>
                    </select>
                  </div>
                  <div class="row">
                    <select name="worker_id">${renderWorkerOptions(selected.worker_id || null)}</select>
                    <select name="status">
                      <option value="active" ${selected.status === "active" ? "selected" : ""}>Aktivní</option>
                      <option value="inactive" ${selected.status === "inactive" ? "selected" : ""}>Neaktivní</option>
                    </select>
                  </div>
                  <div class="toolbar"><button class="button button-primary" type="submit">Uložit změny</button></div>
                </form>
              </div>
            ` : renderEmpty("Vyber uživatele ze seznamu.")}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderLoginView() {
  return `
    <div class="auth-shell">
      <section class="auth-card">
        <div class="page-heading">
          <h2>Přihlášení</h2>
          <p>Přihlas se do systému LB-AGENT.</p>
        </div>
        <form id="login-form" class="dialog-form auth-form">
          <input name="login" type="text" placeholder="Login" required autocomplete="username">
          <input name="password" type="password" placeholder="Heslo" required autocomplete="current-password">
          <button type="submit" class="button button-primary">Přihlásit</button>
        </form>
      </section>
    </div>
  `;
}

function renderApp() {
  if (!root) return;
  if (!state.currentUser) {
    root.innerHTML = normalizeCzechText(renderLoginView());
    renderProjectDialog();
    renderEmailDialog();
    renderTaskDialog();
    renderTaskFromEmailDialog();
    renderPasswordDialog();
    return;
  }
  root.innerHTML = normalizeCzechText(`
    <div class="app-shell">
      ${renderSidebar()}
      <main class="main">
        ${renderTopbar()}
        ${buildMessage()}
        ${renderCurrentView()}
      </main>
    </div>
  `);
  renderProjectDialog();
  renderEmailDialog();
  renderTaskDialog();
  renderTaskFromEmailDialog();
  renderPasswordDialog();
}

async function loadProjectDetail(projectId = state.selectedProjectId) {
  if (!projectId) {
    state.projectDetail = null;
    state.projectAutosaveStatus = "idle";
    return;
  }
  state.projectDetail = await fetchJson(`/api/projects/${projectId}`);
  state.projectAutosaveStatus = "idle";
}

async function loadConversationDetail(conversationId = state.selectedConversationId) {
  if (!conversationId) {
    state.conversationDetail = null;
    return;
  }
  state.conversationDetail = await fetchJson(`/api/conversations/${encodeURIComponent(conversationId)}`);
}

async function loadCurrentUser() {
  const result = await fetchJson("/api/auth/me");
  state.currentUser = result.item || null;
  state.authReady = true;
}

async function loadAll() {
  await loadCurrentUser();
  const role = getCurrentRole();
  const requests = {
    dashboard: fetchJson("/api/dashboard"),
    tasks: fetchJson("/api/tasks"),
    projects: fetchJson("/api/projects"),
    workers: fetchJson("/api/workers"),
    worklogs: fetchJson("/api/worklogs"),
    worklogSummary: fetchJson("/api/worklogs/summary"),
  };
  if (role === "owner") {
    requests.users = fetchJson("/api/users");
    requests.inbox = fetchJson("/api/inbox/unprocessed");
    requests.archive = fetchJson("/api/archive");
    requests.conversations = fetchJson("/api/conversations");
    requests.emails = fetchJson("/api/emails");
    requests.invoices = fetchJson("/api/invoices");
  } else if (role === "admin") {
    requests.invoices = fetchJson("/api/invoices");
  }

  const results = await Promise.all(
    Object.entries(requests).map(async ([key, promise]) => [key, await promise]),
  );
  const resolved = Object.fromEntries(results);

  state.dashboard = resolved.dashboard || null;
  state.inbox = resolved.inbox || { emails: [], tasks: [] };
  state.archive = resolved.archive || { emails: [], tasks: [] };
  state.conversations = resolved.conversations?.items || [];
  state.emails = resolved.emails?.items || [];
  state.tasks = resolved.tasks?.items || [];
  state.users = resolved.users?.items || [];
  state.projects = resolved.projects?.items || [];
  state.invoices = resolved.invoices?.items || [];
  state.workers = resolved.workers?.items || [];
  state.worklogs = resolved.worklogs?.items || [];
  state.worklogSummary = resolved.worklogSummary?.items || [];

  if (role === "worker" && state.currentUser?.worker_id) {
    state.selectedWorkerId = state.currentUser.worker_id;
  }

  if (!state.calendarMonth) {
    state.calendarMonth = monthStartKey();
  }
  if (!state.selectedCalendarDate) {
    state.selectedCalendarDate = toDateKey();
  }
  if (!state.calendarMode) {
    state.calendarMode = "month";
  }

  const allowedViews = ROLE_VIEWS[role] || [];
  if (!allowedViews.includes(state.activeView)) {
    state.activeView = allowedViews[0] || "dashboard";
  }
  if (role === "worker") {
    state.activeView = "workerPortal";
  }

  if (!state.selectedProjectId || !state.projects.some((item) => item.id === state.selectedProjectId)) {
    state.selectedProjectId = state.projects[0]?.id || null;
  }
  if (!state.selectedConversationId || !state.conversations.some((item) => item.id === state.selectedConversationId)) {
    state.selectedConversationId = state.conversations[0]?.id || null;
  }
  if (!state.selectedEmailId || !state.emails.some((item) => item.id === state.selectedEmailId)) {
    state.selectedEmailId = state.emails[0]?.id || null;
  }
  if (!state.selectedTaskId || !state.tasks.some((item) => item.id === state.selectedTaskId)) {
    state.selectedTaskId = state.tasks[0]?.id || null;
  }
  if (!state.selectedUserId || !state.users.some((item) => item.id === state.selectedUserId)) {
    state.selectedUserId = state.users[0]?.id || null;
  }
  if (!state.selectedInvoiceId || !state.invoices.some((item) => item.id === state.selectedInvoiceId)) {
    state.selectedInvoiceId = state.invoices[0]?.id || null;
  }
  if (!state.selectedWorkerId || !state.workers.some((item) => item.id === state.selectedWorkerId)) {
    state.selectedWorkerId = state.workers[0]?.id || null;
  }
  if (!state.selectedWorklogId || !state.worklogs.some((item) => item.id === state.selectedWorklogId)) {
    state.selectedWorklogId = state.worklogs[0]?.id || null;
  }
  if (!state.selectedInboxKey) {
    const inboxItems = getInboxItems();
    state.selectedInboxKey = inboxItems[0] ?`${inboxItems[0].kind}:${inboxItems[0].id}` : null;
  }
  if (!state.selectedArchiveKey) {
    const archiveItems = getArchiveItems();
    state.selectedArchiveKey = archiveItems[0]?.key || null;
  }

  await Promise.all([loadProjectDetail(), loadConversationDetail()]);
  renderApp();
}

async function performEmailAction(emailId, action, projectId = null) {
  await fetchJson(`/api/emails/${encodeURIComponent(emailId)}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, project_id: projectId }),
  });
  await loadAll();
  showMessage("ok", "Akce nad e-mailem byla provedena.");
}

async function performBulkEmailAction(action, emailIds, projectId = null) {
  if (!emailIds.length) {
    showMessage("error", "NejdĹ™Ă­v vyber e-maily.");
    return;
  }
  await fetchJson("/api/emails/bulk-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, email_ids: emailIds, project_id: projectId }),
  });
  state.selectedEmailIds.clear();
  await loadAll();
  showMessage("ok", "HromadnĂˇ akce nad e-maily byla provedena.");
}

async function performTaskAction(taskId, action, projectId = null) {
  const result = await fetchJson(`/api/tasks/${taskId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, project_id: projectId }),
  });
  await loadAll();
  if (action === "create_calendar_event") {
    if (result.synced_to_google) {
      showMessage("ok", "Úkol byl zapsán do Google Kalendáře.");
      return;
    }
    showMessage("info", "Událost byla zatím uložena jen lokálně. Zkontroluj GOOGLE_CALENDAR_ID a OAuth.");
    return;
  }
  showMessage("ok", "Akce nad Ăşkolem byla provedena.");
}

async function performBulkTaskAction(action, taskIds, projectId = null) {
  if (!taskIds.length) {
    showMessage("error", "NejdĹ™Ă­v vyber Ăşkoly.");
    return;
  }
  await fetchJson("/api/tasks/bulk-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, task_ids: taskIds, project_id: projectId }),
  });
  state.selectedTaskIds.clear();
  await loadAll();
  showMessage("ok", "HromadnĂˇ akce nad Ăşkoly byla provedena.");
}

async function updateWorklogPaymentStatus(worklogId, isPaid) {
  await fetchJson(`/api/worklogs/${worklogId}/payment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_paid: isPaid }),
  });
  await loadAll();
  showMessage("ok", isPaid ?"VĂ˝kaz byl oznaÄŤen jako proplacenĂ˝." : "VĂ˝kaz byl vrĂˇcen na neproplaceno.");
}

async function updateProjectWorkerPaymentStatus(projectId, workerId, isPaid) {
  await fetchJson("/api/worklogs/project-payment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, worker_id: workerId, is_paid: isPaid }),
  });
  await loadAll();
  showMessage("ok", isPaid ? "Zakázka byla pro tohoto pracovníka označena jako proplacená." : "Zakázka byla pro tohoto pracovníka vrácena na neproplaceno.");
}

async function deleteEntity(kind, id) {
  const labels = {
    email: "e-mail",
    task: "úkol",
    project: "zakázku",
    worker: "pracovníka",
    worklog: "hodinovou položku",
  };
  const successMessages = {
    email: "E-mail byl smazán.",
    task: "Úkol byl smazán.",
    project: "Zakázka byla smazána.",
    user: "Uživatel byl smazán.",
    worker: "Pracovník byl smazán.",
    worklog: "Hodinová položka byla smazána.",
  };
  const confirmed = window.confirm(normalizeCzechText(`Opravdu chceš smazat ${labels[kind] || "položku"}? Tato akce smaže pouze lokální data v systému.`));
  if (!confirmed) return;

  await fetchJson(`/api/${kind === "project" ?"projects" : kind === "worker" ?"workers" : kind === "user" ? "users" : `${kind}s`}/${encodeURIComponent(id)}/delete`, {
    method: "POST",
  });
  await loadAll();
  showMessage("ok", successMessages[kind] || "Záznam byl smazán.");
}

async function submitProjectForm(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.planned_start_at = payload.planned_start_at || null;
  payload.planned_end_at = payload.planned_end_at || null;
  payload.actual_start_at = null;
  payload.actual_end_at = null;
  payload.budget_amount = payload.budget_amount ?Number(payload.budget_amount) : null;
  payload.notes = "";
  payload.internal_notes = "";
  const result = await fetchJson("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedProjectId = result.item?.id || null;
  projectDialog?.close();
  await loadAll();
  showMessage("ok", "ZakĂˇzka byla vytvoĹ™ena.");
}

async function submitProjectUpdateForm(form) {
  const projectId = Number(form.dataset.projectId);
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.budget_amount = payload.budget_amount ?Number(payload.budget_amount) : null;
  payload.actual_start_at = payload.actual_start_at || null;
  payload.actual_end_at = payload.actual_end_at || null;
  payload.planned_start_at = payload.planned_start_at || null;
  payload.planned_end_at = payload.planned_end_at || null;
  await fetchJson(`/api/projects/${projectId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadAll();
}

function setProjectAutosaveStatus(status, render = true) {
  state.projectAutosaveStatus = status;
  if (render) renderApp();
}

function scheduleProjectAutosave(form) {
  if (!(form instanceof HTMLFormElement)) return;
  window.clearTimeout(projectAutosaveTimer);
  setProjectAutosaveStatus("saving", false);
  projectAutosaveTimer = window.setTimeout(async () => {
    try {
      await submitProjectUpdateForm(form);
      setProjectAutosaveStatus("saved");
    } catch (error) {
      setProjectAutosaveStatus("error");
      showMessage("error", error.message || "Uložení zakázky se nepodařilo.");
    }
  }, 250);
}

async function submitProjectDocumentForm(form) {
  const projectId = Number(form.dataset.projectId);
  const formData = new FormData(form);
  await fetchJson(`/api/projects/${projectId}/documents`, {
    method: "POST",
    body: formData,
  });
  await loadAll();
  showMessage("ok", "Dokument byl nahrĂˇn.");
}

async function submitProjectTaskForm(form) {
  const projectId = Number(form.dataset.projectId);
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.assigned_worker_ids = formData.getAll("assigned_worker_ids").map((value) => Number(value)).filter(Boolean);
  payload.assigned_worker_id = payload.assigned_worker_ids[0] || null;
  payload.estimated_hours = payload.estimated_hours ?Number(payload.estimated_hours) : null;
  payload.due_date = payload.due_date || null;
  await fetchJson(`/api/projects/${projectId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.projectSection = "tasks";
  taskDialog?.close();
  await loadAll();
  showMessage("ok", "Ăškol byl pĹ™idĂˇn k zakĂˇzce.");
}

async function submitTaskForm(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.project_id = payload.project_id ?Number(payload.project_id) : null;
  payload.assigned_worker_ids = formData.getAll("assigned_worker_ids").map((value) => Number(value)).filter(Boolean);
  payload.assigned_worker_id = payload.assigned_worker_ids[0] || null;
  payload.estimated_hours = payload.estimated_hours ?Number(payload.estimated_hours) : null;
  payload.due_date = payload.due_date || null;
  const result = await fetchJson("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedTaskId = result.item?.id || null;
  taskDialog?.close();
  await loadAll();
  showMessage("ok", "Ăškol byl vytvoĹ™en.");
}

async function submitTaskUpdateForm(form) {
  const taskId = Number(form.dataset.taskId);
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.project_id = payload.project_id ?Number(payload.project_id) : null;
  payload.assigned_worker_ids = formData.getAll("assigned_worker_ids").map((value) => Number(value)).filter(Boolean);
  payload.assigned_worker_id = payload.assigned_worker_ids[0] || null;
  payload.estimated_hours = payload.estimated_hours ?Number(payload.estimated_hours) : null;
  payload.due_date = String(payload.due_date || "").trim() || null;

  await fetchJson(`/api/tasks/${taskId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadAll();
  state.selectedTaskId = taskId;
  showMessage("ok", "Úkol byl upraven.");
}

async function submitTaskFromEmailForm(form) {
  const emailId = String(form.dataset.emailId || "").trim();
  if (!emailId) {
    showMessage("error", "Chybí zdrojový e-mail.");
    return;
  }

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.project_id = payload.project_id ?Number(payload.project_id) : null;
  payload.assigned_worker_ids = formData.getAll("assigned_worker_ids").map((value) => Number(value)).filter(Boolean);
  payload.assigned_worker_id = payload.assigned_worker_ids[0] || null;
  payload.estimated_hours = payload.estimated_hours ?Number(payload.estimated_hours) : null;
  payload.due_date = payload.due_date || null;

  const result = await fetchJson(`/api/emails/${encodeURIComponent(emailId)}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: "create_task",
      project_id: payload.project_id,
      title: payload.title,
      description: payload.description,
      due_date: payload.due_date,
      priority: payload.priority,
      assigned_worker_id: payload.assigned_worker_id,
      estimated_hours: payload.estimated_hours,
    }),
  });

  state.selectedTaskId = result.created_task_id || null;
  state.modalTaskEmailId = null;
  taskFromEmailDialog?.close();
  await loadAll();
  showMessage("ok", "Úkol byl vytvořen.");
}

async function submitProjectWorklogForm(form) {
  const projectId = Number(form.dataset.projectId);
  const formData = new FormData(form);
  const workDate = String(formData.get("work_date") || "").trim();
  const notes = String(formData.get("notes") || "").trim();
  const rows = Array.from(form.querySelectorAll(".project-worklog-entry"));
  const payloads = rows
    .map((row, index) => {
      const workerId = Number(formData.get(`worker_id_${index}`) || 0);
      const hours = parseDecimal(formData.get(`hours_${index}`) || 0);
      if (!workerId || !hours) return null;
      return {
        project_id: projectId,
        worker_id: workerId,
        work_date: workDate,
        hours,
        travel_km: 0,
        material_cost: parseDecimal(formData.get(`material_cost_${index}`) || 0),
        payout_amount: formData.get(`payout_amount_${index}`)
          ?parseDecimal(formData.get(`payout_amount_${index}`))
          : null,
        notes,
        billable_amount: null,
        starts_at: null,
        ends_at: null,
      };
    })
    .filter(Boolean);

  if (!workDate) {
    showMessage("error", "Vyber datum práce.");
    return;
  }
  if (!payloads.length) {
    showMessage("error", "Vyplň alespoň jednoho pracovníka a hodiny.");
    return;
  }

  for (const payload of payloads) {
    await fetchJson("/api/worklogs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  form.reset();
  state.projectSection = "worklogs";
  await loadAll();
  showMessage("ok", `Zapsány hodiny pro ${payloads.length} pracovníky.`);
}

async function submitWorkerForm(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.hourly_rate = payload.hourly_rate ?parseDecimal(payload.hourly_rate) : null;
  payload.payout_rate = payload.payout_rate ?parseDecimal(payload.payout_rate) : null;
  payload.status = "active";
  const result = await fetchJson("/api/workers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedWorkerId = result.item?.id || null;
  await loadAll();
  showMessage("ok", "Pracovník byl vytvořen.");
}

async function submitWorkerUpdateForm(form) {
  const workerId = Number(form.dataset.workerId);
  if (!workerId) {
    showMessage("error", "Chybí pracovník pro úpravu.");
    return;
  }

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.hourly_rate = payload.hourly_rate ?parseDecimal(payload.hourly_rate) : null;
  payload.payout_rate = payload.payout_rate ?parseDecimal(payload.payout_rate) : null;
  payload.status = payload.status || "active";

  const result = await fetchJson(`/api/workers/${workerId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedWorkerId = result.item?.id || workerId;
  await loadAll();
  showMessage("ok", "Pracovník byl upraven.");
}

async function submitUserForm(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.worker_id = payload.worker_id ? Number(payload.worker_id) : null;
  const result = await fetchJson("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedUserId = result.item?.id || null;
  await loadAll();
  showMessage("ok", "Uživatel byl vytvořen.");
}

async function submitUserUpdateForm(form) {
  const userId = Number(form.dataset.userId);
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.worker_id = payload.worker_id ? Number(payload.worker_id) : null;
  const result = await fetchJson(`/api/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedUserId = result.item?.id || userId;
  await loadAll();
  showMessage("ok", "Uživatel byl upraven.");
}

async function submitPasswordForm(form) {
  const formData = new FormData(form);
  await fetchJson("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: String(formData.get("current_password") || ""),
      new_password: String(formData.get("new_password") || ""),
    }),
  });
  form.reset();
  passwordDialog?.close();
  showMessage("ok", "Heslo bylo změněno.");
}

async function submitWorkerBulkForm(form) {
  const rows = String(new FormData(form).get("rows") || "")
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean);

  if (!rows.length) {
    showMessage("error", "Nejdřív zadej alespoň jeden řádek.");
    return;
  }

  let created = 0;
  for (const row of rows) {
    const [full_name, role = "", email = "", phone = "", hourly_rate = "", payout_rate = ""] = row
      .split(";")
      .map((part) => part.trim());
    if (!full_name) continue;

    await fetchJson("/api/workers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name,
        role,
        email,
        phone,
        hourly_rate: hourly_rate ?parseDecimal(hourly_rate) : null,
        payout_rate: payout_rate ?parseDecimal(payout_rate) : null,
        status: "active",
      }),
    });
    created += 1;
  }

  form.reset();
  await loadAll();
  showMessage("ok", `Přidáno pracovníků: ${created}.`);
}

async function submitWorkerPortalForm(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.project_id = Number(payload.project_id);
  payload.worker_id = Number(payload.worker_id);
  payload.hours = parseDecimal(payload.hours);
  payload.travel_km = 0;
  payload.material_cost = parseDecimal(payload.material_cost || 0);
  payload.payout_amount = payload.payout_amount ?parseDecimal(payload.payout_amount) : null;
  payload.billable_amount = null;
  payload.starts_at = null;
  payload.ends_at = null;
  await fetchJson("/api/worklogs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadAll();
  showMessage("ok", "Práce byla zapsána.");
}

async function submitWorkerPhotoForm(form) {
  const formData = new FormData(form);
  const projectId = Number(formData.get("project_id") || 0);
  if (!projectId) {
    showMessage("error", "Vyber zak?zku pro fotografii.");
    return;
  }
  formData.set("document_type", "photo");
  await fetchJson(`/api/projects/${projectId}/documents`, {
    method: "POST",
    body: formData,
  });
  await loadAll();
  showMessage("ok", "Fotografie byla nahr?na do zak?zky.");
}

async function submitLoginForm(form) {
  const formData = new FormData(form);
  await fetchJson("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      login: String(formData.get("login") || "").trim(),
      password: String(formData.get("password") || ""),
    }),
  });
  state.activeView = "dashboard";
  await loadAll();
  showMessage("ok", "Přihlášení proběhlo úspěšně.");
}

function bindEvents() {
  root?.addEventListener("click", async (event) => {
    const rawTarget = event.target;
    if (rawTarget instanceof Element && rawTarget.closest("[data-worklog-paid-toggle]")) {
      return;
    }
    const target = event.target.closest("[data-view], [data-refresh], [data-open-project-dialog], [data-open-task-dialog], [data-close-project-dialog], [data-close-email-dialog], [data-close-task-dialog], [data-select-item], [data-project-section], [data-email-action], [data-task-action], [data-task-email], [data-bulk-email-action], [data-bulk-task-action], [data-worklog-pay], [data-project-worklog-pay], [data-open-email], [data-open-task], [data-worklog-id], [data-worklog-summary], [data-conversation-assign], [data-create-project-from-email], [data-delete-email], [data-delete-task], [data-delete-project], [data-delete-worker], [data-delete-worklog], [data-delete-user], [data-logout], [data-open-password-dialog], [data-calendar-nav], [data-calendar-date], [data-calendar-mode]");
    if (!target) return;
    event.preventDefault();

    try {
      if (target.dataset.view) {
        state.activeView = target.dataset.view;
        renderApp();
        return;
      }
      if (target.hasAttribute("data-refresh")) {
        await loadAll();
        showMessage("ok", "Data byla obnovena.");
        return;
      }
      if (target.hasAttribute("data-logout")) {
        await fetchJson("/api/auth/logout", { method: "POST" });
        state.currentUser = null;
        state.authReady = true;
        renderApp();
        return;
      }
      if (target.hasAttribute("data-open-password-dialog")) {
        renderPasswordDialog();
        passwordDialog?.showModal();
        return;
      }
      if (target.hasAttribute("data-open-project-dialog")) {
        projectDialog?.showModal();
        return;
      }
      if (target.hasAttribute("data-open-task-dialog")) {
        state.modalTaskProjectId = target.dataset.openTaskDialog ?Number(target.dataset.openTaskDialog) || null : null;
        renderTaskDialog();
        taskDialog?.showModal();
        return;
      }
      if (target.hasAttribute("data-close-project-dialog")) {
        projectDialog?.close();
        return;
      }
      if (target.hasAttribute("data-close-task-dialog")) {
        taskDialog?.close();
        return;
      }
      if (target.hasAttribute("data-close-email-dialog")) {
        emailDialog?.close();
        state.modalEmailId = null;
        return;
      }
      if (target.dataset.selectItem) {
        const [kind, rawId] = target.dataset.selectItem.split(":");
        if (kind === "email") state.selectedEmailId = rawId;
        if (kind === "task") state.selectedTaskId = Number(rawId);
        if (kind === "project") {
          state.selectedProjectId = Number(rawId);
          await loadProjectDetail(state.selectedProjectId);
        }
        if (kind === "conversation") {
          state.selectedConversationId = rawId;
          await loadConversationDetail(state.selectedConversationId);
        }
        if (kind === "invoice") state.selectedInvoiceId = Number(rawId);
        if (kind === "user") state.selectedUserId = Number(rawId);
        if (kind === "worker") state.selectedWorkerId = Number(rawId);
        if ((kind === "email" || kind === "task") && state.activeView === "inbox") state.selectedInboxKey = `${kind}:${rawId}`;
        if ((kind === "email" || kind === "task") && state.activeView === "archive") state.selectedArchiveKey = `${kind}:${rawId}`;
        renderApp();
        return;
      }
      if (target.dataset.projectSection) {
        state.projectSection = target.dataset.projectSection;
        renderApp();
        return;
      }
      if (target.dataset.calendarNav) {
        if (target.dataset.calendarNav === "today") {
          state.calendarMonth = monthStartKey();
          state.selectedCalendarDate = toDateKey();
        } else {
          if (state.calendarMode === "week") {
            state.selectedCalendarDate = shiftDateKey(state.selectedCalendarDate || toDateKey(), target.dataset.calendarNav === "prev" ? -7 : 7);
            state.calendarMonth = monthStartKey(state.selectedCalendarDate);
          } else {
            state.calendarMonth = shiftMonthKey(state.calendarMonth || monthStartKey(), target.dataset.calendarNav === "prev" ? -1 : 1);
            if (!isSameMonth(state.selectedCalendarDate, state.calendarMonth)) {
              state.selectedCalendarDate = state.calendarMonth;
            }
          }
        }
        renderApp();
        return;
      }
      if (target.dataset.calendarMode) {
        state.calendarMode = target.dataset.calendarMode;
        state.calendarMonth = monthStartKey(state.selectedCalendarDate || toDateKey());
        renderApp();
        return;
      }
      if (target.dataset.calendarDate) {
        state.selectedCalendarDate = target.dataset.calendarDate;
        if (!isSameMonth(state.selectedCalendarDate, state.calendarMonth)) {
          state.calendarMonth = monthStartKey(parseDateKey(state.selectedCalendarDate));
        }
        renderApp();
        return;
      }
      if (target.dataset.emailAction) {
        const action = target.dataset.emailAction;
        const emailId = target.dataset.emailId;
        if (action === "create_task") {
          state.modalTaskEmailId = emailId;
          renderTaskFromEmailDialog();
          taskFromEmailDialog?.showModal();
          return;
        }
        const projectId = action === "assign_project" ?Number(document.querySelector("#email-project-select")?.value || 0) || null : null;
        await performEmailAction(emailId, action, projectId);
        return;
      }
      if (target.dataset.taskAction) {
        const action = target.dataset.taskAction;
        const taskId = Number(target.dataset.taskId);
        const projectId = action === "assign_project" ?Number(document.querySelector("#task-project-select")?.value || 0) || null : null;
        await performTaskAction(taskId, action, projectId);
        return;
      }
      if (target.dataset.taskEmail) {
        const taskId = Number(target.dataset.taskEmail);
        const task = state.tasks.find((item) => item.id === taskId) || null;
        openTaskEmailDraft(task);
        return;
      }
      if (target.dataset.deleteEmail) {
        await deleteEntity("email", target.dataset.deleteEmail);
        return;
      }
      if (target.dataset.deleteTask) {
        await deleteEntity("task", Number(target.dataset.deleteTask));
        return;
      }
      if (target.dataset.deleteProject) {
        await deleteEntity("project", Number(target.dataset.deleteProject));
        return;
      }
      if (target.dataset.deleteWorker) {
        await deleteEntity("worker", Number(target.dataset.deleteWorker));
        return;
      }
      if (target.dataset.deleteWorklog) {
        await deleteEntity("worklog", Number(target.dataset.deleteWorklog));
        return;
      }
      if (target.dataset.deleteUser) {
        await deleteEntity("user", Number(target.dataset.deleteUser));
        return;
      }
      if (target.dataset.bulkEmailAction) {
        const action = target.dataset.bulkEmailAction;
        const projectId = action === "assign_project" ?Number(document.querySelector("#bulk-email-project-select")?.value || 0) || null : null;
        await performBulkEmailAction(action, [...state.selectedEmailIds], projectId);
        return;
      }
      if (target.dataset.bulkTaskAction) {
        const action = target.dataset.bulkTaskAction;
        const projectId = action === "assign_project" ?Number(document.querySelector("#bulk-task-project-select")?.value || 0) || null : null;
        await performBulkTaskAction(action, [...state.selectedTaskIds], projectId);
        return;
      }
      if (target.dataset.worklogPay) {
        await updateWorklogPaymentStatus(Number(target.dataset.worklogPay), target.dataset.paid === "true");
        return;
      }
      if (target.dataset.projectWorklogPay) {
        await updateProjectWorkerPaymentStatus(
          Number(target.dataset.projectWorklogPay),
          Number(target.dataset.workerId),
          target.dataset.paid === "true",
        );
        return;
      }
      if (target.dataset.openEmail) {
        state.modalEmailId = target.dataset.openEmail;
        renderEmailDialog();
        emailDialog?.showModal();
        return;
      }
      if (target.dataset.openTask) {
        state.activeView = "tasks";
        state.selectedTaskId = Number(target.dataset.openTask);
        renderApp();
        return;
      }
      if (target.dataset.worklogId) {
        state.selectedWorklogId = Number(target.dataset.worklogId);
        renderApp();
        return;
      }
      if (target.dataset.worklogSummary) {
        state.selectedWorklogSummaryKey = target.dataset.worklogSummary;
        renderApp();
        return;
      }
      if (target.dataset.conversationAssign) {
        const emailIds = target.dataset.conversationAssign.split(",").filter(Boolean);
        const projectId = Number(document.querySelector("#conversation-project-select")?.value || 0) || null;
        await performBulkEmailAction("assign_project", emailIds, projectId);
        return;
      }
      if (target.dataset.createProjectFromEmail) {
        await performEmailAction(target.dataset.createProjectFromEmail, "create_project", null);
      }
    } catch (error) {
      showMessage("error", error.message || "Operace se nepodaĹ™ila.");
    }
  });

  document.addEventListener("click", (event) => {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;
    const target = rawTarget.closest("[data-close-project-dialog], [data-close-task-dialog], [data-close-email-dialog], [data-close-task-from-email-dialog], [data-close-password-dialog]");
    if (!target) return;

    if (target.hasAttribute("data-close-project-dialog")) {
      projectDialog?.close();
      return;
    }

    if (target.hasAttribute("data-close-task-dialog")) {
      taskDialog?.close();
      state.modalTaskProjectId = null;
      return;
    }

    if (target.hasAttribute("data-close-email-dialog")) {
      emailDialog?.close();
      state.modalEmailId = null;
      return;
    }

    if (target.hasAttribute("data-close-task-from-email-dialog")) {
      taskFromEmailDialog?.close();
      state.modalTaskEmailId = null;
      return;
    }

    if (target.hasAttribute("data-close-password-dialog")) {
      passwordDialog?.close();
    }
  });

  projectDialog?.addEventListener("close", () => {
    renderProjectDialog();
  });

  taskDialog?.addEventListener("close", () => {
    state.modalTaskProjectId = null;
    renderTaskDialog();
  });

  emailDialog?.addEventListener("close", () => {
    state.modalEmailId = null;
    renderEmailDialog();
  });

  taskFromEmailDialog?.addEventListener("close", () => {
    state.modalTaskEmailId = null;
    renderTaskFromEmailDialog();
  });

  passwordDialog?.addEventListener("close", () => {
    renderPasswordDialog();
  });

  emailDialog?.addEventListener("click", (event) => {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;
    const target = rawTarget.closest("[data-close-email-dialog]");
    if (!target) return;
    emailDialog.close();
    state.modalEmailId = null;
  });

  messageDialog?.addEventListener("click", (event) => {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;
    const target = rawTarget.closest("[data-close-message-dialog]");
    if (!target) return;
    messageDialog.close();
  });

  root?.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const projectForm = target.closest("#project-update-form");
    if (projectForm instanceof HTMLFormElement) {
      scheduleProjectAutosave(projectForm);
      return;
    }
    if (target.matches('#project-worklog-form [name^="worker_id_"], #project-worklog-form [name^="hours_"], #project-worklog-form [name^="rate_"], #project-worklog-form [name^="material_cost_"]')) {
      const row = target.closest(".project-worklog-entry");
      if (target.matches('#project-worklog-form [name^="worker_id_"]') && row instanceof HTMLElement) {
        const rateInput = row.querySelector('[name^="rate_"]');
        if (rateInput instanceof HTMLInputElement) {
          rateInput.dataset.autoRate = "true";
        }
      }
      if (target.matches('#project-worklog-form [name^="rate_"]')) {
        target.dataset.autoRate = target.value ?"false" : "true";
      }
      updateProjectWorklogRowPayout(row, true);
      return;
    }
    if (target.matches('#worker-portal-form [name="worker_id"], #worker-portal-form [name="hours"], #worker-portal-form [name="rate"], #worker-portal-form [name="material_cost"]')) {
      if (target.matches('#worker-portal-form [name="rate"]')) {
        target.dataset.autoRate = target.value ?"false" : "true";
      }
      const form = target.closest("form");
      updateWorklogPayoutSuggestion(form, true);
      return;
    }
    if (target.matches("[data-worklog-paid-toggle]")) {
      const worklogId = Number(target.getAttribute("data-worklog-paid-toggle"));
      updateWorklogPaymentStatus(worklogId, target.checked).catch((error) => {
        showMessage("error", error.message || "ZmÄ›na stavu vĂ˝platy se nepodaĹ™ila.");
      });
      return;
    }
    if (target.matches("[data-select-email]")) {
      const emailId = target.getAttribute("data-select-email");
      if (!emailId) return;
      if (target.checked) state.selectedEmailIds.add(emailId);
      else state.selectedEmailIds.delete(emailId);
      renderApp();
      return;
    }
    if (target.matches("[data-select-task]")) {
      const taskId = Number(target.getAttribute("data-select-task"));
      if (target.checked) state.selectedTaskIds.add(taskId);
      else state.selectedTaskIds.delete(taskId);
      renderApp();
      return;
    }
    if (target.id === "email-category-filter") {
      state.emailCategoryFilter = target.value;
      renderApp();
      return;
    }
    if (target.id === "worklog-worker-filter") {
      state.worklogWorkerFilter = target.value;
      state.selectedWorklogSummaryKey = null;
      renderApp();
      return;
    }
    if (target.id === "worklog-project-filter") {
      state.worklogProjectFilter = target.value;
      state.selectedWorklogSummaryKey = null;
      renderApp();
      return;
    }
    if (target.id === "worklog-payment-filter") {
      state.worklogPaymentFilter = target.value;
      state.selectedWorklogSummaryKey = null;
      renderApp();
    }
  });

  root?.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.matches('#project-worklog-form [name^="hours_"], #project-worklog-form [name^="rate_"], #project-worklog-form [name^="material_cost_"]')) {
      if (target.matches('#project-worklog-form [name^="rate_"]')) {
        target.dataset.autoRate = target.value ?"false" : "true";
      }
      const row = target.closest(".project-worklog-entry");
      updateProjectWorklogRowPayout(row);
      return;
    }
    if (target.matches('#worker-portal-form [name="payout_amount"]')) {
      target.dataset.autoPayout = target.value ?"false" : "true";
      return;
    }
    if (target.matches('#worker-portal-form [name="hours"], #worker-portal-form [name="rate"], #worker-portal-form [name="material_cost"]')) {
      if (target.matches('#worker-portal-form [name="rate"]')) {
        target.dataset.autoRate = target.value ?"false" : "true";
      }
      const form = target.closest("form");
      updateWorklogPayoutSuggestion(form);
      return;
    }
    if (target.id === "email-search" && target instanceof HTMLInputElement) {
      const selectionStart = target.selectionStart ?? target.value.length;
      const selectionEnd = target.selectionEnd ?? selectionStart;
      state.emailSearch = target.value;
      renderApp();
      const nextInput = root?.querySelector("#email-search");
      if (nextInput instanceof HTMLInputElement) {
        nextInput.focus();
        nextInput.setSelectionRange(selectionStart, selectionEnd);
      }
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    try {
      if (form.id === "project-form") return await submitProjectForm(form);
      if (form.id === "login-form") return await submitLoginForm(form);
      if (form.id === "password-form") return await submitPasswordForm(form);
      if (form.id === "project-update-form") {
        await submitProjectUpdateForm(form);
        setProjectAutosaveStatus("saved");
        return;
      }
      if (form.id === "project-document-form") return await submitProjectDocumentForm(form);
      if (form.id === "task-form") return await submitTaskForm(form);
      if (form.id === "task-update-form") return await submitTaskUpdateForm(form);
      if (form.id === "task-from-email-form") return await submitTaskFromEmailForm(form);
      if (form.id === "project-task-form") return await submitProjectTaskForm(form);
      if (form.id === "project-worklog-form") return await submitProjectWorklogForm(form);
      if (form.id === "user-form") return await submitUserForm(form);
      if (form.id === "user-update-form") return await submitUserUpdateForm(form);
      if (form.id === "worker-form") return await submitWorkerForm(form);
      if (form.id === "worker-update-form") return await submitWorkerUpdateForm(form);
      if (form.id === "worker-bulk-form") return await submitWorkerBulkForm(form);
      if (form.id === "worker-portal-form") return await submitWorkerPortalForm(form);
      if (form.id === "worker-photo-form") return await submitWorkerPhotoForm(form);
    } catch (error) {
      showMessage("error", error.message || "UloĹľenĂ­ se nepodaĹ™ilo.");
    }
  });
}

async function boot() {
  bindEvents();
  renderApp();
  try {
    await loadAll();
  } catch (error) {
    if (!state.currentUser) {
      state.currentUser = null;
      state.authReady = true;
      renderApp();
      return;
    }
    showMessage("error", error.message || "Načtení se nepodařilo.");
  }
}

boot();
