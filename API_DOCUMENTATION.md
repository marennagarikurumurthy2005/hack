# Village Governance Backend API

## 1. Overview

This backend provides a village-governance platform with:

- multi-role access control
- citizen complaint management
- citizen suggestions and feedback tracking
- development project management
- budget allocation and expenditure tracking
- project progress and milestone monitoring
- village-wise dashboards
- reports and analytics
- scheme publishing
- JWT authentication
- MongoDB persistence
- Cloudinary image storage

Application data is stored in MongoDB. Django also uses a small local SQLite database only for its internal command bookkeeping.

## 2. Feature coverage

### Project Management

- create development projects
- manage projects across multiple villages
- assign a project owner
- assign responsible team members
- create project activities
- create project milestones
- update project workflows and status
- maintain structured project progress timelines

### Budget Tracking

- define project budgets
- manage allocation breakdowns
- track expenditures
- calculate spent and remaining amounts
- expose budget visibility in project and village dashboards

### Progress Monitoring

- update project completion percentages
- track milestone completion
- track project activity completion
- publish timeline-style progress updates
- expose chart-friendly project analytics

### Village Dashboard

- village-wise aggregated project, complaint, feedback, scheme, and budget data
- central dashboard listing all villages
- per-village detail dashboard
- recent activity summaries

### Citizen Feedback

- location-aware complaint workflow
- citizen suggestion and feedback workflow
- public participation records
- admin response and status tracking

### Reports & Analytics

- overview analytics
- project performance reports
- village performance reports
- chart-ready status and workflow datasets

## 3. Roles

- `citizen`
- `government_employee`
- `ward_member`
- `admin`
- `super_admin`

### Role rules

- all normal registrations start as `pending`
- `super_admin` can log in without manual verification
- only `super_admin` can verify users and change user roles
- `admin` and `super_admin` manage projects, schemes, and reports
- operational users can be assigned to projects and complaints

## 4. Tech stack

- Django `6.0.6`
- Django REST Framework `3.17.1`
- MongoDB via `pymongo`
- JWT via `PyJWT`
- Cloudinary via `cloudinary`

## 5. Project structure

- `api/views/auth.py` - authentication endpoints
- `api/views/users.py` - user verification and role management
- `api/views/complaints.py` - complaint workflow
- `api/views/projects.py` - projects, activities, milestones, budgets, expenditures, progress
- `api/views/feedback.py` - suggestions and stakeholder feedback
- `api/views/dashboard.py` - admin dashboard summary
- `api/views/villages.py` - village dashboards
- `api/views/reports.py` - analytics and reports
- `api/views/schemes.py` - government schemes
- `api/services/analytics_service.py` - dashboard/report aggregation
- `api/repositories.py` - MongoDB data access

## 6. Environment setup

Copy `.env.example` to `.env` and fill the values.

### Required variables

- `DJANGO_SECRET_KEY`
- `JWT_SECRET_KEY`
- `MONGODB_URI`
- `MONGODB_DATABASE`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

### Important optional variables

- `DEBUG`
- `ALLOWED_HOSTS`
- `TIME_ZONE`
- `DJANGO_SQLITE_NAME`
- `CORS_ALLOW_ALL_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `AUTO_BOOTSTRAP_BACKEND`
- `SUPER_ADMIN_EMAIL`
- `SUPER_ADMIN_USERNAME`
- `SUPER_ADMIN_PASSWORD`

## 7. Local commands

### Install dependencies

- `pip install -r requirements.txt`

### Prepare Django internal tables

- `python manage.py migrate`

### Create indexes and optional bootstrap super admin

- `python manage.py bootstrap_backend`

### Create the first platform super admin

Interactive:

- `python manage.py createsuperuser`

Non-interactive:

- `python manage.py createsuperuser --email owner@example.com --username owner --password ChangeMe123! --non-interactive`

Only `email`, `username`, and `password` are required. Internal profile fields for the platform super admin are auto-filled automatically.

### Run the API

- `python manage.py runserver`

## 8. Authentication

The API uses bearer JWT tokens.

### Header

`Authorization: Bearer <token>`

### Login identifier support

Users can log in with:

- email
- username
- mobile number

### Auth endpoints

#### `POST /api/auth/register/`

Registers a non-super-admin user.

**Auth:** Public

**Content types:**

- `application/json`
- `multipart/form-data`

**Base fields**

- `full_name`
- `email`
- `mobile_number`
- `password`
- `role`
- `village`
- `ward_number` optional
- `district`
- `state`
- `pincode`
- `address_line1`
- `address_line2` optional
- `identity_document` optional image

**Citizen-only fields**

- `government_id_type`
- `government_id_number`

**Employee, ward member, admin fields**

- `employee_id`
- `department`
- `designation`

#### `POST /api/auth/login/`

Logs in with `identifier` and `password`.

**Auth:** Public

**Body**

```json
{
  "identifier": "owner",
  "password": "ChangeMe123!"
}
```

#### `POST /api/auth/logout/`

Stateless logout.

**Auth:** Logged-in user

#### `GET /api/auth/me/`

Returns the authenticated user profile.

**Auth:** Logged-in user

#### `POST /api/auth/change-password/`

Changes the current password.

**Auth:** Logged-in user

## 9. Users

### `GET /api/users/`

Lists users.

**Auth:** `admin`, `super_admin`

**Query params**

- `page`
- `page_size`
- `role`
- `verification_status`
- `village`
- `district`
- `search`

### `GET /api/users/pending/`

Lists pending users.

**Auth:** `admin`, `super_admin`

### `GET /api/users/{user_id}/`

Returns a user record.

**Auth:** self, `admin`, `super_admin`

### `PATCH /api/users/{user_id}/verification/`

Updates verification status.

**Auth:** `super_admin`

**Body**

```json
{
  "verification_status": "approved",
  "review_notes": "Verified by super admin."
}
```

### `PATCH /api/users/{user_id}/role/`

Changes user role.

**Auth:** `super_admin`

## 10. Projects

Projects cover multi-village development work, ownership, team assignment, structured workflows, budgets, milestones, and progress.

### Project status values

- `planned`
- `active`
- `on_hold`
- `completed`
- `cancelled`

### Workflow stages

- `planning`
- `approval`
- `execution`
- `monitoring`
- `closure`

### Activity status values

- `not_started`
- `in_progress`
- `blocked`
- `completed`

### Milestone status values

- `pending`
- `achieved`
- `delayed`

### `GET /api/projects/`

Lists projects.

**Auth:** Public

**Query params**

- `page`
- `page_size`
- `status`
- `workflow_stage`
- `priority`
- `village`
- `district`
- `state`
- `owner_user_id`
- `responsible_user_id`
- `mine=true`
- `search`

### `POST /api/projects/`

Creates a project.

**Auth:** `admin`, `super_admin`

**Body**

```json
{
  "name": "Road Expansion Phase 1",
  "summary": "Main road improvement across two villages.",
  "description": "Widening and resurfacing the main rural road.",
  "category": "roads",
  "priority": "high",
  "status": "planned",
  "workflow_stage": "planning",
  "villages": ["Village A", "Village B"],
  "district": "Nalgonda",
  "state": "Telangana",
  "start_date": "2026-06-10",
  "target_end_date": "2026-12-31",
  "owner_user_id": "<user_id>",
  "responsible_user_ids": ["<user_id_1>", "<user_id_2>"],
  "budget_allocated_amount": 2500000,
  "budget_currency": "INR",
  "budget_allocations": [
    {"category": "materials", "amount": 1500000},
    {"category": "labor", "amount": 1000000}
  ],
  "tags": ["roads", "connectivity"],
  "target_beneficiaries": 3500
}
```

### `GET /api/projects/{project_id}/`

Returns project detail including:

- project core data
- activity list
- milestone list
- progress updates
- expenditures
- summary metrics

**Auth:** Public

### `PATCH /api/projects/{project_id}/`

Updates project metadata.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

### `DELETE /api/projects/{project_id}/`

Deletes the project and its child records.

**Auth:** `admin`, `super_admin`

## 11. Project activities

### `GET /api/projects/{project_id}/activities/`

Lists project activities.

**Auth:** Public

### `POST /api/projects/{project_id}/activities/`

Creates a project activity.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

**Body**

```json
{
  "title": "Tender publication",
  "description": "Publish tender notice",
  "status": "not_started",
  "assigned_to_user_id": "<user_id>",
  "due_date": "2026-06-20",
  "priority": "high",
  "dependency_ids": []
}
```

### `PATCH /api/projects/{project_id}/activities/{activity_id}/`

Updates an activity.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

## 12. Project milestones

### `GET /api/projects/{project_id}/milestones/`

Lists project milestones.

**Auth:** Public

### `POST /api/projects/{project_id}/milestones/`

Creates a milestone.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

**Body**

```json
{
  "title": "Administrative approval",
  "description": "Approval from district office",
  "target_date": "2026-06-30",
  "status": "pending",
  "weight_percent": 15
}
```

### `PATCH /api/projects/{project_id}/milestones/{milestone_id}/`

Updates milestone status or metadata.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

## 13. Project progress monitoring

### `GET /api/projects/{project_id}/progress/`

Lists project progress updates.

**Auth:** Public

### `POST /api/projects/{project_id}/progress/`

Creates a project progress update and optionally updates project status/workflow/progress percent.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

**Body**

```json
{
  "message": "Survey completed and execution started.",
  "progress_percent": 20,
  "status": "active",
  "workflow_stage": "execution",
  "risk_level": "medium"
}
```

## 14. Project budgets and expenditures

### `PATCH /api/projects/{project_id}/budget/`

Updates the allocated budget and allocation plan.

**Auth:** `admin`, `super_admin`

**Body**

```json
{
  "allocated_amount": 2600000,
  "currency": "INR",
  "allocations": [
    {"category": "materials", "amount": 1600000},
    {"category": "labor", "amount": 1000000}
  ],
  "notes": "Revised after market update"
}
```

### `GET /api/projects/{project_id}/expenditures/`

Lists recorded expenditures.

**Auth:** Public

### `POST /api/projects/{project_id}/expenditures/`

Records expenditure and automatically recalculates spent and remaining budget.

**Auth:** `admin`, `super_admin`, project owner, responsible internal users

**Body**

```json
{
  "amount": 250000,
  "category": "materials",
  "description": "Initial materials purchase",
  "spent_on": "2026-06-18",
  "vendor": "ABC Infra Supplies",
  "receipt_reference": "REC-1001",
  "approved_by_user_id": "<user_id>"
}
```

## 15. Complaints

Complaints remain the formal workflow for village problems and issue resolution.

### `GET /api/complaints/`

Lists complaints.

**Auth:** Public

**Query params**

- `page`
- `page_size`
- `status`
- `priority`
- `category`
- `village`
- `district`
- `state`
- `ward_number`
- `complaint_number`
- `created_by`
- `assigned_to`
- `search`
- `mine=true`

### `POST /api/complaints/`

Creates a complaint.

**Auth:** `citizen`, `super_admin`

### `GET /api/complaints/{complaint_id}/`

Returns complaint detail and progress timeline.

**Auth:** Public

### `PATCH /api/complaints/{complaint_id}/`

Updates complaint detail or status.

**Auth:** `admin`, `super_admin`

### `PATCH /api/complaints/{complaint_id}/assign/`

Assigns complaint to an operational user.

**Auth:** `admin`, `super_admin`

### `GET /api/complaints/{complaint_id}/progress/`

Lists complaint progress updates.

**Auth:** Public

### `POST /api/complaints/{complaint_id}/progress/`

Adds a complaint progress update.

**Auth:** assigned operational user, `admin`, `super_admin`

## 16. Citizen feedback

Feedback is separate from complaints and is intended for:

- suggestions
- stakeholder comments
- general public participation
- requests
- appreciation
- lightweight complaints

### Feedback type values

- `suggestion`
- `feedback`
- `complaint`
- `appreciation`
- `request`

### Feedback status values

- `open`
- `in_review`
- `responded`
- `closed`

### `GET /api/feedback/`

Lists feedback.

**Auth:** Public for public records, scoped access for own/admin data

**Query params**

- `page`
- `page_size`
- `feedback_type`
- `status`
- `village`
- `district`
- `state`
- `mine=true`
- `search`

### `POST /api/feedback/`

Creates a feedback record.

**Auth:** Logged-in user

**Content types**

- `application/json`
- `multipart/form-data`

**Body**

```json
{
  "feedback_type": "suggestion",
  "subject": "Need skill center",
  "message": "The village needs a youth skill development center.",
  "category": "education",
  "village": "Village A",
  "ward_number": "3",
  "district": "Nalgonda",
  "state": "Telangana",
  "is_public": true
}
```

Optional uploaded files:

- `images`

### `GET /api/feedback/{feedback_id}/`

Returns a feedback record.

**Auth:** Public if `is_public=true`, otherwise owner/admin/super_admin

### `PATCH /api/feedback/{feedback_id}/`

Updates a feedback record.

**Auth:** owner while status is `open`, or `admin`, `super_admin`

### `POST /api/feedback/{feedback_id}/respond/`

Stores the administration response and status.

**Auth:** `admin`, `super_admin`

**Body**

```json
{
  "response_message": "The proposal has been forwarded to the district planning committee.",
  "status": "responded"
}
```

## 17. Schemes

### `GET /api/schemes/`

Lists schemes.

**Auth:** Public for published schemes

### `POST /api/schemes/`

Creates a scheme.

**Auth:** `admin`, `super_admin`

### `GET /api/schemes/{scheme_id}/`

Returns scheme detail.

**Auth:** Public if published

### `PATCH /api/schemes/{scheme_id}/`

Updates a scheme.

**Auth:** `admin`, `super_admin`

### `DELETE /api/schemes/{scheme_id}/`

Deletes a scheme.

**Auth:** `admin`, `super_admin`

## 18. Admin dashboard

### `GET /api/dashboard/stats/`

Returns central admin dashboard data including:

- users by role and verification
- projects by status and workflow
- complaints by status
- feedback by status and type
- scheme status counts
- recent projects
- recent complaints
- overview analytics

**Auth:** `admin`, `super_admin`

## 19. Village dashboards

### `GET /api/villages/dashboard/`

Lists dashboard summaries for all villages discovered from projects, complaints, feedback, and schemes.

**Auth:** Public

**Query params**

- `search`
- `district`
- `state`

### `GET /api/villages/{village_name}/dashboard/`

Returns one village dashboard with:

- project totals
- workflow and status breakdowns
- average project progress
- milestone summary
- budget totals
- complaint totals and recent items
- feedback totals and recent items
- scheme totals and recent items
- chart-ready datasets

**Auth:** Public

## 20. Reports and analytics

### `GET /api/reports/overview/`

Returns the top-level analytics overview.

**Auth:** `admin`, `super_admin`

**Includes**

- total projects, complaints, feedback, schemes, villages
- project status and workflow charts
- average progress
- budget totals
- complaint status chart
- feedback type and status chart
- top village performance rows

### `GET /api/reports/projects/`

Returns detailed project report output.

**Auth:** `admin`, `super_admin`

**Query params**

- `village`
- `district`
- `state`

### `GET /api/reports/villages/`

Returns village performance report output.

**Auth:** `admin`, `super_admin`

**Query params**

- `district`
- `state`

## 21. Image uploads

### `POST /api/uploads/images/`

Uploads a single image to Cloudinary.

**Auth:** Logged-in user

**Content type:** `multipart/form-data`

**Fields**

- `image`
- `folder`

### Supported folders

- `complaints`
- `progress`
- `projects`
- `feedback`
- `schemes`
- `identity-documents`
- `general`

## 22. Health

### `GET /api/health/`

Checks service and MongoDB connectivity.

**Auth:** Public

## 23. Common response format

### Success

```json
{
  "message": "Human readable message",
  "data": {}
}
```

### Paginated

```json
{
  "message": "Request processed successfully.",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_items": 24,
      "total_pages": 3,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

## 24. Common error behavior

- invalid or missing token returns auth errors
- unauthorized role access returns permission errors
- invalid Mongo object identifiers return validation errors
- invalid Cloudinary configuration returns image-upload validation errors
- invalid dates, status values, or list shapes return serializer validation errors

## 25. Recommended next enhancements

- add automated pytest API tests
- add Swagger or ReDoc generation
- add notifications for approvals, responses, and project updates
- add audit logs for sensitive actions
- add export endpoints for PDF or Excel reports
