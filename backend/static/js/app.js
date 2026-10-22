// State
let ws = null;
let currentView = 'attendance';

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  
  // Set default filter date to today
  const today = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('filterDate');
  if (dateInput) dateInput.value = today;

  connectWebSocket();
  loadStats();
  loadAttendance();
  loadUsers();
});

// WebSocket for Real-time Card Taps
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onopen = () => {
    updateStatus(true, "Live");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'SCAN_EVENT') {
        showScanAlert(data);
        loadAttendance();
      } else if (data.type === 'USER_CREATED' || data.type === 'USER_DELETED') {
        loadUsers();
      }
      if (data.stats) updateStats(data.stats);
    } catch (e) {
      console.error(e);
    }
  };

  ws.onclose = () => {
    updateStatus(false, "Offline");
    setTimeout(connectWebSocket, 3000);
  };
}

function updateStatus(isOnline, text) {
  const dot = document.getElementById("statusDot");
  const label = document.getElementById("statusText");
  if (!dot || !label) return;

  if (isOnline) {
    dot.className = "h-2 w-2 rounded-full bg-emerald-400 animate-pulse";
    label.textContent = text;
  } else {
    dot.className = "h-2 w-2 rounded-full bg-rose-500";
    label.textContent = text;
  }
}

// Live Tap Notification Banner
function showScanAlert(data) {
  const banner = document.getElementById("liveAlertCard");
  const badge = document.getElementById("liveAlertBadge");
  const name = document.getElementById("liveAlertName");
  const uid = document.getElementById("liveAlertUID");
  const time = document.getElementById("liveAlertTime");
  const action = document.getElementById("liveAlertAction");

  banner.classList.remove("hidden");
  uid.textContent = data.card_uid;
  time.textContent = data.timestamp ? data.timestamp.split(" ")[1] : "Just now";

  if (data.status === "CHECK_IN") {
    banner.className = "rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-4 transition-all";
    badge.className = "text-xs font-bold px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase";
    badge.textContent = "CHECK-IN";
    name.textContent = data.user_name || "Authorized User";
    action.innerHTML = "";
  } else if (data.status === "CHECK_OUT") {
    banner.className = "rounded-xl border border-cyan-500/30 bg-cyan-950/30 p-4 transition-all";
    badge.className = "text-xs font-bold px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 uppercase";
    badge.textContent = "CHECK-OUT";
    name.textContent = data.user_name || "Authorized User";
    action.innerHTML = "";
  } else {
    // Unregistered Card
    banner.className = "rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 transition-all";
    badge.className = "text-xs font-bold px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-400 border border-rose-500/30 uppercase";
    badge.textContent = "UNREGISTERED";
    name.textContent = "Unknown Card Scanned";
    action.innerHTML = `
      <button onclick="openRegisterWithUid('${data.card_uid}')" class="bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs px-2.5 py-1 rounded-lg transition">
        Enroll Card
      </button>
    `;
  }
}

// Summary Metrics
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const stats = await res.json();
    updateStats(stats);
  } catch (e) {
    console.error(e);
  }
}

function updateStats(stats) {
  document.getElementById("statTodayAttendees").textContent = stats.today_attendees ?? 0;
  document.getElementById("statCurrentlyIn").textContent = stats.currently_in ?? 0;
  document.getElementById("statTotalUsers").textContent = stats.total_users ?? 0;
}

// Attendance Table
async function loadAttendance() {
  const dateVal = document.getElementById("filterDate")?.value || "";
  let url = "/api/attendance";
  if (dateVal) url += `?target_date=${dateVal}`;

  try {
    const res = await fetch(url);
    const logs = await res.json();
    const tbody = document.getElementById("attendanceTableBody");
    if (!tbody) return;

    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-slate-500">No attendance records found for this date.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => {
      let badge = "";
      if (l.log_type === "CHECK_IN") {
        badge = `<span class="px-2 py-0.5 rounded font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">IN</span>`;
      } else if (l.log_type === "CHECK_OUT") {
        badge = `<span class="px-2 py-0.5 rounded font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">OUT</span>`;
      } else {
        badge = `<span class="px-2 py-0.5 rounded font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">UNKNOWN</span>`;
      }

      const timeStr = new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      return `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="py-2.5 px-4 font-mono text-slate-400">${timeStr}</td>
          <td class="py-2.5 px-4">${badge}</td>
          <td class="py-2.5 px-4 font-medium text-white">${l.user_name}</td>
          <td class="py-2.5 px-4 text-slate-400 font-mono">${l.identifier || '-'}</td>
          <td class="py-2.5 px-4 font-mono text-cyan-400">${l.card_uid}</td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.error(e);
  }
}

// Enrolled Users Table
async function loadUsers() {
  try {
    const res = await fetch("/api/users");
    const users = await res.json();
    const tbody = document.getElementById("usersTableBody");
    if (!tbody) return;

    if (users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-slate-500">No users enrolled yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = users.map(u => `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="py-2.5 px-4 font-medium text-white">${u.name}</td>
        <td class="py-2.5 px-4 text-slate-400 font-mono">${u.identifier || '-'}</td>
        <td class="py-2.5 px-4 text-slate-400">${u.department || 'General'}</td>
        <td class="py-2.5 px-4 font-mono text-cyan-400">${u.card_uid}</td>
        <td class="py-2.5 px-4 text-right">
          <button onclick="deleteUser(${u.id}, '${u.name}')" class="text-rose-400 hover:text-rose-300 text-xs px-2 py-0.5 rounded hover:bg-rose-950/40 transition">
            Delete
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

// View Switcher: Attendance vs Users
function switchView(viewName) {
  currentView = viewName;
  const viewAtt = document.getElementById("view-attendance");
  const viewUsr = document.getElementById("view-users");
  const btnAtt = document.getElementById("tabBtn-attendance");
  const btnUsr = document.getElementById("tabBtn-users");
  const controls = document.getElementById("attendanceControls");

  if (viewName === 'attendance') {
    viewAtt.classList.remove("hidden");
    viewUsr.classList.add("hidden");
    controls.classList.remove("hidden");
    btnAtt.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-700 text-white transition";
    btnUsr.className = "px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white rounded-lg transition";
    loadAttendance();
  } else {
    viewAtt.classList.add("hidden");
    viewUsr.classList.remove("hidden");
    controls.classList.add("hidden");
    btnUsr.className = "px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-700 text-white transition";
    btnAtt.className = "px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white rounded-lg transition";
    loadUsers();
  }
}

// CSV Export
function exportCSV() {
  const dateVal = document.getElementById("filterDate")?.value || "";
  let url = "/api/attendance/export";
  if (dateVal) url += `?target_date=${dateVal}`;
  window.open(url, "_blank");
}

// User Enrollment Modal
function openRegisterModal() {
  document.getElementById("registerForm").reset();
  document.getElementById("regError").classList.add("hidden");
  document.getElementById("registerModal").classList.remove("hidden");
}

function openRegisterWithUid(cardUid) {
  openRegisterModal();
  document.getElementById("regCardUid").value = cardUid;
}

function closeRegisterModal() {
  document.getElementById("registerModal").classList.add("hidden");
}

async function fetchLastScanned() {
  try {
    const res = await fetch("/api/system/last-scanned");
    const data = await res.json();
    if (data.card_uid) {
      document.getElementById("regCardUid").value = data.card_uid;
    } else {
      alert("No recent card scan found. Swipe a card on the reader first.");
    }
  } catch (e) {
    console.error(e);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const errorBox = document.getElementById("regError");
  errorBox.classList.add("hidden");

  const payload = {
    card_uid: document.getElementById("regCardUid").value,
    name: document.getElementById("regName").value,
    identifier: document.getElementById("regIdentifier").value,
    department: document.getElementById("regDepartment").value,
    role: "Member",
    is_active: true
  };

  try {
    const res = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }

    closeRegisterModal();
    loadUsers();
    loadStats();
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("hidden");
  }
}

async function deleteUser(id, name) {
  if (!confirm(`Delete user '${name}'?`)) return;
  try {
    const res = await fetch(`/api/users/${id}`, { method: "DELETE" });
    if (res.ok) {
      loadUsers();
      loadStats();
    }
  } catch (e) {
    console.error(e);
  }
}
