const API = '';  // same origin

// ── Utilities ─────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  if (r.status === 204) return null;
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 3000);
}

function openModal(title, bodyHTML, onSubmit) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHTML;
  document.getElementById('modal-overlay').style.display = 'flex';
  if (onSubmit) {
    const existing = document.getElementById('modal-submit');
    if (existing) existing.onclick = onSubmit;
  }
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

document.getElementById('modal-close').onclick = closeModal;
document.getElementById('modal-overlay').onclick = (e) => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
};

function badge(text, color) {
  return `<span class="badge badge-${color}">${text}</span>`;
}

function statusBadge(s) {
  const map = { todo: 'blue', in_progress: 'yellow', done: 'green', cancelled: 'gray', active: 'green', archived: 'gray' };
  return badge(s, map[s] || 'gray');
}

function priorityBadge(p) {
  return badge(p, { high: 'red', medium: 'yellow', low: 'blue' }[p] || 'gray');
}

function roleBadge(r) {
  return badge(r, r === 'admin' ? 'purple' : 'blue');
}

// ── Routing ───────────────────────────────────────────────────────────────────

const pages = {};
let currentPage = null;

function navigate(page) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  currentPage = page;
  pages[page]?.();
}

document.querySelectorAll('.nav-item').forEach(el => {
  el.onclick = () => navigate(el.dataset.page);
});

// ── Dashboard ─────────────────────────────────────────────────────────────────

pages.dashboard = async () => {
  document.getElementById('page-title').textContent = 'Dashboard';
  document.getElementById('topbar-actions').innerHTML = '';
  const content = document.getElementById('content');
  content.innerHTML = '<div class="stats" id="stats"></div><div id="recent-tasks"></div>';

  try {
    const [users, projects, tasks] = await Promise.all([
      api('GET', '/users'),
      api('GET', '/projects'),
      api('GET', '/tasks'),
    ]);

    document.getElementById('stats').innerHTML = `
      <div class="stat"><div class="stat-label">Users</div><div class="stat-value">${users.length}</div></div>
      <div class="stat"><div class="stat-label">Projects</div><div class="stat-value">${projects.length}</div></div>
      <div class="stat"><div class="stat-label">Tasks</div><div class="stat-value">${tasks.length}</div></div>
      <div class="stat"><div class="stat-label">Done</div><div class="stat-value" style="color:var(--green)">${tasks.filter(t=>t.status==='done').length}</div></div>
      <div class="stat"><div class="stat-label">In Progress</div><div class="stat-value" style="color:var(--yellow)">${tasks.filter(t=>t.status==='in_progress').length}</div></div>
      <div class="stat"><div class="stat-label">High Priority</div><div class="stat-value" style="color:var(--red)">${tasks.filter(t=>t.priority==='high').length}</div></div>
    `;

    const recent = tasks.slice(0, 8);
    document.getElementById('recent-tasks').innerHTML = `
      <div class="section-header"><h2>Recent Tasks</h2></div>
      ${recent.length ? `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Project</th></tr></thead>
          <tbody>
            ${recent.map(t => `
              <tr>
                <td>${t.title}</td>
                <td>${statusBadge(t.status)}</td>
                <td>${priorityBadge(t.priority)}</td>
                <td><span style="color:var(--text-dim);font-size:11px">${t.project_id.slice(0,8)}…</span></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>` : '<div class="empty"><div class="empty-icon">📋</div><p>No tasks yet. Create a project and add some tasks.</p></div>'}
    `;
  } catch (e) {
    content.innerHTML = `<div class="card"><p style="color:var(--red)">${e.message}</p></div>`;
  }
};

// ── Users ─────────────────────────────────────────────────────────────────────

pages.users = async () => {
  document.getElementById('page-title').textContent = 'Users';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-primary" id="btn-add-user">+ Add User</button>`;

  document.getElementById('btn-add-user').onclick = () => showUserForm();

  await renderUsers();
};

async function renderUsers(roleFilter = '') {
  const content = document.getElementById('content');
  let users = await api('GET', '/users' + (roleFilter ? `?role=${roleFilter}` : ''));

  content.innerHTML = `
    <div class="filter-bar">
      <select id="filter-role">
        <option value="">All roles</option>
        <option value="member" ${roleFilter==='member'?'selected':''}>Member</option>
        <option value="admin" ${roleFilter==='admin'?'selected':''}>Admin</option>
      </select>
    </div>
    ${users.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th></th></tr></thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td><strong>${u.name}</strong></td>
              <td style="color:var(--text-dim)">${u.email}</td>
              <td>${roleBadge(u.role)}</td>
              <td style="color:var(--text-dim);font-size:12px">${new Date(u.created_at).toLocaleDateString()}</td>
              <td>
                <button class="btn btn-ghost btn-sm" onclick="showUserForm('${u.id}')">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteUser('${u.id}')">Delete</button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>` : '<div class="empty"><div class="empty-icon">👤</div><p>No users yet.</p></div>'}
  `;

  document.getElementById('filter-role').onchange = (e) => renderUsers(e.target.value);
}

async function showUserForm(id = null) {
  let user = id ? await api('GET', `/users/${id}`) : null;
  openModal(id ? 'Edit User' : 'Add User', `
    <div class="form-group"><label>Name</label><input id="f-name" value="${user?.name||''}" placeholder="Full name" /></div>
    <div class="form-group"><label>Email</label><input id="f-email" type="email" value="${user?.email||''}" placeholder="user@example.com" ${id?'disabled':''}/></div>
    <div class="form-group"><label>Role</label>
      <select id="f-role">
        <option value="member" ${user?.role==='member'?'selected':''}>Member</option>
        <option value="admin" ${user?.role==='admin'?'selected':''}>Admin</option>
      </select>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="modal-submit">Save</button>
    </div>
  `);

  document.getElementById('modal-submit').onclick = async () => {
    const body = { name: document.getElementById('f-name').value, role: document.getElementById('f-role').value };
    if (!id) body.email = document.getElementById('f-email').value;
    try {
      if (id) await api('PUT', `/users/${id}`, body);
      else await api('POST', '/users', body);
      closeModal(); toast(id ? 'User updated' : 'User created');
      await renderUsers();
    } catch (e) { toast(e.message, 'error'); }
  };
}

async function deleteUser(id) {
  if (!confirm('Delete this user?')) return;
  try { await api('DELETE', `/users/${id}`); toast('User deleted'); await renderUsers(); }
  catch (e) { toast(e.message, 'error'); }
}

// ── Projects ──────────────────────────────────────────────────────────────────

pages.projects = async () => {
  document.getElementById('page-title').textContent = 'Projects';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-primary" id="btn-add-project">+ New Project</button>`;
  document.getElementById('btn-add-project').onclick = () => showProjectForm();
  await renderProjects();
};

async function renderProjects(statusFilter = '') {
  const content = document.getElementById('content');
  const [projects, users] = await Promise.all([
    api('GET', '/projects' + (statusFilter ? `?status=${statusFilter}` : '')),
    api('GET', '/users'),
  ]);
  const userMap = Object.fromEntries(users.map(u => [u.id, u.name]));

  content.innerHTML = `
    <div class="filter-bar">
      <select id="filter-status">
        <option value="">All statuses</option>
        <option value="active" ${statusFilter==='active'?'selected':''}>Active</option>
        <option value="archived" ${statusFilter==='archived'?'selected':''}>Archived</option>
      </select>
    </div>
    ${projects.length ? `
    <div class="card-grid">
      ${projects.map(p => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <strong style="font-size:15px">${p.name}</strong>
            ${statusBadge(p.status)}
          </div>
          <div style="color:var(--text-dim);font-size:13px;margin-bottom:14px">${p.description || 'No description'}</div>
          <div style="font-size:12px;color:var(--text-dim);margin-bottom:14px">Owner: <span style="color:var(--text)">${userMap[p.owner_id] || 'Unknown'}</span></div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-ghost btn-sm" onclick="showProjectForm('${p.id}')">Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProject('${p.id}')">Delete</button>
          </div>
        </div>`).join('')}
    </div>` : '<div class="empty"><div class="empty-icon">📁</div><p>No projects yet.</p></div>'}
  `;

  document.getElementById('filter-status').onchange = (e) => renderProjects(e.target.value);
}

async function showProjectForm(id = null) {
  const [project, users] = await Promise.all([
    id ? api('GET', `/projects/${id}`) : Promise.resolve(null),
    api('GET', '/users'),
  ]);
  const userOpts = users.map(u => `<option value="${u.id}" ${project?.owner_id===u.id?'selected':''}>${u.name}</option>`).join('');

  openModal(id ? 'Edit Project' : 'New Project', `
    <div class="form-group"><label>Name</label><input id="f-name" value="${project?.name||''}" placeholder="Project name" /></div>
    <div class="form-group"><label>Description</label><textarea id="f-desc" placeholder="What is this project about?">${project?.description||''}</textarea></div>
    <div class="form-row">
      <div class="form-group"><label>Owner</label><select id="f-owner">${userOpts}</select></div>
      <div class="form-group"><label>Status</label>
        <select id="f-status">
          <option value="active" ${project?.status==='active'?'selected':''}>Active</option>
          <option value="archived" ${project?.status==='archived'?'selected':''}>Archived</option>
        </select>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="modal-submit">Save</button>
    </div>
  `);

  document.getElementById('modal-submit').onclick = async () => {
    const body = {
      name: document.getElementById('f-name').value,
      description: document.getElementById('f-desc').value || null,
      owner_id: document.getElementById('f-owner').value,
      status: document.getElementById('f-status').value,
    };
    try {
      if (id) await api('PUT', `/projects/${id}`, body);
      else await api('POST', '/projects', body);
      closeModal(); toast(id ? 'Project updated' : 'Project created');
      await renderProjects();
    } catch (e) { toast(e.message, 'error'); }
  };
}

async function deleteProject(id) {
  if (!confirm('Delete this project?')) return;
  try { await api('DELETE', `/projects/${id}`); toast('Project deleted'); await renderProjects(); }
  catch (e) { toast(e.message, 'error'); }
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

pages.tasks = async () => {
  document.getElementById('page-title').textContent = 'Tasks';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-primary" id="btn-add-task">+ New Task</button>`;
  document.getElementById('btn-add-task').onclick = () => showTaskForm();
  await renderTasks();
};

async function renderTasks(filters = {}) {
  const content = document.getElementById('content');
  const qs = new URLSearchParams(Object.fromEntries(Object.entries(filters).filter(([,v])=>v))).toString();
  const [tasks, users, projects] = await Promise.all([
    api('GET', '/tasks' + (qs ? '?'+qs : '')),
    api('GET', '/users'),
    api('GET', '/projects'),
  ]);
  const userMap = Object.fromEntries(users.map(u => [u.id, u.name]));
  const projMap = Object.fromEntries(projects.map(p => [p.id, p.name]));
  const projectOpts = `<option value="">All projects</option>` + projects.map(p => `<option value="${p.id}" ${filters.project_id===p.id?'selected':''}>${p.name}</option>`).join('');
  const userOpts = `<option value="">All assignees</option>` + users.map(u => `<option value="${u.id}" ${filters.assignee_id===u.id?'selected':''}>${u.name}</option>`).join('');

  content.innerHTML = `
    <div class="filter-bar">
      <select id="f-project">${projectOpts}</select>
      <select id="f-assignee">${userOpts}</select>
      <select id="f-status">
        <option value="">All statuses</option>
        ${['todo','in_progress','done','cancelled'].map(s=>`<option value="${s}" ${filters.status===s?'selected':''}>${s.replace('_',' ')}</option>`).join('')}
      </select>
      <select id="f-priority">
        <option value="">All priorities</option>
        ${['low','medium','high'].map(p=>`<option value="${p}" ${filters.priority===p?'selected':''}>${p}</option>`).join('')}
      </select>
    </div>
    ${tasks.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Title</th><th>Project</th><th>Assignee</th><th>Status</th><th>Priority</th><th>Due</th><th></th></tr></thead>
        <tbody>
          ${tasks.map(t => `
            <tr>
              <td><strong>${t.title}</strong>${t.description?`<div style="color:var(--text-dim);font-size:11px;margin-top:2px">${t.description.slice(0,50)}${t.description.length>50?'…':''}</div>`:''}</td>
              <td style="color:var(--text-dim);font-size:12px">${projMap[t.project_id]||'—'}</td>
              <td style="font-size:12px">${userMap[t.assignee_id]||'<span style="color:var(--text-dim)">Unassigned</span>'}</td>
              <td>${statusBadge(t.status)}</td>
              <td>${priorityBadge(t.priority)}</td>
              <td style="color:var(--text-dim);font-size:12px">${t.due_date||'—'}</td>
              <td>
                <button class="btn btn-ghost btn-sm" onclick="showTaskForm('${t.id}')">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteTask('${t.id}')">Delete</button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>` : '<div class="empty"><div class="empty-icon">✅</div><p>No tasks match the filters.</p></div>'}
  `;

  const applyFilters = () => renderTasks({
    project_id: document.getElementById('f-project').value,
    assignee_id: document.getElementById('f-assignee').value,
    status: document.getElementById('f-status').value,
    priority: document.getElementById('f-priority').value,
  });
  ['f-project','f-assignee','f-status','f-priority'].forEach(id => {
    document.getElementById(id).onchange = applyFilters;
  });
}

async function showTaskForm(id = null) {
  const [task, users, projects] = await Promise.all([
    id ? api('GET', `/tasks/${id}`) : Promise.resolve(null),
    api('GET', '/users'),
    api('GET', '/projects'),
  ]);

  const projOpts = projects.map(p => `<option value="${p.id}" ${task?.project_id===p.id?'selected':''}>${p.name}</option>`).join('');
  const userOpts = `<option value="">Unassigned</option>` + users.map(u => `<option value="${u.id}" ${task?.assignee_id===u.id?'selected':''}>${u.name}</option>`).join('');
  const statusOpts = ['todo','in_progress','done','cancelled'].map(s => `<option value="${s}" ${(task?.status||'todo')===s?'selected':''}>${s.replace('_',' ')}</option>`).join('');
  const priorityOpts = ['low','medium','high'].map(p => `<option value="${p}" ${(task?.priority||'medium')===p?'selected':''}>${p}</option>`).join('');

  openModal(id ? 'Edit Task' : 'New Task', `
    <div class="form-group"><label>Title</label><input id="f-title" value="${task?.title||''}" placeholder="Task title" /></div>
    <div class="form-group"><label>Description</label><textarea id="f-desc" placeholder="Optional details">${task?.description||''}</textarea></div>
    <div class="form-group"><label>Project</label><select id="f-project">${projOpts}</select></div>
    <div class="form-group"><label>Assignee</label><select id="f-assignee">${userOpts}</select></div>
    <div class="form-row">
      <div class="form-group"><label>Status</label><select id="f-status">${statusOpts}</select></div>
      <div class="form-group"><label>Priority</label><select id="f-priority">${priorityOpts}</select></div>
    </div>
    <div class="form-group"><label>Due Date</label><input id="f-due" type="date" value="${task?.due_date||''}" /></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="modal-submit">Save</button>
    </div>
  `);

  document.getElementById('modal-submit').onclick = async () => {
    const body = {
      title: document.getElementById('f-title').value,
      description: document.getElementById('f-desc').value || null,
      project_id: document.getElementById('f-project').value,
      assignee_id: document.getElementById('f-assignee').value || null,
      status: document.getElementById('f-status').value,
      priority: document.getElementById('f-priority').value,
      due_date: document.getElementById('f-due').value || null,
    };
    try {
      if (id) await api('PUT', `/tasks/${id}`, body);
      else await api('POST', '/tasks', body);
      closeModal(); toast(id ? 'Task updated' : 'Task created');
      await renderTasks();
    } catch (e) { toast(e.message, 'error'); }
  };
}

async function deleteTask(id) {
  if (!confirm('Delete this task?')) return;
  try { await api('DELETE', `/tasks/${id}`); toast('Task deleted'); await renderTasks(); }
  catch (e) { toast(e.message, 'error'); }
}

// ── Weather ───────────────────────────────────────────────────────────────────

pages.weather = async () => {
  document.getElementById('page-title').textContent = 'Weather';
  document.getElementById('topbar-actions').innerHTML = '';
  document.getElementById('content').innerHTML = `
    <div class="search-bar">
      <input id="city-input" placeholder="Enter city name…" />
      <button class="btn btn-primary" id="btn-search-city">Search</button>
    </div>
    <div id="weather-result"></div>
    <div style="margin-top:24px">
      <div class="section-header"><h2>Quick Presets</h2></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        ${['New York','London','Tokyo','Paris','Sydney','Mumbai'].map(c =>
          `<button class="btn btn-ghost" onclick="fetchWeatherCity('${c}')">${c}</button>`).join('')}
      </div>
    </div>
  `;
  document.getElementById('btn-search-city').onclick = () => fetchWeatherCity(document.getElementById('city-input').value);
  document.getElementById('city-input').onkeydown = (e) => e.key === 'Enter' && fetchWeatherCity(document.getElementById('city-input').value);
};

async function fetchWeatherCity(city) {
  const el = document.getElementById('weather-result');
  if (!city.trim()) return;
  el.innerHTML = '<p style="color:var(--text-dim)">Fetching…</p>';
  try {
    const d = await api('GET', `/external/weather/city?city=${encodeURIComponent(city)}`);
    const w = d.weather;
    const wmoDesc = { 0:'Clear sky', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast', 45:'Fog', 51:'Drizzle', 61:'Rain', 71:'Snow', 80:'Rain showers', 95:'Thunderstorm' };
    el.innerHTML = `
      <div class="weather-card">
        <div style="color:var(--text-dim);margin-bottom:8px">${d.city}, ${d.country||''}</div>
        <div style="display:flex;align-items:flex-end;gap:16px">
          <div class="weather-temp">${Math.round(w.temperature_2m)}°C</div>
          <div style="color:var(--text-dim);padding-bottom:10px">${wmoDesc[w.weathercode]||'—'}</div>
        </div>
        <div class="weather-meta">
          <span>💨 ${w.windspeed_10m} km/h</span>
          <span>💧 ${w.relativehumidity_2m}%</span>
          <span>📍 ${d.latitude.toFixed(2)}, ${d.longitude.toFixed(2)}</span>
        </div>
      </div>
    `;
  } catch (e) { el.innerHTML = `<p style="color:var(--red)">${e.message}</p>`; }
}

// ── Countries ─────────────────────────────────────────────────────────────────

pages.countries = async () => {
  document.getElementById('page-title').textContent = 'Countries';
  document.getElementById('topbar-actions').innerHTML = '';
  document.getElementById('content').innerHTML = `
    <div class="filter-bar" style="margin-bottom:20px">
      <input id="country-search" placeholder="Search by name…" />
      <select id="region-filter">
        <option value="">All regions</option>
        ${['Africa','Americas','Asia','Europe','Oceania'].map(r=>`<option value="${r}">${r}</option>`).join('')}
      </select>
    </div>
    <div id="countries-result"><p style="color:var(--text-dim)">Loading…</p></div>
  `;
  document.getElementById('region-filter').onchange = (e) => fetchCountries(e.target.value, document.getElementById('country-search').value);
  document.getElementById('country-search').oninput = (e) => fetchCountries(document.getElementById('region-filter').value, e.target.value);
  fetchCountries();
};

let _countriesCache = [];

async function fetchCountries(region = '', search = '') {
  const el = document.getElementById('countries-result');
  if (!_countriesCache.length) {
    try {
      _countriesCache = await api('GET', '/external/countries');
    } catch (e) { el.innerHTML = `<p style="color:var(--red)">${e.message}</p>`; return; }
  }
  let data = _countriesCache;
  if (region) data = data.filter(c => c.region === region);
  if (search) data = data.filter(c => c.name?.toLowerCase().includes(search.toLowerCase()));
  data = data.slice(0, 60);
  el.innerHTML = `
    <div style="color:var(--text-dim);font-size:12px;margin-bottom:12px">${data.length} countries shown</div>
    <div class="country-grid">
      ${data.map(c => `
        <div class="country-card">
          ${c.flag ? `<img class="country-flag" src="${c.flag}" alt="${c.name}" />` : ''}
          <div><strong>${c.name}</strong></div>
          <div style="color:var(--text-dim);font-size:12px">Capital: ${c.capital||'—'}</div>
          <div style="color:var(--text-dim);font-size:12px">Pop: ${c.population?.toLocaleString()||'—'}</div>
          <div style="font-size:11px">${c.currencies?.join(', ')||'—'}</div>
        </div>`).join('')}
    </div>
  `;
}

// ── Crypto ────────────────────────────────────────────────────────────────────

pages.crypto = async () => {
  document.getElementById('page-title').textContent = 'Crypto';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-ghost" id="btn-refresh-crypto">↻ Refresh</button>`;
  document.getElementById('content').innerHTML = `
    <div id="crypto-prices"><p style="color:var(--text-dim)">Loading…</p></div>
    <div style="margin-top:28px">
      <div class="section-header"><h2>Trending</h2></div>
      <div id="crypto-trending"><p style="color:var(--text-dim)">Loading…</p></div>
    </div>
  `;
  document.getElementById('btn-refresh-crypto').onclick = loadCrypto;
  loadCrypto();
};

async function loadCrypto() {
  try {
    const [prices, trending] = await Promise.all([
      api('GET', '/external/crypto/prices?coins=bitcoin,ethereum,solana,cardano,polkadot&currency=usd'),
      api('GET', '/external/crypto/trending'),
    ]);

    document.getElementById('crypto-prices').innerHTML = `
      <div class="section-header"><h2>Live Prices</h2></div>
      ${Object.entries(prices).map(([coin, data]) => `
        <div class="coin-row">
          <div class="coin-name" style="text-transform:capitalize">${coin}</div>
          <div style="text-align:right">
            <div class="coin-price">$${data.usd?.toLocaleString() || '—'}</div>
            <div class="${data.usd_24h_change >= 0 ? 'change-up' : 'change-down'}">
              ${data.usd_24h_change >= 0 ? '▲' : '▼'} ${Math.abs(data.usd_24h_change || 0).toFixed(2)}%
            </div>
          </div>
        </div>`).join('')}
    `;

    document.getElementById('crypto-trending').innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Symbol</th><th>Market Cap Rank</th></tr></thead>
          <tbody>
            ${trending.map(c => `
              <tr>
                <td>${c.thumb ? `<img src="${c.thumb}" style="width:20px;vertical-align:middle;margin-right:8px" />` : ''}${c.name}</td>
                <td>${badge(c.symbol,'gray')}</td>
                <td style="color:var(--text-dim)">#${c.market_cap_rank||'—'}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    document.getElementById('crypto-prices').innerHTML = `<p style="color:var(--red)">${e.message}</p>`;
  }
}

// ── Jokes ─────────────────────────────────────────────────────────────────────

pages.jokes = async () => {
  document.getElementById('page-title').textContent = 'Jokes';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-primary" id="btn-more-jokes">Load More</button>`;
  document.getElementById('content').innerHTML = `<div id="jokes-list"></div>`;
  document.getElementById('btn-more-jokes').onclick = loadMoreJokes;
  loadMoreJokes();
};

async function loadMoreJokes() {
  const el = document.getElementById('jokes-list');
  try {
    const jokes = await api('GET', '/external/jokes/ten');
    el.innerHTML += jokes.map(j => `
      <div class="joke-card">
        <div class="joke-setup">${j.setup}</div>
        <div class="joke-punchline">— ${j.punchline}</div>
      </div>`).join('');
  } catch (e) { el.innerHTML = `<p style="color:var(--red)">${e.message}</p>`; }
}

// ── Dogs ──────────────────────────────────────────────────────────────────────

pages.dogs = async () => {
  document.getElementById('page-title').textContent = 'Dogs';
  document.getElementById('topbar-actions').innerHTML =
    `<button class="btn btn-primary" id="btn-more-dogs">More Dogs</button>`;
  document.getElementById('content').innerHTML = `
    <div class="filter-bar" style="margin-bottom:20px">
      <select id="breed-select"><option value="">Random (any breed)</option></select>
      <button class="btn btn-ghost" id="btn-search-breed">Fetch</button>
    </div>
    <div id="dog-grid" class="dog-grid"></div>
  `;

  // Load breed list
  try {
    const { breeds } = await api('GET', '/external/dogs/breeds');
    const sel = document.getElementById('breed-select');
    breeds.forEach(b => sel.innerHTML += `<option value="${b}">${b}</option>`);
  } catch {}

  document.getElementById('btn-more-dogs').onclick = fetchDogs;
  document.getElementById('btn-search-breed').onclick = fetchDogs;
  fetchDogs();
};

async function fetchDogs() {
  const el = document.getElementById('dog-grid');
  const breed = document.getElementById('breed-select')?.value;
  el.innerHTML = '<p style="color:var(--text-dim)">Fetching…</p>';
  try {
    let urls = [];
    if (breed) {
      const data = await api('GET', `/external/dogs/breed/${breed}?count=9`);
      urls = data.message || [];
    } else {
      const results = await Promise.all(Array.from({length: 9}, () => api('GET', '/external/dogs/random')));
      urls = results.map(r => r.message);
    }
    el.innerHTML = urls.map(url => `<img class="dog-img" src="${url}" loading="lazy" />`).join('');
  } catch (e) { el.innerHTML = `<p style="color:var(--red)">${e.message}</p>`; }
}

// ── Boot ──────────────────────────────────────────────────────────────────────
navigate('dashboard');
