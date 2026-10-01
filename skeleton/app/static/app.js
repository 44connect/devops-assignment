// =============================================================================
// 전역 변수
// =============================================================================
let subscribers = [];
let currentDevices = [];
let selectedUserId = null;
let selectedDeviceId = null;
let usageChart = null;


// =============================================================================
// [요구사항 #3] 상태 기반 Badge 스타일
// =============================================================================
// TODO [요구사항 #3]: 상태 값(value)에 따라 적절한 CSS 클래스를 반환하세요.
//
function badgeClass(value) {
    const v = (value || "").toLowerCase();

    // 매핑 규칙:
    // Active, Online, Normal   → "badge status-active"   (초록)
    // Paused, Standby          → "badge status-paused"   (파랑)
    // Expired, Error, Warning  → "badge status-expired"  (빨강)
    // Offline                  → "badge status-offline"  (회색)
    // On, Cleaning             → "badge status-on"       (노랑)
    // Off                      → "badge status-off"      (연회색)
    // 그 외                     → "badge"
    const statusClass = {
        active: "status-active", online: "status-active", normal: "status-active",
        paused: "status-paused", standby: "status-paused",
        expired: "status-expired", error: "status-expired", warning: "status-expired",
        offline: "status-offline",
        on: "status-on", cleaning: "status-on",
        off: "status-off",
    };

    return Object.hasOwn(statusClass, v) ? `badge ${statusClass[v]}` : "badge";
}


// =============================================================================
// [요구사항 #1] 구독 사용자 조회 + 검색/필터
// =============================================================================

// TODO [요구사항 #1-A]: GET /api/subscribers 를 호출하여
//   subscribers 변수에 저장하고 renderSubscribers()를 호출하세요.
//
async function fetchSubscribers() {
    try {
        // 1. GET /api/subscribers 호출
        const res = await fetch("/api/subscribers");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // 2. 응답을 subscribers 변수에 저장 (배열이 아니면 빈 목록으로 처리)
        subscribers = Array.isArray(data) ? data : [];
    } catch (err) {
        console.error("Failed to fetch subscribers:", err);
        subscribers = [];
    }

    // 3. renderSubscribers() 호출
    renderSubscribers();
}

// TODO [요구사항 #1-B]: subscribers 배열을 테이블에 렌더링하세요.
//
function renderSubscribers() {
    const tbody = document.getElementById("subscriber-body");
    const search = document.getElementById("subscriber-search").value.toLowerCase();
    const statusFilter = document.getElementById("subscriber-status-filter").value;
    
    // 1. 검색어와 상태 필터 값 가져오기 (위에서 처리)
    // 2. subscribers 배열 필터링
    //    - 검색: name, plan, status, userId에 대해 부분 문자열 매칭
    //    - 필터: status가 선택된 값과 일치
    const filtered = subscribers.filter((s) => {
        const matchesSearch = [s.name, s.plan, s.status, s.userId]
            .some((field) => (field || "").toLowerCase().includes(search));
        const matchesStatus = !statusFilter || s.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // 3. <tbody>에 <tr> 렌더링
    tbody.innerHTML = "";

    if (filtered.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "empty-msg";
        td.textContent = subscribers.length === 0 ? "No subscribers" : "No subscribers matched";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    filtered.forEach((s) => {
        const tr = document.createElement("tr");
        tr.className = "clickable";
        //    - 선택된 행(selectedUserId)에 "selected" 클래스 추가
        if (s.userId === selectedUserId) tr.classList.add("selected");

        //    - 표시 컬럼: userId, name, plan, status, deviceCount
        [s.userId, s.name, s.plan].forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        });

        const statusTd = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = badgeClass(s.status);
        badge.textContent = s.status;
        statusTd.appendChild(badge);
        tr.appendChild(statusTd);

        const countTd = document.createElement("td");
        countTd.textContent = s.deviceCount;
        tr.appendChild(countTd);

        //    - 각 행 클릭 시 selectSubscriber(userId) 호출
        tr.addEventListener("click", () => selectSubscriber(s.userId));
        tbody.appendChild(tr);
    });
}


// =============================================================================
// [요구사항 #2] 사용자별 가전 목록 + 사용 현황 + 차트
// =============================================================================

// TODO [요구사항 #2-A]: 사용자 클릭 시 해당 사용자의 가전 목록을 조회하세요.
//
async function selectSubscriber(userId) {
    // 1. selectedUserId 업데이트, selectedDeviceId = null
    selectedUserId = userId;
    selectedDeviceId = null;

    // 2. renderSubscribers() 호출 (선택 상태 반영)
    renderSubscribers();

    // 3. 이전 사용 현황 초기화:
    //    - usage-empty 표시, usage-detail 숨기기
    //    - usage-info 내용 비우기
    const usageEmpty = document.getElementById("usage-empty");
    usageEmpty.textContent = "Select a device to view usage details.";
    usageEmpty.classList.remove("hidden");
    document.getElementById("usage-detail").classList.add("hidden");
    document.getElementById("usage-info").innerHTML = "";

    // 4. GET /api/subscribers/{userId}/devices 호출
    let devices = [];
    try {
        const res = await fetch(`/api/subscribers/${encodeURIComponent(userId)}/devices`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        devices = Array.isArray(data) ? data : [];
    } catch (err) {
        console.error("Failed to fetch devices:", err);
    }

    // 응답을 기다리는 동안 다른 사용자를 클릭했다면 이전 응답은 무시
    if (selectedUserId !== userId) return;

    // 5. currentDevices에 저장
    currentDevices = devices;

    // 6. renderDevices() 호출
    renderDevices();
}

// TODO [요구사항 #2-B]: currentDevices 배열을 테이블에 렌더링하세요.
//
function renderDevices() {
    const emptyEl = document.getElementById("device-empty");
    const tableEl = document.getElementById("device-table");
    const tbody = document.getElementById("device-body");
    const search = document.getElementById("device-search").value.toLowerCase();
    const statusFilter = document.getElementById("device-status-filter").value;

    // 1. 검색어, 상태 필터 값 가져오기 (위에서 처리)
    // 2. currentDevices 배열 필터링
    //    - 검색: type, model, status, deviceId, location 부분 매칭
    //    - 필터: status 일치
    const filtered = currentDevices.filter((d) => {
        const matchesSearch = [d.type, d.model, d.status, d.deviceId, d.location]
            .some((field) => (field || "").toLowerCase().includes(search));
        const matchesStatus = !statusFilter || d.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // 3. 가전이 없으면 → "No registered devices" 메시지 표시
    //    필터 결과가 없으면 → "No devices matched" 메시지 표시
    //    결과 있으면 → device-table 표시
    tbody.innerHTML = "";

    if (currentDevices.length === 0 || filtered.length === 0) {
        emptyEl.textContent = currentDevices.length === 0 ? "No registered devices" : "No devices matched";
        emptyEl.classList.remove("hidden");
        tableEl.classList.add("hidden");
        return;
    }

    emptyEl.classList.add("hidden");
    tableEl.classList.remove("hidden");

    // 4. <tbody>에 deviceId, type, model, location, status(badge) 렌더링
    filtered.forEach((d) => {
        const tr = document.createElement("tr");
        tr.className = "clickable";
        if (d.deviceId === selectedDeviceId) tr.classList.add("selected");

        [d.deviceId, d.type, d.model, d.location].forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        });

        const statusTd = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = badgeClass(d.status);
        badge.textContent = d.status;
        statusTd.appendChild(badge);
        tr.appendChild(statusTd);

        // 5. 각 행 클릭 시 selectDevice(deviceId) 호출
        tr.addEventListener("click", () => selectDevice(d.deviceId));
        tbody.appendChild(tr);
    });
}

// TODO [요구사항 #2-C]: 가전 클릭 시 상세 사용 현황을 조회하세요.
//
async function selectDevice(deviceId) {
    // 1. selectedDeviceId 업데이트
    selectedDeviceId = deviceId;

    // 2. renderDevices() 호출 (선택 상태 반영)
    renderDevices();

    // 3. GET /api/devices/{deviceId}/usage 호출
    let data = null;
    try {
        const res = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/usage`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        data = await res.json();
    } catch (err) {
        console.error("Failed to fetch usage:", err);
    }

    // 응답을 기다리는 동안 다른 가전을 클릭했다면 이전 응답은 무시
    if (selectedDeviceId !== deviceId) return;

    const emptyEl = document.getElementById("usage-empty");
    const detailEl = document.getElementById("usage-detail");
    const infoEl = document.getElementById("usage-info");

    if (!data) {
        emptyEl.textContent = "Failed to load usage details.";
        emptyEl.classList.remove("hidden");
        detailEl.classList.add("hidden");
        return;
    }

    // 4. usage-empty 숨기기, usage-detail 표시
    emptyEl.classList.add("hidden");
    detailEl.classList.remove("hidden");

    // 5. usage-info에 상세 정보 렌더링 (badge: true 이면 badge 스타일 적용)
    const rows = [
        { label: "Device ID", value: data.deviceId },
        { label: "Device Name", value: data.deviceName },
        { label: "Power Status", value: data.powerStatus, badge: true },
        { label: "Last Used", value: data.lastUsedAt },
        { label: "Total Usage Hours", value: `${data.totalUsageHours} hrs` },
        { label: "Weekly Usage Count", value: data.weeklyUsageCount },
        { label: "Health Status", value: data.healthStatus, badge: true },
        { label: "Remark", value: data.remark },
    ];

    infoEl.innerHTML = "";
    rows.forEach(({ label, value, badge }) => {
        const labelEl = document.createElement("div");
        labelEl.className = "label";
        labelEl.textContent = label;

        const valueEl = document.createElement("div");
        valueEl.className = "value";
        if (badge) {
            const span = document.createElement("span");
            span.className = badgeClass(value);
            span.textContent = value;
            valueEl.appendChild(span);
        } else {
            valueEl.textContent = value;
        }

        infoEl.append(labelEl, valueEl);
    });

    // 6. renderUsageChart(data.weeklyUsageTrend) 호출
    renderUsageChart(data.weeklyUsageTrend || []);
}

// TODO [요구사항 #2-D]: Chart.js를 사용하여 주간 사용량 Bar Chart를 그리세요.
//
function renderUsageChart(trend) {
    const ctx = document.getElementById("usageChart");

    // 1. 기존 차트 있으면 destroy()
    if (usageChart) {
        usageChart.destroy();
        usageChart = null;
    }

    // Chart.js(CDN) 로드 실패 시 차트 없이 상세 정보만 표시
    if (typeof Chart === "undefined") {
        console.error("Chart.js is not loaded");
        return;
    }

    // 2. new Chart() 생성
    usageChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [{
                label: "Weekly Usage Trend",
                data: trend,
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: { y: { beginAtZero: true } },
        },
    });
}


// =============================================================================
// 이벤트 바인딩 + 초기화
// =============================================================================
function bindEvents() {
    // [요구사항 #1] 완료 후 아래 주석을 해제하세요
    document.getElementById("subscriber-search").addEventListener("input", renderSubscribers);
    document.getElementById("subscriber-status-filter").addEventListener("change", renderSubscribers);

    // [요구사항 #2] 완료 후 아래 주석을 해제하세요
    document.getElementById("device-search").addEventListener("input", renderDevices);
    document.getElementById("device-status-filter").addEventListener("change", renderDevices);
}

bindEvents();

// [요구사항 #1] 완료 후 아래 주석을 해제하세요
fetchSubscribers();
