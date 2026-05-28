const API = 'http://127.0.0.1:8765/api';
let state = { profiles: [], selectedProfileId: null, tasks: [], editingProfileId: null, activeTab: 'channels' };
const openTaskIds = new Set();
const $ = (id) => document.getElementById(id);
function toast(msg) {
  const el = $('toast');
  el.innerHTML = msg;
  el.classList.remove('hidden');
  clearTimeout(el._timeout);
  el._timeout = setTimeout(() => el.classList.add('hidden'), 5000);
}
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
function statusBadge(status) {
  const map = {
    Pending: ['Đang đợi', 'yellow'],
    Running: ['Đang đăng', 'blue'],
    Completed: ['Đã đăng', 'green'],
    Failed: ['Lỗi', 'red'],
  };
  const [label, cls] = map[status] || [status, ''];
  return `<span class="badge ${cls}">${label}</span>`;
}
function fmtDate(value) {
  if (!value) return 'Chưa đặt lịch';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value.replace('T', ' ').slice(0, 16);
  return d.toLocaleString('vi-VN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
function fmtTime(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value.slice(11, 16);
  return d.toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit' });
}
function fmtShortDate(val) {
  if (!val) return '';
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return val.slice(5, 10);
  const day = d.getDate();
  const month = d.getMonth() + 1;
  return `${day}/${month}`;
}
function toInputDate(value) {
  if (!value) return '';
  return value.replace(' ', 'T').slice(0, 16);
}
// ─── TAB NAVIGATION ───
function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById('tab-' + tabId);
  if (target) target.classList.remove('hidden');
  document.querySelectorAll('.sidebar .nav').forEach(el => el.classList.remove('active'));
  const nav = document.querySelector(`.sidebar .nav[data-tab="${tabId}"]`);
  if (nav) nav.classList.add('active');
  if (tabId === 'channels') loadProfiles();
  if (tabId === 'report') loadReport();
  if (tabId === 'settings') loadSettings();
}
document.querySelectorAll('.sidebar .nav').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    if (tab) switchTab(tab);
  });
});
// ─── PROFILES ───
async function loadProfiles() {
  if (state.activeTab !== 'channels') return;
  try {
    const data = await api('/profiles');
    const fresh = data.profiles || [];
    // Detect if profiles were added or removed
    const oldIds = state.profiles.map(p => p.id).join(',');
    const newIds = fresh.map(p => p.id).join(',');
    const structureChanged = oldIds !== newIds;
    state.profiles = fresh;
    $('apiStatus').textContent = 'Đã kết nối';
    $('apiStatus').className = 'status-indicator ok';
    const modalOpen = !$('profileModal').classList.contains('hidden');
    if (modalOpen || !structureChanged) {
      // Lightweight patch: only update badges + stats, never rebuild DOM
      patchProfileCards();
    } else {
      // Full rebuild only when profile list structure changes (add/delete)
      renderProfiles();
    }
  } catch (err) {
  }
}
// Surgical DOM update — only touches badges and stats numbers, never freezes input
function patchProfileCards() {
  const root = $('profiles');
  if (!root) return;
  // If cards not rendered yet, do full render
  if (!root.querySelector('[data-pid]')) { renderProfiles(); return; }
  state.profiles.forEach(p => {
    const card = root.querySelector(`[data-pid="${p.id}"]`);
    if (!card) return;
    const s = p.stats || {};
    const badgesEl = card.querySelector('.card-badges');
    if (badgesEl) badgesEl.innerHTML =
      `<span class="badge ${p.isActive ? 'badge-success' : 'badge-danger'}">${p.isActive ? 'API On' : 'API Off'}</span>` +
      `<span class="badge ${p.chromeRunning ? 'badge-info' : ''}">${p.chromeRunning ? 'Chrome On' : 'Chrome Off'}</span>`;
    const statsEl = card.querySelector('.card-stats');
    if (statsEl) statsEl.innerHTML =
      stat('Tổng', s.total || 0) + stat('Đợi', s.waiting || 0) +
      stat('Đang', s.running || 0) + stat('Đã đăng', s.completed || 0) +
      stat('Lỗi', s.failed || 0);
    const subtitleEl = card.querySelector('.card-subtitle');
    if (subtitleEl) subtitleEl.textContent = p.channelTitle || p.channelId || 'Chưa có thông tin kênh';
    const avatarEl = card.querySelector('.card-logo');
    if (avatarEl && p.channelAvatar) avatarEl.src = p.channelAvatar;
  });
}
function renderProfiles() {
  const root = $('profiles');
  const emptyEl = $('emptyState');
  if (!state.profiles || state.profiles.length === 0) {
    root.innerHTML = '';
    if (emptyEl) emptyEl.classList.remove('hidden');
    return;
  }
  if (emptyEl) emptyEl.classList.add('hidden');
  root.innerHTML = state.profiles.map((p) => {
    const s = p.stats || {};
    const avatarSrc = p.channelAvatar || 'assets/app-icon.jpg';
    return `<article class="profile-card" data-pid="${p.id}">
      <div class="card-head">
        <img class="card-logo" src="${escapeHtml(avatarSrc)}" alt="" onerror="this.src='assets/app-icon.jpg'" />
        <div class="card-info">
          <div class="card-title">${escapeHtml(p.name)}</div>
          <div class="card-subtitle">${escapeHtml(p.channelTitle || p.channelId || 'Chưa có thông tin kênh')}</div>
        </div>
        <div class="card-head-actions">
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); editProfile(${p.id})" title="Sửa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
          <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteProfile(${p.id})" title="Xóa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
        </div>
      </div>
      <div class="card-badges">
        <span class="badge ${p.isActive ? 'badge-success' : 'badge-danger'}">${p.isActive ? 'API On' : 'API Off'}</span>
        <span class="badge ${p.chromeRunning ? 'badge-info' : ''}">${p.chromeRunning ? 'Chrome On' : 'Chrome Off'}</span>
      </div>
      <div class="card-stats">
        ${stat('Tổng', s.total || 0)}${stat('Đợi', s.waiting || 0)}${stat('Đang', s.running || 0)}${stat('Đã đăng', s.completed || 0)}${stat('Lỗi', s.failed || 0)}
      </div>
      <div class="card-actions">
        <button class="btn btn-success btn-sm" onclick="openTasks(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>Quản lý video</button>
        <button class="btn btn-warning btn-sm" onclick="postProfile(${p.id}, 'open-studio')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><polyline points="8 21 12 17 16 21"/></svg>Studio</button>
        <button class="btn btn-secondary btn-sm" onclick="checkApi(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>Check API</button>
        <button class="btn btn-secondary btn-sm" onclick="postProfile(${p.id}, 'open-api-key')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>API Key</button>
      </div>
    </article>`;
  }).join('');
}
function stat(label, value) { return `<div class="stat-item"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`; }
// ─── TASKS ───
async function openTasks(profileId) { state.selectedProfileId = profileId; await loadTasks(profileId, true); }
async function loadTasks(profileId, showPanel = true) {
  const data = await api(`/profiles/${profileId}/tasks`);
  state.tasks = data.tasks || [];
  if (showPanel) $('tasksModal').classList.remove('hidden');
  renderTasks();
}
function renderTasks() {
  const profile = state.profiles.find(p => p.id === state.selectedProfileId);
  const panel = $('tasksPanel');
  if (!profile) return;
  panel.innerHTML = `<div class="modal-header"><div><h2>Quản lý video — ${escapeHtml(profile.name)}</h2><p class="muted">Thêm, chỉnh sửa và đăng video</p></div><div style="display:flex;gap:8px"><button class="btn btn-success btn-sm" onclick="addVideos(${profile.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>Thêm video</button><button class="btn btn-secondary btn-sm" onclick="loadTasks(${profile.id}, true)">Làm mới</button><button class="btn btn-secondary btn-sm" onclick="closeTasks()">Đóng</button></div></div><div class="task-list">${state.tasks.length ? state.tasks.map(taskHtml).join('') : '<div class="muted" style="padding:12px">Chưa có video nào. Nhấn "Thêm video" để bắt đầu.</div>'}</div>`;
}
function taskHtml(t) {
  const isOpen = openTaskIds.has(t.id);
  const statusMap = { Pending: ['Đang đợi', 'pending'], Running: ['Đang đăng', 'running'], Completed: ['Đã đăng', 'completed'], Failed: ['Lỗi', 'failed'] };
  const [statusLabel, statusCls] = statusMap[t.status] || [t.status, ''];
  const retryCount = t.retryCount || 0;
  const retryBadge = retryCount > 0 ? `<span class="badge" style="background:orange;color:#000;font-size:10px;margin-left:4px">Retry ${retryCount}/3</span>` : '';
  const retryBtn = t.status === 'Failed' ? `<button class="btn btn-warning btn-sm" onclick="event.stopPropagation(); retryTask(${t.id})" title="Thử lại ngay"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg></button>` : '';
  return `<div class="task-row ${isOpen ? 'open' : ''}" id="task-${t.id}">
    <div class="task-row-main" onclick="toggleTask(${t.id})">
      <div class="task-row-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>
      <div class="task-row-info"><div class="task-row-title">${escapeHtml(t.title || 'Video mới')}${retryBadge}</div><div class="task-row-meta"><span class="task-row-meta-item">#${t.id}</span><span class="task-row-meta-sep">·</span><span class="task-row-meta-item">${fmtDate(t.scheduleTime)}</span><span class="task-row-meta-sep">·</span><span class="task-row-meta-item">${escapeHtml(t.timezone || 'UTC')}</span></div></div>
      <div class="task-row-status"><span class="task-status ${statusCls}" id="status-${t.id}">${statusLabel}</span></div>
      <div class="task-row-actions">
        ${retryBtn}
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); toggleTask(${t.id})" title="Mở setting"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>${isOpen ? 'Thu gọn' : 'Setting'}</button>
        <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteTask(${t.id})" title="Xóa task"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Xóa</button>
      </div>
    </div>
    <div class="task-row-body">
      <div class="form-grid">
        <label class="wide">Tiêu đề video<input id="title-${t.id}" value="${attr(t.title)}" /></label>
        <label class="wide">Mô tả<textarea id="desc-${t.id}">${escapeHtml(t.description || '')}</textarea></label>
        <label>Tags<input id="tags-${t.id}" value="${attr(t.tags)}" /></label>
        <label>Hashtags<input id="hashtags-${t.id}" value="${attr(t.hashtags)}" /></label>
        <label class="field-highlight">Lịch đăng<div class="schedule-picker"><input id="schedule-${t.id}" type="datetime-local" value="${toInputDate(t.scheduleTime)}" /><button class="btn btn-sm btn-secondary" onclick="document.getElementById('schedule-${t.id}').showPicker ? document.getElementById('schedule-${t.id}').showPicker() : document.getElementById('schedule-${t.id}').click()">📅</button></div><span class="schedule-hint">Để trống = đăng ngay</span></label>
        <label>Múi giờ<select id="timezone-${t.id}">${timezoneOptions(t.timezone || 'Asia/Ho_Chi_Minh')}</select></label>
        <label>Audience / trẻ em<select id="kids-${t.id}"><option value="false" ${!t.madeForKids ? 'selected' : ''}>Không dành cho trẻ em</option><option value="true" ${t.madeForKids ? 'selected' : ''}>Dành cho trẻ em</option></select></label>
        <label>Altered content<select id="altered-${t.id}"><option value="false" ${!t.alteredContent ? 'selected' : ''}>Không</option><option value="true" ${t.alteredContent ? 'selected' : ''}>Có</option></select></label>
        <label class="check-row wide"><input id="paid-${t.id}" type="checkbox" ${t.paidPromotion ? 'checked' : ''}/> Có paid promotion / tài trợ / product placement</label>
      </div>
      <div class="form-actions"><button class="btn btn-success btn-sm" onclick="saveTask(${t.id})">💾 Lưu và chạy</button></div>
    </div>
  </div>`;
}
function toggleTask(id) {
  const el = document.getElementById(`task-${id}`);
  if (!el) return;
  const willOpen = !el.classList.contains('open');
  if (willOpen) openTaskIds.add(id); else openTaskIds.delete(id);
  renderTasks();
}
function closeTasks() {
  state.selectedProfileId = null; openTaskIds.clear(); $('tasksModal').classList.add('hidden'); }
async function refreshTaskStatusOnly() {
  if (!state.selectedProfileId || $('tasksModal').classList.contains('hidden')) return;
  try {
    const data = await api(`/profiles/${state.selectedProfileId}/tasks`);
    const freshTasks = data.tasks || [];
    const freshById = new Map(freshTasks.map(t => [t.id, t]));
    for (const oldTask of state.tasks) {
      if (!freshById.has(oldTask.id)) { openTaskIds.delete(oldTask.id); document.getElementById(`task-${oldTask.id}`)?.remove(); }
    }
    for (const task of freshTasks) { const statusEl = document.getElementById(`status-${task.id}`); if (statusEl) statusEl.innerHTML = statusBadge(task.status); }
    state.tasks = freshTasks;
    if (openTaskIds.size === 0) renderTasks();
  } catch (err) { console.warn('Task status refresh failed:', err.message); }
}
async function addVideos(profileId) {
  const paths = await window.nativeApi.pickVideos();
  if (!paths || !paths.length) return;
  try { await api(`/profiles/${profileId}/tasks`, { method: 'POST', body: JSON.stringify({ paths }) }); toast(`Đã thêm ${paths.length} video`); await loadProfiles(); await loadTasks(profileId, true); }
  catch (err) { toast('Lỗi thêm video: ' + err.message); }
}
async function saveTask(id) {
  const title = (val(`title-${id}`) || '').trim();
  const desc = (val(`desc-${id}`) || '').trim();
  const tags = (val(`tags-${id}`) || '').trim();
  const hashtags = (val(`hashtags-${id}`) || '').trim();
  const scheduleVal = val(`schedule-${id}`);
  const timezone = val(`timezone-${id}`) || 'Asia/Ho_Chi_Minh';
  var errors = [];
  if (!title) errors.push('thiếu tiêu đề');
  if (!desc) errors.push('thiếu mô tả');
  if (!tags) errors.push('thiếu tags');
  if (!scheduleVal) {
    errors.push('chưa đặt lịch');
  } else {
    var selected = new Date(scheduleVal + ':00');
    var now = new Date();
    if (selected <= now) errors.push('lịch đăng không hợp lệ (đã qua)');
  }
  if (errors.length > 0) {
    toast('\u274c ' + errors.join(', '));
    return;
  }
  const data = { title: title, description: desc, tags: tags, hashtags: hashtags, scheduleTime: scheduleVal, timezone: timezone, madeForKids: val(`kids-${id}`) === 'true', paidPromotion: document.getElementById(`paid-${id}`).checked, alteredContent: val(`altered-${id}`) === 'true' };
  try {
    const r = await api(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    toast('\u2705 Đã lưu thành công');
    // Giữ nguyên UI, không load lại task list
    loadProfiles();
  } catch (err) {
    toast('\u274c Lỗi lưu: ' + (err.message || 'Lỗi không xác định'));
  }
}
async function deleteTask(id) {
  if (!confirm('Xóa task này và file cache?')) return;
  try { await api(`/tasks/${id}`, { method: 'DELETE' }); openTaskIds.delete(id); toast('Đã xóa task'); await loadProfiles(); if (state.selectedProfileId) await loadTasks(state.selectedProfileId, true); }
  catch (err) { toast('Lỗi xóa: ' + err.message); }
}
async function runDue(profileId) {
  try {
    const data = await api(`/profiles/${profileId}/run-due`, { method: 'POST', body: '{}' });
    var msgs = [];
    if (data.started > 0) msgs.push('Đã chạy ' + data.started + ' task');
    if (data.skippedFuture > 0) msgs.push('Bỏ qua ' + data.skippedFuture + ' task chưa tới giờ');
    if (data.invalid && data.invalid.length > 0) msgs.push('\u274c ' + data.invalid.length + ' task lỗi: ' + data.invalid.join('; '));
    toast(msgs.length > 0 ? msgs.join('. ') : 'Không có task nào để chạy');
    await loadProfiles();
  }
  catch (err) { toast('Lỗi khi chạy: ' + err.message); }
}
async function retryTask(taskId) {
  try { await api(`/tasks/${taskId}/retry`, { method: 'POST', body: '{}' }); toast('Đã gửi retry'); await loadProfiles(); if (state.selectedProfileId) await loadTasks(state.selectedProfileId, true); }
  catch (err) { toast('Lỗi retry: ' + err.message); }
}
async function postProfile(profileId, action) {
  try { const r = await api(`/profiles/${profileId}/${action}`, { method: 'POST', body: '{}' }); toast(r.opened === true ? 'Đã mở Chrome' : 'Đang mở Chrome...'); }
  catch (err) { toast('Lỗi: ' + err.message); }
}
function openProfileModal() {
  state.editingProfileId = null;
  $('profileModalTitle').textContent = 'Thêm kênh mới';
  $('profileModalSub').textContent = 'Tạo profile riêng, sau đó check OAuth/YouTube API.';
  $('saveProfileBtn').textContent = 'Tạo kênh';
  $('saveCheckProfileBtn').textContent = 'Tạo & Check API';
  $('newProfileName').value = '';
  $('newProfileJson').value = '';
  $('profileModal').classList.remove('hidden');
  const _inp = $('newProfileName');
  if (_inp) _inp.focus();
}
function editProfile(profileId) {
  const profile = state.profiles.find(p => p.id === profileId);
  if (!profile) return toast('Không tìm thấy kênh');
  state.editingProfileId = profileId;
  $('profileModalTitle').textContent = 'Sửa thông tin kênh';
  $('profileModalSub').textContent = 'Sửa tên profile hoặc đổi file OAuth client JSON.';
  $('saveProfileBtn').textContent = 'Lưu thay đổi';
  $('saveCheckProfileBtn').textContent = 'Lưu & Check API';
  $('newProfileName').value = profile.name || '';
  $('newProfileJson').value = profile.jsonApiPath || '';
  $('profileModal').classList.remove('hidden');
}
function closeProfileModal() { state.editingProfileId = null; $('profileModal').classList.add('hidden'); if (state.activeTab === 'channels') loadProfiles(); }
async function pickProfileJson() { const jsonPath = await window.nativeApi.pickJson(); if (jsonPath) $('newProfileJson').value = jsonPath; }
async function saveProfile(checkNow = false) {
  const name = val('newProfileName').trim();
  const jsonApiPath = val('newProfileJson').trim();
  if (!name) return toast('Vui lòng nhập tên kênh');
  try {
    const isEdit = Boolean(state.editingProfileId);
    const url = isEdit ? `/profiles/${state.editingProfileId}` : '/profiles';
    const data = await api(url, { method: isEdit ? 'PUT' : 'POST', body: JSON.stringify({ name, jsonApiPath }) });
    const profileId = data.profile.id;
    toast(isEdit ? 'Đã lưu thông tin kênh' : 'Đã tạo kênh mới');
    closeProfileModal();
    await loadProfiles();
    if (checkNow && jsonApiPath) {
      toast('Đang kiểm tra kết nối API...');
      await api(`/profiles/${profileId}/check-api`, { method: 'POST', body: JSON.stringify({ jsonApiPath }) });
      toast('Kết nối API thành công');
      await loadProfiles();
    }
  } catch (err) { toast('Lỗi: ' + err.message); }
}
async function deleteProfile(profileId) {
  const profile = state.profiles.find(p => p.id === profileId);
  if (!profile) return;
  const ok = confirm(`Xóa kênh "${profile.name}"?\n\nViệc này sẽ xóa luôn task, video cache và Chrome profile/cookie riêng của kênh này.`);
  if (!ok) return;
  try { await api(`/profiles/${profileId}`, { method: 'DELETE' }); toast('Đã xóa kênh'); if (state.selectedProfileId === profileId) closeTasks(); await loadProfiles(); }
  catch (err) { toast('Lỗi xóa kênh: ' + err.message); }
}
async function checkApi(profileId) {
  const jsonApiPath = await window.nativeApi.pickJson();
  if (!jsonApiPath) return;
  try { toast('Đang kiểm tra kết nối API...'); await api(`/profiles/${profileId}/check-api`, { method: 'POST', body: JSON.stringify({ jsonApiPath }) }); toast('Kết nối API thành công'); await loadProfiles(); }
  catch (err) { toast('Lỗi check API: ' + err.message); }
}
async function switchChannel(profileId, channelId) {
  try {
    toast('Đang chuyển kênh...');
    await api(`/profiles/${profileId}/switch-channel`, { method: 'POST', body: JSON.stringify({ channelId }) });
    toast('Đã chuyển kênh');
    await loadProfiles();
    if (state.selectedProfileId === profileId) await loadTasks(profileId, true);
  } catch (err) { toast('Lỗi chuyển kênh: ' + err.message); }
}
// ─── PHÂN TÍCH ───
async function toggleAnaVideo(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const isOpen = el.classList.contains('open');
  document.querySelectorAll('.ana-video-wrapper.open').forEach(e => e.classList.remove('open'));
  if (!isOpen) el.classList.add('open');
}
// ─── BÁO CÁO ───
async function loadReport() {
  if (state.activeTab !== 'report') return;
  try {
    const data = await api('/statistics/daily');
    // Summary cards
    const today = data.today || {};
    $('rptTotal').textContent = today.total || 0;
    $('rptDone').textContent = today.completed || 0;
    $('rptFailed').textContent = today.failed || 0;
    // Pending comes from upcoming count
    const upc = (data.upcoming || []).length;
    $('rptPending').textContent = upc;
    // 7-day chart
    renderChart(data.days || []);
    // Recent timeline
    renderTimeline(data.recent || []);
    // Upcoming queue
    renderQueue(data.upcoming || []);
  } catch (err) {
    toast('Lỗi tải báo cáo: ' + err.message);
  }
}
function renderChart(days) {
  const container = $('weeklyChart');
  if (!days.length) { container.innerHTML = '<div class="rpt-empty">Chưa có dữ liệu</div>'; return; }
  // Days are most recent first, reverse for left-to-right display
  const reversed = [...days].reverse();
  const maxVal = Math.max(1, ...reversed.map(d => d.total || 0));
  const maxH = 100;
  container.innerHTML = reversed.map((d, i) => {
    const doneH = d.completed ? Math.max(3, (d.completed / maxVal) * maxH) : 0;
    const failH = d.failed ? Math.max(3, (d.failed / maxVal) * maxH) : 0;
    const total = d.total || 0;
    const dayLabel = fmtShortDate(d.date);
    return `<div class="chart-bar-group">
      <div class="chart-bar-value">${total}</div>
      <div class="chart-bars">
        <div class="chart-bar done" style="height:${doneH}px" title="Thành công: ${d.completed}"></div>
        <div class="chart-bar fail" style="height:${failH}px" title="Thất bại: ${d.failed}"></div>
      </div>
      <div class="chart-bar-label">${dayLabel}</div>
    </div>`;
  }).join('');
}
function renderTimeline(recent) {
  const container = $('recentTimeline');
  if (!recent.length) { container.innerHTML = '<div class="rpt-empty">Chưa có dữ liệu upload</div>'; return; }
  container.innerHTML = recent.map(t => {
    const isOk = t.status === 'Completed';
    const profileName = (state.profiles.find(p => p.id === t.profileId) || {}).name || 'Kênh #' + t.profileId;
    const safeChannelName = profileName.replace(/'/g, "\\'");
    const ytLink = t.youtubeUrl ? `
        <div class="timeline-link-row">
          <a class="timeline-link" href="#" onclick="openExternal('${escapeHtml(t.youtubeUrl)}'); return false;" title="Mở trên YouTube">🔗 Mở video</a>
          <button class="btn-copy-link" onclick="event.stopPropagation(); copyToClipboard('${t.youtubeUrl.replace(/'/g, "\\'")}');" title="Sao chép link video">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          </button>
        </div>` : '';
    return `<div class="timeline-item">
      <div class="timeline-dot ${isOk ? 'ok' : 'err'}"></div>
      <div class="timeline-info">
        <div class="timeline-title">${escapeHtml(t.title || 'Video #' + t.id)}</div>
        <div class="timeline-meta">
          <span class="timeline-channel-name">📺 ${escapeHtml(profileName)}</span>
          <button class="btn-copy-link" onclick="event.stopPropagation(); copyToClipboard('${safeChannelName}');" title="Sao chép tên kênh" style="display:inline-flex">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          </button>
          ${isOk ? ytLink : `<span class="timeline-error">❌ ${escapeHtml(t.errorMessage || 'Lỗi không xác định')}</span>`}
        </div>
      </div>
      <span class="timeline-channel">${escapeHtml(profileName)}</span>
      <span class="timeline-time">${fmtTime(t.updatedAt)}</span>
    </div>`;
  }).join('');
}
function renderQueue(upcoming) {
  const container = $('upcomingQueue');
  if (!upcoming.length) { container.innerHTML = '<div class="rpt-empty">Không có video nào trong hàng đợi</div>'; return; }
  container.innerHTML = upcoming.map(t => {
    const profileName = (state.profiles.find(p => p.id === t.profileId) || {}).name || 'Kênh #' + t.profileId;
    return `<div class="queue-item">
      <div class="queue-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>
      <div class="queue-info"><div class="queue-title">${escapeHtml(t.title || 'Video #' + t.id)}</div><div class="queue-meta">${escapeHtml(profileName)}</div></div>
      <span class="queue-schedule">${t.scheduleTime ? fmtDate(t.scheduleTime) : 'Chưa đặt lịch'}</span>
    </div>`;
  }).join('');
}
// ─── CÀI ĐẶT ───
async function loadSettings() {
  if (state.activeTab !== 'settings') return;
  try {
    const data = await api('/settings');
    // Cache
    const cacheMB = ((data.cacheBytes || 0) / (1024 * 1024)).toFixed(1);
    const limitMB = (data.cacheLimitGB || 5) * 1024;
    const pct = Math.min(100, ((data.cacheBytes || 0) / (limitMB * 1024 * 1024)) * 100).toFixed(1);
    $('cacheFill').style.width = pct + '%';
    $('cacheUsed').textContent = cacheMB + ' MB';
    $('cacheStats').innerHTML = `${data.cacheFiles || 0} file · Giới hạn ${data.cacheLimitGB || 5} GB`;
    // App info
    $('infoDataDir').textContent = data.dataDir || '—';
    $('infoProfileCount').textContent = data.profileCount || 0;
    // Total uploaded
    try {
      const sum = await api('/statistics/summary');
      $('infoTotalUploaded').textContent = sum.totalCompleted || 0;
    } catch (e) { $('infoTotalUploaded').textContent = '—'; }
  } catch (err) {
    toast('Lỗi tải cài đặt: ' + err.message);
  }
}
async function clearCache() {
  if (!confirm('Xóa toàn bộ file cache tạm?')) return;
  try {
    const data = await api('/settings/cache/clear', { method: 'POST', body: '{}' });
    const freedMB = ((data.freedBytes || 0) / (1024 * 1024)).toFixed(1);
    toast(`Đã dọn ${data.removed} file · Giải phóng ${freedMB} MB`);
    loadSettings();
  } catch (err) { toast('Lỗi dọn cache: ' + err.message); }
}
// ─── UTILS ───
function val(id) { return document.getElementById(id)?.value || ''; }
function escapeHtml(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function attr(s) { return escapeHtml(s).replace(/'/g, '&#39;'); }
async function openExternal(url) {
  if (window.nativeApi?.openExternal) {
    await window.nativeApi.openExternal(url);
  } else {
    window.open(url, '_blank');
  }
}
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast('✅ Đã sao chép link');
  } catch {
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    toast('✅ Đã sao chép link');
  }
}
function timezoneOptions(selected) {
  const zones = [
    'Asia/Ho_Chi_Minh',
    'Asia/Bangkok',
    'Asia/Singapore',
    'Asia/Kuala_Lumpur',
    'Asia/Jakarta',
    'Asia/Manila',
    'Asia/Tokyo',
    'Asia/Seoul',
    'Asia/Shanghai',
    'Asia/Dubai',
    'Asia/Kolkata',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Europe/Moscow',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Sao_Paulo',
    'Pacific/Auckland',
    'Australia/Sydney',
  ];
  return zones.map(z => `<option value="${z}" ${z === selected ? 'selected' : ''}>${z.replace('_',' ')}</option>`).join('');
}
function fmtSubs(n) {
  const num = Number(n) || 0;
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return String(num);
}
// ─── INIT ───
$('refreshBtn').addEventListener('click', () => {
  if (state.activeTab === 'channels') loadProfiles();
  else if (state.activeTab === 'report') loadReport();
  else if (state.activeTab === 'settings') loadSettings();
});
$('addProfileBtn').addEventListener('click', openProfileModal);
loadProfiles();
setInterval(() => {
  if (state.activeTab === 'channels') loadProfiles();
  else if (state.activeTab === 'report') loadReport();
  else if (state.activeTab === 'settings') loadSettings();
}, 8000);
setInterval(refreshTaskStatusOnly, 3000);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeTasks(); closeProfileModal(); }
});