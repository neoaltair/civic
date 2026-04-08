# CivicFix - Municipality Complaint & Event Platform

CivicFix is a comprehensive web platform designed to bridge the gap between citizens and municipal administration. It allows citizens to report issues, track complaint status, and participate in community events, while providing administrators with tools to manage these activities efficiently.

## 🚀 Core Technologies
- **Frontend**: Pure HTML5, CSS3 (Modern Design System), JavaScript (ES6+).
- **Data Persistence**: `localStorage` (No backend required for demonstration).
- **Mapping**: Leaflet.js (OpenStreetMap) for location pinning.
- **Charts**: Chart.js for analytics.

## 📂 File Structure & Description

### Core Files
| File | Description |
|------|-------------|
| `index.html` | The landing page for public visitors. Introduces the platform and provides links to Login/Register. |
| `style.css` | The central design system. Contains CSS variables for colors, spacing, typography, and reusable components like cards, buttons, and forms. |
| `script.js` | The "brain" of the application. Contains all logic for data storage, authentication, and UI rendering. |

### Authentication
| File | Description |
|------|-------------|
| `login.html` | User login form. Redirects to `citizen.html` or `admin.html` based on role. |
| `register.html` | User registration form. Creates a new user in `localStorage`. |
| `logout.html` | Simple redirect page that clears the session and sends user to login. |

### Citizen Features
| File | Description |
|------|-------------|
| `citizen.html` | Citizen Dashboard. Shows statistics (pending/resolved complaints) and sidebar navigation. |
| `submit_complaint.html` | Form to report issues. Integrates **Leaflet Maps** to pin exact locations (defaults to Chennai). |
| `my_complaints.html` | List of complaints submitted by the current user. Cards are clickable for details. |
| `public_complaints.html` | Community feed of all public complaints. Allows upvoting. |
| `complaint_details.html` | Detailed view of a specific complaint, showing map, description, status, and admin remarks. |
| `announcements.html` | View official updates posted by the administration. |
| `volunteer.html` | Event participation hub. Users can view and **Join** community events. |
| `feedback.html` | Form to provide feedback on resolved complaints. |

### Admin Features
| File | Description |
|------|-------------|
| `admin.html` | Admin Dashboard. Overview of system health and key metrics. |
| `manage_complaints.html` | Interface to filter complaints, update status (Pending -> Resolved), and add remarks. |
| `manage_events.html` | Interface to create and delete community events. |
| `announcements_admin.html` | Form to publish new announcements to the system. |
| `analytics.html` | Visual analytics using Chart.js to show complaint trends and status distribution. |

## 🧠 Code Documentation (`script.js`)

The `script.js` file is organized into three main modules:

### 1. `Storage` Object
Handling all interactions with `localStorage`. Acts as a pseudo-database layer.
- **Users**: `getUsers()`, `addUser()`, `findUser(email)`.
- **Complaints**: `getComplaints()`, `addComplaint()`, `updateComplaint()`.
- **Announcements**: `getAnnouncements()`, `addAnnouncement()`.
- **Events**:
    - `getEvents()`: Returns list of events.
    - `addEvent(event)`: Creates a new event.
    - `deleteEvent(id)`: Removes an event.
    - `joinEvent(eventId, email)`: Adds user to event attendee list.
    - `leaveEvent(eventId, email)`: Removes user from attendee list.

### 2. `Auth` Object
Manages user sessions and access control.
- `register(name, email, password, role)`: Validates unique email and saves user.
- `login(email, password)`: Validates credentials and sets active session.
- `logout()`: Clears session and redirects to login.
- `check()`: Verifies if a user is logged in; redirects to login if not.
- `checkAdmin()`: Strict check for admin role; redirects non-admins.

### 3. `UI` Object
Helper functions for DOM manipulation and consistent rendering.
- `renderNavbar()`: Dynamically injects the navigation bar into the top of the `<body>`. It checks the user's role to show correct links (e.g., "Dashboard" for logged-in users vs "Login/Register" for guests).
- `formatDate(isoString)`: Converts computer-readable timestamps into human-readable text (e.g., "August 24, 2024").

## 🎨 Design System (`style.css`)
The design uses a **Premium Theme** based on Deep Navy and Electric Blue.
- **Variables (`:root`)**: Defines a consistent palette (`--primary-color`, `--secondary-color`), spacing scales, and font families.
- **Glassmorphism**: Uses semi-transparent backgrounds with blur filters for the Navbar.
- **Components**: Reusable classes for `.btn`, `.card`, `.input-control`, and `.badge`.
- **Responsive**: Uses CSS Grid and Flexbox to ensure layout works on mobile and desktop.

## 🛠️ How to Run
1.  **No Server Needed**: Since there is no backend, simply double-click `index.html` to open it in your browser.
2.  **Default Admin**: The system auto-generates an admin account on first load:
    -   **Email**: `admin@civic.com`
    -   **Password**: `admin`
