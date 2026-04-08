/**
 * CivicFix - Shared Logic
 * Handles Storage, Authentication, and Common Utilities
 */

const Storage = {
    get: (key) => JSON.parse(localStorage.getItem(key)) || [],
    set: (key, value) => localStorage.setItem(key, JSON.stringify(value)),

    // Users
    getUsers: () => Storage.get('civic_users'),
    addUser: (user) => {
        const users = Storage.getUsers();
        users.push(user);
        Storage.set('civic_users', users);
    },
    findUser: (email) => {
        const users = Storage.getUsers();
        return users.find(u => u.email === email);
    },

    // Current Session
    getSession: () => JSON.parse(localStorage.getItem('civic_session')),
    setSession: (user) => localStorage.setItem('civic_session', JSON.stringify(user)),
    clearSession: () => localStorage.removeItem('civic_session'),

    // Complaints
    getComplaints: () => Storage.get('civic_complaints'),
    addComplaint: (complaint) => {
        const complaints = Storage.getComplaints();
        complaint.id = Date.now().toString();
        complaint.status = 'Pending';
        complaint.timestamp = new Date().toISOString();
        complaints.push(complaint);
        Storage.set('civic_complaints', complaints);
    },
    updateComplaint: (id, updates) => {
        let complaints = Storage.getComplaints();
        complaints = complaints.map(c => c.id === id ? { ...c, ...updates } : c);
        Storage.set('civic_complaints', complaints);
    },

    // Announcements
    getAnnouncements: () => Storage.get('civic_announcements'),
    addAnnouncement: (announcement) => {
        const items = Storage.getAnnouncements();
        announcement.id = Date.now().toString();
        announcement.timestamp = new Date().toISOString();
        items.push(announcement);
        Storage.set('civic_announcements', items);
    },

    // Events
    getEvents: () => Storage.get('civic_events'),
    addEvent: (event) => {
        const events = Storage.getEvents();
        event.id = Date.now().toString();
        event.attendees = []; // List of user emails
        events.push(event);
        Storage.set('civic_events', events);
    },
    deleteEvent: (id) => {
        const events = Storage.getEvents().filter(e => e.id !== id);
        Storage.set('civic_events', events);
    },
    joinEvent: (eventId, userEmail) => {
        const events = Storage.getEvents();
        const event = events.find(e => e.id === eventId);
        if (event && !event.attendees.includes(userEmail)) {
            event.attendees.push(userEmail);
            Storage.set('civic_events', events);
            return true;
        }
        return false;
    },
    leaveEvent: (eventId, userEmail) => {
        const events = Storage.getEvents();
        const event = events.find(e => e.id === eventId);
        if (event) {
            event.attendees = event.attendees.filter(email => email !== userEmail);
            Storage.set('civic_events', events);
            return true;
        }
        return false;
    }
};

const Auth = {
    register: (name, email, password, role = 'citizen') => {
        if (Storage.findUser(email)) {
            return { success: false, message: 'Email already registered' };
        }
        Storage.addUser({ name, email, password, role });
        return { success: true, message: 'Registration successful' };
    },

    login: (email, password) => {
        const user = Storage.findUser(email);
        if (user && user.password === password) {
            Storage.setSession({ name: user.name, email: user.email, role: user.role });
            return { success: true, user };
        }
        return { success: false, message: 'Invalid credentials' };
    },

    logout: () => {
        Storage.clearSession();
        window.location.href = 'login.html';
    },

    check: () => {
        const session = Storage.getSession();
        if (!session) {
            window.location.href = 'login.html';
        }
        return session;
    },

    checkAdmin: () => {
        const session = Auth.check();
        if (session.role !== 'admin') {
            alert('Access Denied');
            window.location.href = 'citizen.html';
        }
    }
};

// Initialize some dummy data if empty
const Init = () => {
    if (Storage.getUsers().length === 0) {
        // Create default admin
        Storage.addUser({
            name: 'Admin User',
            email: 'admin@civic.com',
            password: 'admin',
            role: 'admin'
        });
        console.log('Default admin created: admin@civic.com / admin');
    }
};

// UI Helpers
const UI = {
    formatDate: (isoString) => {
        return new Date(isoString).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
    },

    // Inject Navbar based on session
    renderNavbar: () => {
        const session = Storage.getSession();
        const nav = document.createElement('nav');
        nav.className = 'navbar';

        // Define links based on role
        let links = '';
        if (!session) {
            links = `
                <li><a href="index.html" class="nav-link">Home</a></li>
                <li><a href="login.html" class="nav-link">Login</a></li>
                <li><a href="register.html" class="btn btn-primary">Register</a></li>
            `;
        } else if (session.role === 'citizen') {
            links = `
                <li><a href="citizen.html" class="nav-link">Dashboard</a></li>
                <li><a href="#" onclick="Auth.logout()" class="nav-link">Logout</a></li>
            `;
        } else if (session.role === 'admin') {
            links = `
                <li><a href="admin.html" class="nav-link">Dashboard</a></li>
                <li><a href="#" onclick="Auth.logout()" class="nav-link">Logout</a></li>
            `;
        }

        nav.innerHTML = `
            <div class="container flex justify-between items-center">
                <a href="index.html" class="nav-brand">
                    <span>🏛️</span> CivicFix
                </a>
                <ul class="nav-links items-center">
                    ${links}
                </ul>
            </div>
        `;
        document.body.prepend(nav);
    }
};

// Run initialization
Init();
