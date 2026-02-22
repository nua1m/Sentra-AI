const API_BASE = '/api';

export async function fetchHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
}

export async function fetchScans() {
    const res = await fetch(`${API_BASE}/scans`);
    return res.json();
}

export async function fetchScan(scanId) {
    const res = await fetch(`${API_BASE}/scan/${scanId}`);
    return res.json();
}

export async function fetchFixes(scanId) {
    const res = await fetch(`${API_BASE}/scan/${scanId}/fixes`);
    return res.json();
}

export async function startScan(target) {
    const res = await fetch(`${API_BASE}/scan/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
    });
    return res.json();
}

export async function exportPdf(scanId) {
    const res = await fetch(`${API_BASE}/scan/${scanId}/export`);
    return res.json();
}

export async function removeScan(scanId) {
    const res = await fetch(`${API_BASE}/scan/${scanId}`, { method: 'DELETE' });
    return res.json();
}
