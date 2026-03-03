# Vision Task API Documentation

## Overview

Vision Task provides a RESTful API for healthcare task management with built-in authentication, role-based access control, and sensitivity-aware filtering.

## Authentication

All API endpoints (except `/login`) require Bearer token authentication. The token is simply the username in demo mode.

**Request Header:**
```
Authorization: Bearer <username>
```

**Example:**
```bash
curl -H "Authorization: Bearer admin" http://localhost:5000/api/tasks
```

## Base URL

```
http://localhost:5000/api
```

## Response Format

All responses are JSON. Successful responses include a 200-299 status code. Errors include:
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User lacks required permissions
- `404 Not Found` - Resource not found
- `400 Bad Request` - Invalid request data

## Endpoints

### Tasks

#### List Tasks
```
GET /api/tasks
```

Returns all tasks visible to the authenticated user, filtered by sensitivity level and accessibility.

**Authentication Required:** Yes

**Query Parameters:** None

**Response:**
```json
{
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Update patient records",
      "description": "Review Q1 patient records",
      "sensitivity": "high",
      "status": "in_progress",
      "created_by": "admin",
      "assigned_to": "clerk",
      "department": "Clinic",
      "priority": 2,
      "created_at": "2026-03-03T14:25:30.123456",
      "updated_at": "2026-03-03T14:30:15.654321"
    }
  ],
  "count": 1,
  "stats": {
    "total_tasks": 5,
    "by_status": {
      "new": 2,
      "assigned": 1,
      "in_progress": 1,
      "completed": 1,
      "cancelled": 0
    },
    "by_sensitivity": {
      "low": 2,
      "medium": 2,
      "high": 1
    },
    "assigned_to_user": 2,
    "created_by_user": 3
  }
}
```

**Filtering Behavior:**
- Admin users see all tasks
- Manager users see all high and medium sensitivity tasks
- Standard users see only low/medium tasks they created or are assigned to
- Access denial attempts are logged for audit trail

---

#### Get Task
```
GET /api/tasks/<task_id>
```

Retrieve a single task with full details. Access control is enforced.

**Authentication Required:** Yes

**Parameters:**
- `task_id` (path) - UUID of the task

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Update patient records",
  "description": "Review Q1 patient records",
  "sensitivity": "high",
  "status": "in_progress",
  "created_by": "admin",
  "assigned_to": "clerk",
  "department": "Clinic",
  "priority": 2,
  "created_at": "2026-03-03T14:25:30.123456",
  "updated_at": "2026-03-03T14:30:15.654321"
}
```

**Status Codes:**
- `200 OK` - Task retrieved successfully
- `404 Not Found` - Task does not exist or access denied
- `401 Unauthorized` - Missing authentication

---

#### Create Task
```
POST /api/tasks
```

Create a new task with sensitivity level, priority, and assignment.

**Authentication Required:** Yes

**Request Body:**
```json
{
  "title": "Process insurance claims",
  "description": "Review and process March insurance submissions",
  "sensitivity": "medium",
  "assigned_to": "staff",
  "priority": 1
}
```

**Fields:**
- `title` (string, required) - Task title
- `description` (string, optional) - Detailed task description
- `sensitivity` (string, optional) - "low", "medium", or "high" (default: "low")
- `assigned_to` (string, optional) - Username to assign task to
- `priority` (integer, optional) - 0 (low), 1 (medium), 2 (high)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Process insurance claims",
  "description": "Review and process March insurance submissions",
  "sensitivity": "medium",
  "status": "new",
  "created_by": "manager",
  "assigned_to": "staff",
  "department": "Billing",
  "priority": 1,
  "created_at": "2026-03-03T14:25:30.123456",
  "updated_at": "2026-03-03T14:25:30.123456"
}
```

**Status Codes:**
- `201 Created` - Task created successfully
- `401 Unauthorized` - Missing authentication

**Audit:** Task creation is logged with full details

---

#### Update Task
```
PUT /api/tasks/<task_id>
```

Update a task. Only the task creator or administrators can modify tasks.

**Authentication Required:** Yes

**Parameters:**
- `task_id` (path) - UUID of the task

**Request Body:**
```json
{
  "title": "Process insurance claims - URGENT",
  "status": "in_progress",
  "assigned_to": "manager",
  "priority": 2
}
```

**Fields (all optional):**
- `title` (string) - New task title
- `description` (string) - Updated description
- `status` (string) - "new", "assigned", "in_progress", "completed", "cancelled"
- `assigned_to` (string) - Reassign to different user
- `priority` (integer) - 0, 1, or 2

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Process insurance claims - URGENT",
  "description": "Review and process March insurance submissions",
  "sensitivity": "medium",
  "status": "in_progress",
  "created_by": "manager",
  "assigned_to": "manager",
  "department": "Billing",
  "priority": 2,
  "created_at": "2026-03-03T14:25:30.123456",
  "updated_at": "2026-03-03T14:35:45.987654"
}
```

**Status Codes:**
- `200 OK` - Task updated successfully
- `404 Not Found` - Task not found or access denied
- `401 Unauthorized` - Missing authentication

**Audit:** All field changes are logged with before/after values

---

#### Delete Task
```
DELETE /api/tasks/<task_id>
```

Delete a task. **Admin only**

**Authentication Required:** Yes

**Authorization Required:** "admin" role

**Parameters:**
- `task_id` (path) - UUID of the task

**Response:**
```json
{
  "deleted": true
}
```

**Status Codes:**
- `200 OK` - Task deleted successfully
- `404 Not Found` - Task not found
- `403 Forbidden` - User lacks admin role
- `401 Unauthorized` - Missing authentication

**Audit:** Task deletion is logged with task details

---

### Statistics

#### Get User Statistics
```
GET /api/stats
```

Retrieve task statistics for the authenticated user.

**Authentication Required:** Yes

**Response:**
```json
{
  "user": "manager",
  "department": "Clinic",
  "stats": {
    "total_tasks": 12,
    "by_status": {
      "new": 3,
      "assigned": 2,
      "in_progress": 4,
      "completed": 2,
      "cancelled": 1
    },
    "by_sensitivity": {
      "low": 4,
      "medium": 5,
      "high": 3
    },
    "assigned_to_user": 5,
    "created_by_user": 8
  }
}
```

---

### Administration

#### List Users
```
GET /api/users
```

List all users in the system. **Admin only**

**Authentication Required:** Yes

**Authorization Required:** "admin" role

**Response:**
```json
{
  "users": [
    {
      "username": "admin",
      "roles": ["admin", "manager"],
      "department": "Administration",
      "can_view_high_sensitivity": true
    },
    {
      "username": "clerk",
      "roles": ["user"],
      "department": "Clinic",
      "can_view_high_sensitivity": false
    }
  ],
  "count": 4
}
```

**Status Codes:**
- `200 OK` - User list retrieved
- `403 Forbidden` - User lacks admin role
- `401 Unauthorized` - Missing authentication

---

### Documentation

#### API Documentation
```
GET /api/docs
```

Get API endpoint documentation.

**Response:**
```json
{
  "endpoints": [
    {
      "path": "/api/tasks",
      "method": "GET",
      "auth": true,
      "description": "List tasks visible to user"
    },
    {
      "path": "/api/tasks",
      "method": "POST",
      "auth": true,
      "description": "Create new task"
    }
  ]
}
```

---

## Sensitivity Levels & Access Control

### Sensitivity Levels

| Level | Clearance Required | Examples |
|-------|-------------------|----------|
| **Low** | None | General announcements, completed tasks |
| **Medium** | Manager+ | Internal policies, patient aggregate data |
| **High** | Admin | HIPAA-protected, individual patient records |

### Access Rules

- **Admin users**: View all tasks regardless of sensitivity
- **Manager users**: View high and medium sensitivity tasks
- **Standard users**: View only low/medium sensitivity + tasks they created/assigned to
- **Access denial**: Automatically logged for compliance

---

## Error Responses

### Authentication Error (401)
```json
{
  "error": "Unauthorized"
}
```

### Authorization Error (403)
```json
{
  "error": "Forbidden"
}
```

### Not Found (404)
```json
{
  "error": "Task not found or access denied"
}
```

---

## Rate Limiting & Throttling

Currently not implemented. For production, add:
- Rate limiting (e.g., 100 requests/minute)
- Backoff strategies for bulk operations
- Request signing for critical operations

---

## Audit Logging

All API operations are logged to `activity_log.txt` with:
- Timestamp (ISO 8601)
- Username
- Action (create, read, update, delete)
- Resource type and ID
- Success/denial status
- Detailed change information

**Log Example:**
```
2026-03-03 14:25:30 | vision_task.activity | INFO | ACTION: admin create task(...) | {...json...}
2026-03-03 14:25:45 | vision_task.activity | WARNING | ACCESS DENIED: clerk tried read on task(...) | {...json...}
```

---

## Example Workflows

### 1. Create and Assign a High-Priority Task

```bash
# Create task
curl -X POST http://localhost:5000/api/tasks \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review patient consent forms",
    "description": "Verify Q1 consent forms for HIPAA compliance",
    "sensitivity": "high",
    "assigned_to": "manager",
    "priority": 2
  }'

# Get task details
curl http://localhost:5000/api/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer manager"

# Update status
curl -X PUT http://localhost:5000/api/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer manager" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }'
```

### 2. Restricted Access Attempt

```bash
# Clerk attempts to view high-sensitivity task (will be denied)
curl http://localhost:5000/api/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer clerk"
# Response: 404 Not Found (or logged as access denial)
```

### 3. Get Statistics

```bash
curl http://localhost:5000/api/stats \
  -H "Authorization: Bearer manager"
```

---

## WebUI Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/login` | GET/POST | User login page |
| `/logout` | GET | Logout current user |
| `/dashboard` | GET | Main task dashboard |
| `/dashboard` | POST | Create task from form |
| `/task/<id>` | GET | View task details |
| `/task/<id>` | POST | Update task from form |

---

## Production Recommendations

Before deploying to production:

1. **Authentication**: Implement password hashing (bcrypt/Argon2), not bearer tokens
2. **Database**: Move from in-memory storage to PostgreSQL/MySQL
3. **Encryption**: Use HTTPS with valid SSL certificates
4. **Sessions**: Implement proper session management with timeout
5. **Validation**: Add comprehensive input validation
6. **Rate Limiting**: Implement request throttling
7. **Monitoring**: Add application monitoring and alerting
8. **Logging**: Encrypt and archive audit logs securely

---

## Support

For API issues or feature requests, contact the development team.
