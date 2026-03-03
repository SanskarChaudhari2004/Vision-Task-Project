# Vision-Task-Project

## Positioning

**Business Opportunity**

Healthcare administrative teams manage many sensitive and time-critical tasks every day, such as patient record updates, insurance processing, compliance documentation, and internal coordination. Many small healthcare offices either use general-purpose task management tools or manual tracking methods that do not address data sensitivity, compliance awareness, or role-based access control.

This creates a business opportunity to develop a task management system specifically designed for healthcare administrative teams. By combining secure authentication, role-based access control, task sensitivity levels, and activity logging, Vision Task provides a structured and secure environment tailored to healthcare workflows.


## Problem Statement

The problem of using general-purpose or manual task management systems for healthcare administrative operations affects healthcare administrators, office managers, and healthcare team members who manage sensitive and time-critical tasks. The impact of which is increased risk of unauthorized task modification, lack of accountability, poor visibility of task priority, and potential non-compliance with data sensitivity expectations such as HIPAA-related practices.

A successful solution would be a secure task management system that enforces role-based access control, protects high-sensitivity tasks through re-authentication, tracks user activity, prioritizes urgent tasks clearly, and supports structured healthcare administrative workflows.


## Product Position Statement

For small healthcare administrative teams and office managers who need a secure, structured, and accountability-focused way to manage sensitive and high-priority administrative tasks, Vision Task is a secure role-based task management application that provides HIPAA-aware task sensitivity levels, authentication controls, priority visualization, and activity logging to protect and organize healthcare workflows.

Unlike general-purpose task management applications that treat all tasks equally and lack healthcare-focused security enforcement, our product enforces task sensitivity rules, restricts unauthorized deletion of high-sensitivity tasks, requires re-authentication for critical actions, and integrates security directly into daily healthcare administrative operations.

---

## Healthcare Features Implemented

### 1. **Secure Authentication**
- User login system with token-based API authentication
- User roles: Admin, Manager, User
- Department-based organization (Administration, Clinic, Billing)
- Foundation for future password hashing and OAuth integration

### 2. **Role-Based Access Control (RBAC)**
- Admin access for system-wide operations
- Manager permissions for team oversight
- Standard user permissions for task creators/assignees
- Granular permissions for sensitive operations (task deletion, user administration)

### 3. **Task Sensitivity Levels**
- **Low**: Standard operations visible to all users
- **Medium**: Internal data accessible to managers and users with clearance
- **High**: Confidential/HIPAA data restricted to authorized personnel
- Automatic filtering based on user clearance level
- Compliance logging for unauthorized access attempts

### 4. **Comprehensive Activity Logging**
- Detailed audit trail for all system operations (create, read, update, delete)
- Structured JSON logging for compliance and analytics
- Access attempt tracking (both allowed and denied)
- Change tracking with before/after values
- Logs stored to both console and file (`activity_log.txt`)
- Timestamp and user identification for all actions

### 5. **Task Management Features**
- **Task Status Tracking**: New, Assigned, In Progress, Completed, Cancelled
- **Task Assignment**: Assign tasks to specific team members
- **Priority Levels**: Low, Medium, High for urgent task identification
- **Department Tracking**: Tasks linked to originating department
- **Metadata**: Created/updated timestamps for compliance

### 6. **Healthcare Workflow Support**
- Multi-department organization (Administration, Clinic, Billing)
- Task creator and assignee tracking
- Priority visualization for urgent healthcare tasks
- History of all task modifications
- Audit trail for HIPAA compliance

### 7. **Web Interface**
- Professional login page with demo credentials
- Dashboard with task statistics and quick overview
- Color-coded sensitivity levels for visual clarity
- Task detail view with full edit capabilities
- Responsive Bootstrap-based UI

### 8. **REST API**
- Complete API endpoints for programmatic access
- Task CRUD operations with authorization enforcement
- User statistics and administration endpoints
- API documentation endpoint

---

## System Architecture

### Database Models

```python
User:
  - username (unique identifier)
  - roles (admin, manager, user)
  - department (Administration, Clinic, Billing)
  - sensitive data clearance (high, medium, low)

Task:
  - ID (UUID)
  - Title and description
  - Sensitivity level (high, medium, low)
  - Status (new, assigned, in_progress, completed, cancelled)
  - Assignment tracking (created_by, assigned_to)
  - Priority (high, medium, low)
  - Department and timestamps
```

### Security Components

- **Authentication**: Bearer token validation
- **Authorization**: RBAC enforcement at route level
- **Audit Logging**: Comprehensive activity tracking
- **Sensitivity Filtering**: Automatic task filtering by clearance
- **Access Denial Logging**: All unauthorized attempts recorded

---

## Demo Credentials

Login with any of the following usernames (no password required for demo):

| Username | Role | Department | Permissions |
|----------|------|-----------|-------------|
| `admin` | Admin, Manager | Administration | Full system access, can delete tasks, view all data |
| `manager` | Manager, User | Clinic | Team oversight, view high/medium sensitivity tasks |
| `clerk` | User | Clinic | Standard operations, view medium/low sensitivity tasks |
| `staff` | User | Billing | Limited access, view only low/medium non-sensitive tasks |

---

## Python Implementation

This repository contains a Python-based prototype of the Vision Task system built with Flask. It includes:

* API endpoints for task management
* In-memory user store with role-based authentication
* Task sensitivity levels and simple logging

## Getting Started

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository** (if applicable)
2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the Flask server**

   ```bash
   python run.py
   ```

   The application will be available at `http://127.0.0.1:5000/`

2. **Access the Web Interface**
   - Navigate to `http://127.0.0.1:5000/login`
   - Login with any demo credential (e.g., `admin`, `manager`, `clerk`, `staff`)
   - No password required for demo (in production, use secure password hashing)

3. **Dashboard Features**
   - View tasks based on your permissions and clearance level
   - Create new tasks with sensitivity levels and priority
   - Assign tasks to team members
   - Track task status through the workflow
   - View detailed task information with audit history

### API Usage

The REST API supports programmatic access to the task management system.

#### Authentication

All API requests (except login page) require Bearer token authentication:

```bash
Authorization: Bearer <username>
```

Example with curl:

```bash
curl -H "Authorization: Bearer admin" http://127.0.0.1:5000/api/tasks
```

#### API Endpoints

**Get Tasks**
- `GET /api/tasks` - List tasks visible to authenticated user (respects sensitivity levels)
- `GET /api/tasks/<id>` - Get task details with access control

**Create Task**
- `POST /api/tasks` - Create new task with sensitivity level and assignment

```json
{
  "title": "Update patient records",
  "description": "Review and update Q1 patient records",
  "sensitivity": "high",
  "assigned_to": "clerk",
  "priority": 2
}
```

**Update Task**
- `PUT /api/tasks/<id>` - Update task (creator or admin only)

```json
{
  "status": "in_progress",
  "assigned_to": "manager",
  "priority": 1
}
```

**Delete Task**
- `DELETE /api/tasks/<id>` - Delete task (admin only)

**Statistics**
- `GET /api/stats` - Get task statistics for current user

**Administration**
- `GET /api/users` - List all users (admin only)

**Documentation**
- `GET /api/docs` - View API documentation

### Activity Logging

All user actions are logged to `activity_log.txt` in the project root directory. Logs include:

- Timestamp and username
- Action performed (create, read, update, delete)
- Resource type and ID
- Success/denial status
- Detailed change information

Example log entry:
```
2026-03-03 14:25:30 | vision_task.activity | INFO | ACTION: admin create task(...) | {...}
2026-03-03 14:25:45 | vision_task.activity | WARNING | ACCESS DENIED: clerk tried read on task(...) | {...}
```

### Running Tests

```bash
pip install pytest
pytest tests/
```

---

## Project Structure

```
Vision-Task-Project/
├── vision_task/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Flask application factory
│   ├── auth.py              # Authentication and RBAC
│   ├── models.py            # Data models (User, Task)
│   ├── tasks.py             # Task management logic
│   ├── logger.py            # Comprehensive audit logging
│   ├── templates/
│   │   ├── base.html        # Base template with navigation
│   │   ├── login.html       # Login page
│   │   ├── dashboard.html   # Task dashboard
│   │   ├── task_detail.html # Task detail view with editing
│   │   └── error.html       # Error page
│   └── static/              # Static files (CSS, JS)
├── tests/
│   └── test_app.py          # Test suite
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## Future Enhancements

To extend Vision Task for production use, consider implementing:

### Security
- [ ] Password-based authentication with bcrypt hashing
- [ ] Multi-factor authentication (MFA)
- [ ] HTTPS/TLS encryption
- [ ] LDAP/Active Directory integration for healthcare networks
- [ ] Session timeout and expiration

### Data Persistence
- [ ] PostgreSQL or MySQL database integration
- [ ] Encrypted storage for sensitive task data
- [ ] Database backup and disaster recovery
- [ ] Data retention policies for compliance

### Healthcare Integration
- [ ] EHR system integration (HL7 FHIR API)
- [ ] Patient data redaction for privacy
- [ ] HIPAA compliance validation
- [ ] Patient Privacy Act (PPA) reporting

### Advanced Features
- [ ] Task templates for common healthcare workflows
- [ ] Task dependencies and scheduling
- [ ] Team collaboration and comments
- [ ] Mobile application
- [ ] Email notifications
- [ ] Advanced search and filtering
- [ ] Performance analytics and dashboards

### Compliance & Audit
- [ ] Enhanced audit logging with digital signatures
- [ ] Compliance reporting (HIPAA, state regulations)
- [ ] Data retention and archival
- [ ] Log encryption and tamper detection
- [ ] Third-party audit access

---

## Important Security Notes

**This is a demonstration system.** In production deployments:

1. **Never use token-based authentication without passwords** - Implement proper password hashing (bcrypt, Argon2)
2. **Enable HTTPS** - Use TLS certificates for encrypted communication
3. **Use a production database** - Replace in-memory storage with PostgreSQL or similar
4. **Implement session management** - Add timeout and secure session cookies
5. **Configure CORS properly** - Restrict to trusted domains only
6. **Enable audit logging encryption** - Sign and encrypt audit logs
7. **Use environment variables** - Store secrets in `.env` files (never commit)
8. **Regular security audits** - Conduct penetration testing and code reviews

---

## Support & Contact

For questions about implementing Vision Task or healthcare management systems, contact the development team.

---

## License

This project is provided as-is for demonstration purposes.
