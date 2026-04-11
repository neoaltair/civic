/**
 * CivicFix — Shared Logic (API-backed, Dark Theme)
 * Auth reads localStorage synchronously.
 * Storage methods are async and hit http://localhost:8000
 */

const API_BASE = 'http://localhost:8000';

// ─── API Fetch Helper ──────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
    const session = JSON.parse(localStorage.getItem('civic_session'));
    const isFormData = options.body instanceof FormData;
    const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
    if (options.headers) Object.assign(headers, options.headers);
    if (session && session.token) {
        headers['Authorization'] = `Bearer ${session.token}`;
    }
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
        localStorage.removeItem('civic_session');
        window.location.href = 'login.html';
        return;
    }
    return res;
}

// ─── Auth ─────────────────────────────────────────────────────────────────

const Auth = {
    // SYNCHRONOUS — reads localStorage directly
    check: () => {
        const session = JSON.parse(localStorage.getItem('civic_session'));
        if (!session) { window.location.href = 'login.html'; return null; }
        return session;
    },

    checkAdmin: () => {
        const session = JSON.parse(localStorage.getItem('civic_session'));
        if (!session) { window.location.href = 'login.html'; return null; }
        if (session.role !== 'admin') {
            alert('Access Denied');
            window.location.href = 'citizen.html';
            return null;
        }
        return session;
    },

    // ASYNC
    login: async (email, password) => {
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            if (!res.ok) {
                const err = await res.json();
                return { success: false, message: err.detail || 'Invalid credentials' };
            }
            const data = await res.json();
            const session = { token: data.access_token, ...data.user };
            localStorage.setItem('civic_session', JSON.stringify(session));
            return { success: true, user: data.user };
        } catch (e) {
            return { success: false, message: 'Cannot reach server. Is the backend running?' };
        }
    },

    register: async (name, email, password, role = 'citizen') => {
        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password, role }),
            });
            if (!res.ok) {
                const err = await res.json();
                return { success: false, message: err.detail || 'Registration failed' };
            }
            return { success: true, message: 'Registration successful' };
        } catch (e) {
            return { success: false, message: 'Cannot reach server. Is the backend running?' };
        }
    },

    logout: () => {
        localStorage.removeItem('civic_session');
        window.location.href = 'login.html';
    },
};

// ─── Storage (async API calls) ────────────────────────────────────────────

const Storage = {
    // Session helpers (kept for UI.renderNavbar compatibility)
    getSession: () => JSON.parse(localStorage.getItem('civic_session')),
    setSession: (s) => localStorage.setItem('civic_session', JSON.stringify(s)),
    clearSession: () => localStorage.removeItem('civic_session'),

    // ── Complaints ──────────────────────────────────────────────────────────

    getComplaints: async () => {
        const res = await apiFetch('/complaints');
        if (!res || !res.ok) return [];
        return await res.json();
    },

    getPublicComplaints: async () => {
        const res = await apiFetch('/complaints/public');
        if (!res || !res.ok) return [];
        return await res.json();
    },

    getComplaintById: async (id) => {
        const res = await apiFetch(`/complaints/${id}`);
        if (!res || !res.ok) return null;
        return await res.json();
    },

    // Accepts FormData for multipart upload
    addComplaint: async (formData) => {
        const res = await apiFetch('/complaints', { method: 'POST', body: formData });
        if (!res || !res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to submit complaint');
        }
        return await res.json();
    },

    updateComplaint: async (id, updates) => {
        const res = await apiFetch(`/complaints/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(updates),
        });
        if (!res || !res.ok) throw new Error('Failed to update complaint');
        return await res.json();
    },

    upvoteComplaint: async (id) => {
        const res = await apiFetch(`/complaints/${id}/upvote`, { method: 'POST' });
        if (!res || !res.ok) throw new Error('Failed to upvote');
        return await res.json();
    },

    // ── Comments ─────────────────────────────────────────────────────────────

    getComments: async (complaintId) => {
        const res = await apiFetch(`/complaints/${complaintId}/comments`);
        if (!res || !res.ok) return [];
        return await res.json();
    },

    addComment: async (complaintId, text) => {
        const res = await apiFetch(`/complaints/${complaintId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        if (!res || !res.ok) throw new Error('Failed to post comment');
        return await res.json();
    },

    // ── Announcements ────────────────────────────────────────────────────────

    getAnnouncements: async () => {
        const res = await apiFetch('/announcements');
        if (!res || !res.ok) return [];
        return await res.json();
    },

    addAnnouncement: async (data) => {
        const res = await apiFetch('/announcements', {
            method: 'POST',
            body: JSON.stringify(data),
        });
        if (!res || !res.ok) throw new Error('Failed to post announcement');
        return await res.json();
    },

    deleteAnnouncement: async (id) => {
        const res = await apiFetch(`/announcements/${id}`, { method: 'DELETE' });
        if (!res || !res.ok) throw new Error('Failed to delete announcement');
    },

    // ── Events ──────────────────────────────────────────────────────────────

    getEvents: async () => {
        const res = await apiFetch('/events');
        if (!res || !res.ok) return [];
        return await res.json();
    },

    addEvent: async (data) => {
        const res = await apiFetch('/events', { method: 'POST', body: JSON.stringify(data) });
        if (!res || !res.ok) throw new Error('Failed to create event');
        return await res.json();
    },

    deleteEvent: async (id) => {
        const res = await apiFetch(`/events/${id}`, { method: 'DELETE' });
        if (!res || !res.ok) throw new Error('Failed to delete event');
    },

    joinEvent: async (id) => {
        const res = await apiFetch(`/events/${id}/join`, { method: 'POST' });
        if (!res || !res.ok) throw new Error('Failed to join event');
        return await res.json();
    },

    leaveEvent: async (id) => {
        const res = await apiFetch(`/events/${id}/leave`, { method: 'POST' });
        if (!res || !res.ok) throw new Error('Failed to leave event');
        return await res.json();
    },

    // ── Admin Stats ──────────────────────────────────────────────────────────

    getAdminStats: async () => {
        const res = await apiFetch('/admin/stats');
        if (!res || !res.ok) return { totalUsers: 0, totalComplaints: 0, pending: 0, resolved: 0, inProgress: 0 };
        return await res.json();
    },

    // ── User Profile ─────────────────────────────────────────────────────────

    getProfile: async () => {
        const res = await apiFetch('/users/me/profile');
        if (!res || !res.ok) return null;
        return await res.json();
    },

    updateProfile: async (data) => {
        const res = await apiFetch('/users/me/profile', {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
        if (!res || !res.ok) throw new Error('Failed to update profile');
        return await res.json();
    },

    // ── Feedback (localStorage only) ─────────────────────────────────────────
    get: (key) => JSON.parse(localStorage.getItem(key)) || [],
    set: (key, value) => localStorage.setItem(key, JSON.stringify(value)),
};

// ─── UI Helpers ───────────────────────────────────────────────────────────

const UI = {
    formatDate: (isoString) => {
        return new Date(isoString).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
    },

    formatDateTime: (isoString) => {
        return new Date(isoString).toLocaleString('en-US', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    },

    statusBadge: (status) => {
        const map = {
            'Pending':     'badge-pending',
            'In Progress': 'badge-progress',
            'Resolved':    'badge-resolved',
            'Rejected':    'badge-rejected',
        };
        const cls = map[status] || 'badge-rejected';
        return `<span class="badge ${cls}">${status}</span>`;
    },

    statusCardClass: (status) => {
        if (status === 'Resolved')    return 'status-resolved';
        if (status === 'In Progress') return 'status-progress';
        return 'status-pending';
    },

    renderNavbar: () => {
        const session = Storage.getSession();
        const nav = document.createElement('nav');
        nav.className = 'navbar';
        nav.id = 'mainNavbar';

        let links = '';
        if (!session) {
            links = `
                <li><a href="index.html" class="nav-link">Home</a></li>
                <li><a href="login.html" class="nav-link">Login</a></li>
                <li><a href="register.html" class="btn btn-primary btn-sm">Register</a></li>
            `;
        } else if (session.role === 'citizen') {
            links = `
                <li><a href="citizen.html" class="nav-link">Dashboard</a></li>
                <li><a href="profile.html" class="nav-link">👤 ${session.name.split(' ')[0]}</a></li>
                <li><a href="#" onclick="Auth.logout()" class="nav-link">Logout</a></li>
            `;
        } else if (session.role === 'admin') {
            links = `
                <li><a href="admin.html" class="nav-link">Dashboard</a></li>
                <li><a href="profile.html" class="nav-link">👤 ${session.name.split(' ')[0]}</a></li>
                <li><a href="#" onclick="Auth.logout()" class="nav-link">Logout</a></li>
            `;
        }

        nav.innerHTML = `
            <div class="container flex justify-between items-center">
                <a href="index.html" class="nav-brand">
                    CivicFix<span class="dot">.</span>
                </a>
                <button class="hamburger" id="hamburgerBtn" aria-label="Menu">
                    <span></span><span></span><span></span>
                </button>
                <ul class="nav-links" id="navLinks">
                    ${links}
                </ul>
            </div>
        `;
        document.body.prepend(nav);

        // Hamburger toggle
        document.getElementById('hamburgerBtn')?.addEventListener('click', () => {
            document.getElementById('navLinks')?.classList.toggle('open');
        });

        // Scroll blur
        window.addEventListener('scroll', () => {
            nav.classList.toggle('scrolled', window.scrollY > 10);
        });

        // Sidebar hamburger for dashboard
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                document.querySelector('.sidebar')?.classList.toggle('open');
            });
        }
    },
};
