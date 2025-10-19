# Workspace App

The Workspace app manages workspaces (organizations), their branches in different locations, and the bookable spaces within those branches.

## Models

### Workspace
- **Purpose**: Represents an organization/workspace
- **Admin**: The user who owns/manages the workspace
- **Fields**: 
  - Basic info: name, description, logo, website
  - Contact: email, phone
  - Address: address, city, state, country, postal_code
  - Status: is_active

### Branch
- **Purpose**: Represents a physical location of a workspace
- **Workspace**: Foreign key to parent workspace
- **Manager**: User responsible for managing the branch
- **Fields**:
  - Basic info: name, description
  - Contact: email, phone
  - Location: address, city, state, country, postal_code
  - Coordinates: latitude, longitude (for mapping)
  - Status: is_active

### Space
- **Purpose**: Represents a bookable space/room within a branch
- **Branch**: Foreign key to parent branch
- **Fields**:
  - Basic info: name, description, space_type
  - Pricing: hourly_rate, daily_rate, monthly_rate
  - Capacity: capacity (number of people)
  - Media: image_url, amenities (JSON)
  - Status: is_available

### WorkspaceUser
- **Purpose**: Manages workspace membership and roles
- **Roles**: admin, manager, staff
- **Fields**:
  - Workspace, User, Role, is_active
  - Timestamps: joined_at

## API Endpoints

### Workspace Endpoints
- `POST /api/workspace/workspaces/create/` - Create workspace
- `GET /api/workspace/workspaces/` - List all user workspaces
- `GET /api/workspace/workspaces/<id>/` - Get workspace details
- `PUT /api/workspace/workspaces/<id>/` - Update workspace
- `DELETE /api/workspace/workspaces/<id>/` - Delete workspace

### Branch Endpoints
- `POST /api/workspace/workspaces/<workspace_id>/branches/create/` - Create branch
- `GET /api/workspace/workspaces/<workspace_id>/branches/` - List workspace branches
- `GET /api/workspace/branches/<branch_id>/` - Get branch details
- `PUT /api/workspace/branches/<branch_id>/` - Update branch
- `DELETE /api/workspace/branches/<branch_id>/` - Delete branch

### Space Endpoints
- `POST /api/workspace/branches/<branch_id>/spaces/create/` - Create space
- `GET /api/workspace/branches/<branch_id>/spaces/` - List branch spaces
- `GET /api/workspace/spaces/<space_id>/` - Get space details
- `PUT /api/workspace/spaces/<space_id>/` - Update space
- `DELETE /api/workspace/spaces/<space_id>/` - Delete space

## Permissions

- **Workspace Admin**: Can create branches, add members, manage spaces
- **Branch Manager**: Can manage spaces in their branch, update branch info
- **Staff**: Can view workspace, branches, and spaces (read-only)

## Structure

```
workspace/
├── migrations/          # Database migrations
├── serializers/         # DRF serializers
├── services/            # Business logic services
├── tests/               # Unit and integration tests
├── validators/          # Custom validators
├── views/               # API views
│   ├── workspace.py     # Workspace views
│   ├── branch.py        # Branch views
│   └── space.py         # Space views
├── admin.py             # Django admin interface
├── apps.py              # App configuration
├── models.py            # Data models
├── urls.py              # URL routing
└── README.md            # This file
```

## Usage Examples

### Create a Workspace
```python
POST /api/workspace/workspaces/create/
{
  "name": "Tech Hub",
  "description": "A modern co-working space",
  "email": "info@techhub.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "country": "USA"
}
```

### Create a Branch
```python
POST /api/workspace/workspaces/<workspace_id>/branches/create/
{
  "name": "Downtown Branch",
  "description": "Our main office downtown",
  "email": "downtown@techhub.com",
  "phone": "+1234567891",
  "address": "456 Oak Ave",
  "city": "New York",
  "country": "USA",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

### Create a Space
```python
POST /api/workspace/branches/<branch_id>/spaces/create/
{
  "name": "Meeting Room A",
  "description": "Small meeting room for 4-6 people",
  "space_type": "meeting_room",
  "capacity": 6,
  "hourly_rate": "25.00",
  "daily_rate": "150.00",
  "monthly_rate": "2000.00",
  "amenities": ["projector", "whiteboard", "video_conference"],
  "is_available": true
}
```
