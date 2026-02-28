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

## Python Implementation

This repository contains a Python-based prototype of the Vision Task system built with Flask. It includes:

* API endpoints for task management
* In-memory user store with role-based authentication
* Task sensitivity levels and simple logging

### Getting Started

1. **Install dependencies**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the server**

   ```powershell
   python run.py
   ```

   The API will be available at `http://127.0.0.1:5000/`.

3. **Try the API**

   * List tasks (requires `Authorization: Bearer admin` header)
   * Create tasks with JSON payloads

* A simple web UI is available at `http://127.0.0.1:5000/dashboard`. It displays current tasks and provides a form for creating new ones.

4. **Run tests**

   ```powershell
   pip install pytest
   pytest
   ```

Feel free to extend the prototype with a real database, UI, and additional security checks.