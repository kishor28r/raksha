/**
 * RAKSHA: AI-Powered Emergency Response & Resource Allocation System
 * Frontend Application & Real-time Leaflet Tactical Map Controller
 */

// Application State
const state = {
  incidents: [],
  units: [],
  allocations: [],
  benchmark: null,
  systemStatus: null,
  map: null,
  markers: {
    incidents: {},
    units: {},
    polylines: {}
  },
  activeTab: 'tab-allocations',
  simRunning: false,
  simTimer: null
};

// Emoji & Icon Lookup
const UNIT_ICONS = {
  AMBULANCE: '🚑',
  FIRE_TRUCK: '🚒',
  RESCUE_SQUAD: '🚤',
  POLICE_PATROL: '🚓',
  MULTI_HAZARD: '🛡️'
};

const INCIDENT_ICONS = {
  FIRE: '🔥',
  FLOOD: '🌊',
  ACCIDENT: '🚗',
  MEDICAL_TRAUMA: '🏥',
  BUILDING_COLLAPSE: '🏚️',
  GAS_LEAK: '💨',
  HAZMAT: '☣️'
};

const SEV_COLORS = {
  CRITICAL: '#ff2d55',
  HIGH: '#ff9500',
  MEDIUM: '#ffd60a',
  LOW: '#30d158'
};


// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  bindEvents();
  refreshAllData();
  
  // Polling loop for live telemetry updates
  setInterval(refreshTelemetry, 2000);
});


// ==========================================================================
// Map Setup & Rendering
// ==========================================================================
function initMap() {
  const defaultCenter = [28.6139, 77.2090]; // Delhi NCR
  state.map = L.map('map', {
    zoomControl: false,
    attributionControl: false
  }).setView(defaultCenter, 13);

  // Add Zoom Control at top right
  L.control.zoom({ position: 'topright' }).addTo(state.map);

  // 1. Google Maps Streets (Clear Roads, Landmarks & Buildings)
  const googleStreets = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
    attribution: '&copy; Google Maps'
  });

  // 2. Google Maps Hybrid / Satellite (Satellite imagery + road labels)
  const googleHybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
    attribution: '&copy; Google Maps Satellite'
  });

  // 3. OpenStreetMap Standard
  const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  });

  // 4. Carto Dark Matter (Dark Tactical)
  const cartoDark = L.tileLayer('https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; CARTO'
  });

  // Set Google Maps as default active layer
  googleStreets.addTo(state.map);

  // Add Leaflet Layer Switcher Control
  const baseMaps = {
    "🗺️ Google Maps": googleStreets,
    "🛰️ Google Satellite": googleHybrid,
    "🌐 OpenStreetMap": osmLayer,
    "🌙 Dark Mode": cartoDark
  };
  L.control.layers(baseMaps, null, { position: 'topright' }).addTo(state.map);

  // Force map size refresh
  setTimeout(() => {
    state.map.invalidateSize();
  }, 200);

  window.addEventListener('resize', () => {
    state.map.invalidateSize();
  });

  // Map Click Handler to pick coordinates for SOS Intake
  state.map.on('click', (e) => {
    const lat = e.latlng.lat.toFixed(5);
    const lng = e.latlng.lng.toFixed(5);
    document.getElementById('sosLat').value = lat;
    document.getElementById('sosLng').value = lng;
    document.getElementById('sosAddress').value = `Map Pin Location (${lat}, ${lng})`;
    openSosModal();
  });
}

function updateMapMarkers() {
  if (!state.map) return;

  // 1. Render/Update Incident Markers
  const currentIncIds = new Set(state.incidents.map(i => i.id));
  
  // Remove resolved/deleted incident markers
  for (const incId in state.markers.incidents) {
    if (!currentIncIds.has(incId) || state.incidents.find(i => i.id === incId)?.status === 'RESOLVED') {
      state.map.removeLayer(state.markers.incidents[incId]);
      delete state.markers.incidents[incId];
    }
  }

  // Draw active incident radar markers
  state.incidents.forEach(inc => {
    if (inc.status === 'RESOLVED') return;

    const sevColor = SEV_COLORS[inc.severity.level] || '#38bdf8';
    const iconEmoji = INCIDENT_ICONS[inc.type] || '🚨';
    const isCritical = inc.severity.level === 'CRITICAL';

    const customIcon = L.divIcon({
      className: 'radar-pulse-container',
      html: `
        <div class="radar-pulse-marker" style="color: ${sevColor}">
          <div class="pulse-ring"></div>
          <div class="pulse-core" style="background-color: ${sevColor}; display:flex; align-items:center; justify-content:center; font-size:11px;">
            ${iconEmoji}
          </div>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    });

    const popupHtml = `
      <div style="font-family: Outfit, sans-serif; color: #fff; background: #0e1526; padding: 10px; border-radius: 8px; min-width: 200px; border: 1px solid rgba(255,255,255,0.1);">
        <div style="font-size: 11px; font-weight: bold; color: ${sevColor}; text-transform: uppercase;">${inc.severity.level} (${(inc.severity.final_score).toFixed(2)})</div>
        <div style="font-size: 13px; font-weight: bold; margin: 4px 0;">${inc.title}</div>
        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px;">${inc.description.slice(0, 100)}...</div>
        <div style="font-size: 10px; color: #38bdf8; font-family: monospace;">Source: ${inc.source} | Casualties: ${inc.severity.extracted_casualties}</div>
        ${inc.assigned_unit_id ? `<div style="margin-top: 6px; font-size: 11px; color: #30d158; font-weight: bold;">Dispatched Unit: ${inc.assigned_unit_id}</div>` : ''}
        <button onclick="resolveIncidentDirect('${inc.id}')" style="margin-top: 8px; width: 100%; background: #16a34a; color: #fff; border: none; padding: 5px; border-radius: 4px; font-size: 11px; cursor: pointer;">Mark Resolved</button>
      </div>
    `;

    if (state.markers.incidents[inc.id]) {
      state.markers.incidents[inc.id].setLatLng([inc.location.lat, inc.location.lng]);
    } else {
      const marker = L.marker([inc.location.lat, inc.location.lng], { icon: customIcon })
        .bindPopup(popupHtml)
        .addTo(state.map);
      state.markers.incidents[inc.id] = marker;
    }
  });

  // 2. Render/Update Unit Fleet Markers
  state.units.forEach(unit => {
    const unitEmoji = UNIT_ICONS[unit.type] || '🚑';
    const statusClass = unit.status === 'EN_ROUTE' ? 'en-route' : unit.status === 'ON_SCENE' ? 'on-scene' : '';

    const unitIcon = L.divIcon({
      className: 'unit-marker-wrapper',
      html: `
        <div class="unit-vehicle-marker ${statusClass}" title="${unit.name} (${unit.status})">
          ${unitEmoji}
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const unitPopupHtml = `
      <div style="font-family: Outfit, sans-serif; color: #fff; background: #0e1526; padding: 10px; border-radius: 8px; min-width: 190px;">
        <div style="font-size: 13px; font-weight: bold;">${unit.name}</div>
        <div style="font-size: 11px; color: #38bdf8; font-family: monospace;">Type: ${unit.type} | Speed: ${unit.speed_kmh}km/h</div>
        <div style="font-size: 11px; color: #94a3b8; margin: 4px 0;">Base: ${unit.base_location.address || 'Base Post'}</div>
        <div style="font-size: 11px; font-weight: bold; color: ${unit.status === 'AVAILABLE' ? '#30d158' : '#ff9500'};">Status: ${unit.status}</div>
        <button onclick="resetUnitDirect('${unit.id}')" style="margin-top: 8px; width: 100%; background: #334155; color: #fff; border: none; padding: 4px; border-radius: 4px; font-size: 10px; cursor: pointer;">Reset to Base</button>
      </div>
    `;

    if (state.markers.units[unit.id]) {
      state.markers.units[unit.id].setLatLng([unit.location.lat, unit.location.lng]);
    } else {
      const marker = L.marker([unit.location.lat, unit.location.lng], { icon: unitIcon })
        .bindPopup(unitPopupHtml)
        .addTo(state.map);
      state.markers.units[unit.id] = marker;
    }
  });

  // 3. Render/Update Dynamic Polyline Route Connectors for En-Route / Dispatched Units
  // Clear old polylines
  for (const key in state.markers.polylines) {
    state.map.removeLayer(state.markers.polylines[key]);
    delete state.markers.polylines[key];
  }

  // Draw routes for units with target incidents
  state.units.forEach(u => {
    if (u.assigned_incident_id && u.status === 'EN_ROUTE') {
      const inc = state.incidents.find(i => i.id === u.assigned_incident_id);
      if (inc) {
        const polyline = L.polyline(
          [[u.location.lat, u.location.lng], [inc.location.lat, inc.location.lng]],
          {
            color: '#38bdf8',
            weight: 3,
            opacity: 0.85,
            dashArray: '6, 8',
            lineCap: 'round'
          }
        ).addTo(state.map);
        state.markers.polylines[u.id] = polyline;
      }
    }
  });
}


// ==========================================================================
// Data Fetching & API Services
// ==========================================================================
async function refreshAllData() {
  await Promise.all([
    fetchStatus(),
    fetchIncidents(),
    fetchUnits(),
    fetchOptimizations(),
    fetchBenchmark()
  ]);
  updateMapMarkers();
  renderAllocations();
  renderIncidentsList();
  renderFleetList();
}

async function refreshTelemetry() {
  try {
    const [incRes, unitRes, optRes, bmRes] = await Promise.all([
      fetch('/api/incidents'),
      fetch('/api/units'),
      fetch('/api/optimize'),
      fetch('/api/benchmark')
    ]);

    state.incidents = await incRes.json();
    state.units = await unitRes.json();
    const optData = await optRes.json();
    state.allocations = optData.allocations || [];
    state.benchmark = await bmRes.json();

    updateHeaderStats();
    updateMapMarkers();
    renderAllocations();
    renderIncidentsList();
    renderFleetList();
    renderBenchmark();
  } catch (err) {
    console.error('Telemetry refresh error:', err);
  }
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    state.systemStatus = await res.json();
    updateHeaderStats();
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

async function fetchIncidents() {
  try {
    const res = await fetch('/api/incidents');
    state.incidents = await res.json();
  } catch (err) {
    console.error('Error fetching incidents:', err);
  }
}

async function fetchUnits() {
  try {
    const res = await fetch('/api/units');
    state.units = await res.json();
  } catch (err) {
    console.error('Error fetching units:', err);
  }
}

async function fetchOptimizations() {
  try {
    const res = await fetch('/api/optimize');
    const data = await res.json();
    state.allocations = data.allocations || [];
  } catch (err) {
    console.error('Error fetching optimizations:', err);
  }
}

async function fetchBenchmark() {
  try {
    const res = await fetch('/api/benchmark');
    state.benchmark = await res.json();
    renderBenchmark();
  } catch (err) {
    console.error('Error fetching benchmark:', err);
  }
}


// ==========================================================================
// UI Rendering Functions
// ==========================================================================
function updateHeaderStats() {
  const activeInc = state.incidents.filter(i => i.status !== 'RESOLVED');
  const criticalCount = activeInc.filter(i => i.severity.level === 'CRITICAL').length;
  const availUnits = state.units.filter(u => u.status === 'AVAILABLE').length;
  const enRouteUnits = state.units.filter(u => u.status === 'EN_ROUTE').length;

  document.getElementById('statCritical').textContent = criticalCount;
  document.getElementById('statActive').textContent = activeInc.length;
  document.getElementById('statUnitsAvail').textContent = availUnits;
  document.getElementById('statEnRoute').textContent = enRouteUnits;

  document.getElementById('badgeAllocCount').textContent = state.allocations.length;
  document.getElementById('badgeIncCount').textContent = activeInc.length;
  document.getElementById('badgeFleetCount').textContent = state.units.length;
  document.getElementById('incidentStreamStats').textContent = `${activeInc.length} active emergencies`;

  const btnAcceptAll = document.getElementById('btnAcceptAll');
  btnAcceptAll.style.display = state.allocations.length > 0 ? 'inline-flex' : 'none';
}

function renderAllocations() {
  const container = document.getElementById('allocationsList');
  if (!container) return;

  if (state.allocations.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🛡️</div>
        <p class="empty-text">No active emergencies awaiting dispatch.</p>
        <p class="empty-sub">Load a disaster scenario above or click "+ New SOS" to begin.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.allocations.map(alloc => {
    const sevClass = alloc.severity_level.toLowerCase();
    const inc = state.incidents.find(i => i.id === alloc.incident_id);
    const unit = state.units.find(u => u.id === alloc.unit_id);
    const unitEmoji = UNIT_ICONS[alloc.unit_type] || '🚑';
    const incEmoji = INCIDENT_ICONS[inc?.type] || '🚨';

    return `
      <div class="card ${sevClass}-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-title">${incEmoji} ${alloc.incident_title}</div>
            <div class="card-loc">📍 ${inc?.location?.address || 'City Zone'} (${alloc.incident_id})</div>
          </div>
          <span class="sev-badge sev-${sevClass}">${alloc.severity_level} (${alloc.severity_score.toFixed(2)})</span>
        </div>

        <div class="match-box">
          <div class="match-unit">
            <div class="unit-icon-pill">${unitEmoji}</div>
            <div class="unit-details">
              <span class="unit-name">${alloc.unit_name}</span>
              <span class="unit-meta">${alloc.distance_km.toFixed(1)} km away • ${alloc.unit_type}</span>
            </div>
          </div>
          <div class="match-stats">
            <span class="eta-highlight">ETA ~${alloc.eta_minutes.toFixed(1)} min</span>
            <span class="conf-pill">${alloc.match_confidence_pct}% Match Confidence</span>
          </div>
        </div>

        <div class="ai-reasoning">
          💡 <strong>AI Rationale:</strong> ${alloc.reasoning}
        </div>

        <div class="card-actions">
          <button class="hud-btn hud-btn-success hud-btn-sm" style="flex:1;" onclick="acceptDispatchDirect('${alloc.incident_id}', '${alloc.unit_id}')">
            ✓ Dispatch ${alloc.unit_name}
          </button>
          <button class="hud-btn hud-btn-outline hud-btn-sm" onclick="openOverrideModal('${alloc.incident_id}', '${alloc.incident_title}')">
            Override
          </button>
          <button class="hud-btn hud-btn-ghost hud-btn-sm" onclick="panToIncident('${alloc.incident_id}')" title="Center map on incident">
            🎯 View
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderIncidentsList() {
  const container = document.getElementById('incidentsList');
  if (!container) return;

  const activeInc = state.incidents.filter(i => i.status !== 'RESOLVED');
  if (activeInc.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">✅</div>
        <p class="empty-text">All reported incidents are resolved.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = activeInc.map(inc => {
    const sevClass = inc.severity.level.toLowerCase();
    const incEmoji = INCIDENT_ICONS[inc.type] || '🚨';
    const isAssigned = !!inc.assigned_unit_id;

    return `
      <div class="card ${sevClass}-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-title">${incEmoji} ${inc.title}</div>
            <div class="card-loc">📍 ${inc.location.address || 'Active Zone'} • Source: ${inc.source}</div>
          </div>
          <span class="sev-badge sev-${sevClass}">${inc.severity.level}</span>
        </div>

        <p style="font-size: 0.76rem; color: #cbd5e1; line-height: 1.35;">${inc.description}</p>

        <div style="font-family: monospace; font-size: 0.7rem; color: #94a3b8; background: rgba(0,0,0,0.25); padding: 5px 8px; border-radius: 4px;">
          Status: <strong style="color:${isAssigned ? '#38bdf8' : '#ff9500'}">${inc.status}</strong> 
          ${isAssigned ? `| Unit: <strong>${inc.assigned_unit_id}</strong>` : ''}
          | Casualties: ${inc.severity.extracted_casualties}
        </div>

        <div class="card-actions">
          <button class="hud-btn hud-btn-outline hud-btn-sm" style="flex:1;" onclick="panToIncident('${inc.id}')">
            🎯 Locate on Map
          </button>
          <button class="hud-btn hud-btn-success hud-btn-sm" onclick="resolveIncidentDirect('${inc.id}')">
            ✓ Mark Resolved
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderFleetList() {
  const container = document.getElementById('fleetList');
  if (!container) return;

  container.innerHTML = state.units.map(unit => {
    const unitEmoji = UNIT_ICONS[unit.type] || '🚑';
    const statusColor = unit.status === 'AVAILABLE' ? '#30d158' : unit.status === 'EN_ROUTE' ? '#ff9500' : '#ff2d55';

    return `
      <div class="card" style="padding: 10px 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="unit-icon-pill">${unitEmoji}</div>
            <div>
              <div style="font-size: 0.85rem; font-weight: 700; color: #fff;">${unit.name}</div>
              <div style="font-size: 0.7rem; color: #94a3b8;">${unit.type} • Cap: ${unit.capacity} • Speed: ${unit.speed_kmh}km/h</div>
            </div>
          </div>
          <div style="text-align: right;">
            <span style="font-family: monospace; font-size: 0.72rem; font-weight: 700; color: ${statusColor};">${unit.status}</span>
            ${unit.assigned_incident_id ? `<div style="font-size: 0.65rem; color: #38bdf8;">To: ${unit.assigned_incident_id}</div>` : ''}
          </div>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 6px; margin-top: 6px;">
          <button class="hud-btn hud-btn-ghost hud-btn-sm" onclick="panToUnit('${unit.id}')">Locate</button>
          <button class="hud-btn hud-btn-outline hud-btn-sm" onclick="resetUnitDirect('${unit.id}')">Reset to Base</button>
        </div>
      </div>
    `;
  }).join('');
}

function renderBenchmark() {
  const bm = state.benchmark;
  if (!bm || !bm.has_data) {
    document.getElementById('bmTimeSaved').textContent = '--%';
    document.getElementById('bmCritSpeedup').textContent = '--%';
    document.getElementById('bmMismatches').textContent = '0';
    document.getElementById('bmSummary').textContent = 'No active incidents loaded to benchmark.';
    return;
  }

  document.getElementById('bmTimeSaved').textContent = `-${bm.improvements.overall_time_reduction_pct}%`;
  document.getElementById('bmCritSpeedup').textContent = `+${bm.improvements.critical_emergency_speedup_pct}%`;
  document.getElementById('bmMismatches').textContent = `${bm.improvements.mismatches_prevented} Prevented`;
  document.getElementById('bmSummary').textContent = bm.improvements.summary;
}


// ==========================================================================
// Event Listeners & User Interactions
// ==========================================================================
function bindEvents() {
  // Tabs Navigation
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      const targetTab = btn.getAttribute('data-tab');
      btn.classList.add('active');
      document.getElementById(targetTab)?.classList.add('active');
      state.activeTab = targetTab;
    });
  });

  // Load Scenario Button
  document.getElementById('btnLoadScenario').addEventListener('click', async () => {
    const scenKey = document.getElementById('scenarioSelect').value;
    if (!scenKey) return alert('Please select a disaster scenario from the dropdown.');

    try {
      const res = await fetch(`/api/scenarios/${scenKey}/load`, { method: 'POST' });
      const data = await res.json();
      await refreshAllData();
      // Zoom map to encompass loaded incidents
      fitMapToIncidents();
    } catch (err) {
      alert('Failed to load scenario: ' + err.message);
    }
  });

  // Inject Random Emergency
  document.getElementById('btnInjectRandom').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/simulation/inject-random', { method: 'POST' });
      const newInc = await res.json();
      await refreshAllData();
      panToIncident(newInc.id);
    } catch (err) {
      alert('Error injecting alert: ' + err.message);
    }
  });

  // Accept All Button
  document.getElementById('btnAcceptAll').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/dispatch/accept-all', { method: 'POST' });
      const data = await res.json();
      await refreshAllData();
      // Start simulation transit automatically to show vehicles moving!
      startSimulationTransit();
    } catch (err) {
      alert('Error accepting all: ' + err.message);
    }
  });

  // Reset All Button
  document.getElementById('btnResetAll').addEventListener('click', async () => {
    if (!confirm('Reset all emergency incidents and units to baseline?')) return;
    try {
      stopSimulationTransit();
      await fetch('/api/simulation/reset', { method: 'POST' });
      await refreshAllData();
    } catch (err) {
      alert('Reset failed: ' + err.message);
    }
  });

  // Sim Transit Toggle Button
  document.getElementById('btnSimToggle').addEventListener('click', () => {
    if (state.simRunning) {
      stopSimulationTransit();
    } else {
      startSimulationTransit();
    }
  });

  // Modal Open/Close Controls
  document.getElementById('btnOpenSosModal').addEventListener('click', openSosModal);
  document.getElementById('btnCloseSosModal').addEventListener('click', closeSosModal);
  document.getElementById('btnCancelSos').addEventListener('click', closeSosModal);
  document.getElementById('btnCloseOverrideModal').addEventListener('click', closeOverrideModal);
  document.getElementById('btnCancelOverride').addEventListener('click', closeOverrideModal);

  // Quick Preset Chips in Intake Form
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.getElementById('sosType').value = chip.getAttribute('data-type');
      document.getElementById('sosTitle').value = chip.getAttribute('data-title');
      document.getElementById('sosDesc').value = chip.getAttribute('data-desc');
    });
  });

  // SOS Intake Form Submit
  document.getElementById('sosForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById('sosTitle').value,
      type: document.getElementById('sosType').value,
      description: document.getElementById('sosDesc').value,
      location: {
        lat: parseFloat(document.getElementById('sosLat').value),
        lng: parseFloat(document.getElementById('sosLng').value),
        address: document.getElementById('sosAddress').value
      },
      source: document.getElementById('sosSource').value,
      reported_casualties: document.getElementById('sosCasualties').value ? parseInt(document.getElementById('sosCasualties').value) : null,
      has_vulnerable_groups: document.getElementById('sosVuln').checked
    };

    try {
      const res = await fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const created = await res.json();
      closeSosModal();
      await refreshAllData();
      panToIncident(created.id);
      // Switch tab to AI Dispatch Plan
      document.getElementById('tabBtnAlloc').click();
    } catch (err) {
      alert('Error submitting emergency: ' + err.message);
    }
  });

  // Override Form Submit
  document.getElementById('overrideForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const incId = document.getElementById('overrideIncId').value;
    const unitId = document.getElementById('overrideUnitSelect').value;
    const reason = document.getElementById('overrideReason').value;

    try {
      await fetch('/api/dispatch/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_id: incId, unit_id: unitId, reason: reason })
      });
      closeOverrideModal();
      await refreshAllData();
    } catch (err) {
      alert('Error saving override: ' + err.message);
    }
  });

  // Toggle Benchmark Collapse
  document.getElementById('btnToggleBenchmark').addEventListener('click', () => {
    const body = document.getElementById('benchmarkBody');
    const btn = document.getElementById('btnToggleBenchmark');
    if (body.style.display === 'none') {
      body.style.display = 'grid';
      btn.textContent = '▲';
    } else {
      body.style.display = 'none';
      btn.textContent = '▼';
    }
  });
}


// ==========================================================================
// Simulation Transit Loop
// ==========================================================================
function startSimulationTransit() {
  if (state.simRunning) return;
  state.simRunning = true;
  document.getElementById('simToggleText').textContent = '⏸ Pause Transit';
  document.getElementById('btnSimToggle').classList.add('hud-btn-primary');

  state.simTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/simulation/step?multiplier=1.8', { method: 'POST' });
      const data = await res.json();
      state.units = data.units;
      state.incidents = data.incidents;
      updateMapMarkers();
      renderFleetList();
    } catch (err) {
      console.error('Simulation step error:', err);
    }
  }, 1000);
}

function stopSimulationTransit() {
  state.simRunning = false;
  clearInterval(state.simTimer);
  document.getElementById('simToggleText').textContent = '▶ Sim Transit';
  document.getElementById('btnSimToggle').classList.remove('hud-btn-primary');
}


// ==========================================================================
// Global Action Callbacks (Invoked from HTML strings)
// ==========================================================================
window.acceptDispatchDirect = async function(incidentId, unitId) {
  try {
    await fetch(`/api/dispatch/accept?incident_id=${incidentId}&unit_id=${unitId}`, { method: 'POST' });
    await refreshAllData();
    startSimulationTransit();
  } catch (err) {
    alert('Failed to dispatch: ' + err.message);
  }
};

window.resolveIncidentDirect = async function(incidentId) {
  try {
    await fetch(`/api/incidents/${incidentId}/resolve`, { method: 'POST' });
    await refreshAllData();
  } catch (err) {
    alert('Failed to resolve: ' + err.message);
  }
};

window.resetUnitDirect = async function(unitId) {
  try {
    await fetch(`/api/units/${unitId}/reset`, { method: 'POST' });
    await refreshAllData();
  } catch (err) {
    alert('Failed to reset unit: ' + err.message);
  }
};

window.panToIncident = function(incidentId) {
  const inc = state.incidents.find(i => i.id === incidentId);
  if (inc && state.map) {
    state.map.flyTo([inc.location.lat, inc.location.lng], 15, { duration: 1.2 });
    state.markers.incidents[incidentId]?.openPopup();
  }
};

window.panToUnit = function(unitId) {
  const u = state.units.find(i => i.id === unitId);
  if (u && state.map) {
    state.map.flyTo([u.location.lat, u.location.lng], 15, { duration: 1.2 });
    state.markers.units[unitId]?.openPopup();
  }
};

function fitMapToIncidents() {
  const activeInc = state.incidents.filter(i => i.status !== 'RESOLVED');
  if (activeInc.length > 0 && state.map) {
    const latLngs = activeInc.map(i => [i.location.lat, i.location.lng]);
    state.map.fitBounds(latLngs, { padding: [50, 50] });
  }
}

function openSosModal() {
  document.getElementById('sosModal').style.display = 'flex';
}

function closeSosModal() {
  document.getElementById('sosModal').style.display = 'none';
}

window.openOverrideModal = function(incidentId, incidentTitle) {
  document.getElementById('overrideIncId').value = incidentId;
  document.getElementById('overrideIncSummary').textContent = `Reassigning emergency: ${incidentTitle}`;

  const select = document.getElementById('overrideUnitSelect');
  select.innerHTML = state.units.map(u => `
    <option value="${u.id}">${u.name} (${u.type} - Status: ${u.status})</option>
  `).join('');

  document.getElementById('overrideModal').style.display = 'flex';
};

function closeOverrideModal() {
  document.getElementById('overrideModal').style.display = 'none';
}
