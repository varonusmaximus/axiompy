# Example: User Management Domain

Use this as a template for your own domain specifications:

```
# Domain: User Management Service

## Context (Optional)

**Business Case**: A growing SaaS company struggled with manual user provisioning across multiple systems, causing onboarding delays and security gaps. This API centralizes user management, reducing setup time from hours to minutes and ensuring consistent access control across all services.

**Impact**: Automated user lifecycle management (create, update, deactivate) with role-based access control enables the ops team to scale from 500 to 5000+ users without adding headcount.

**Use Cases**:
- User registration and profile management
- Email-based unique identification
- Admin panels for user queries
- Activity audit via timestamps

**Constraints**: Username and email globally unique, case-insensitive email handling.

## Resources

User:
- id: UUID (auto-generated)
- email: string (required, unique)
- username: string (required, unique, 3-50 chars)
- full_name: string (optional)
- is_active: bool (default true)
- created_at: timestamp (auto)
- updated_at: timestamp (auto)

## Endpoints

- GET /api/v1/users - List all users (paginated)
- POST /api/v1/users - Create new user
- GET /api/v1/users/{id} - Get user by ID
- PUT /api/v1/users/{id} - Update user
- DELETE /api/v1/users/{id} - Delete user

## Business Rules

1. Email must be valid email format
2. Username must be unique and alphanumeric
3. Email uniqueness is case-insensitive
4. Cannot modify immutable fields (created_at, id)

## Validation Rules

- email: valid email format, unique
- username: 3-50 chars, alphanumeric + underscore, unique
- full_name: optional, max 200 chars
- is_active: boolean

## Error Scenarios

- UserNotFound (404) - User doesn't exist
- UserConflict (409) - Email or username already taken
- ValidationError (400) - Invalid input
```

