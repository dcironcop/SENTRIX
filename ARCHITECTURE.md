# Sentrix Architecture

## Overview
Sentrix là hệ thống quản lý và tra cứu camera giám sát, được xây dựng với Flask framework.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│  (Browser - HTML/CSS/JavaScript)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Templates  │  │  Static Files│  │   API Docs   │     │
│  │  (Jinja2)    │  │  (CSS/JS)    │  │  (Swagger)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        Route Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Auth   │  │  Camera  │  │  Map     │  │ Dashboard│  │
│  │  Blueprint│  │ Blueprint│  │ Blueprint│  │ Blueprint│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ CameraService    │  │ UserService      │                │
│  │ - Business Logic │  │ - Business Logic │                │
│  └──────────────────┘  └──────────────────┘                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ CameraRepository │  │ UserRepository   │                │
│  │ - DB Access      │  │ - DB Access      │                │
│  └──────────────────┘  └──────────────────┘                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Validation Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ CameraValidators │  │ UserValidators   │                │
│  │ (Pydantic)       │  │ (Pydantic)       │                │
│  └──────────────────┘  └──────────────────┘                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Models     │  │   Database    │  │    Cache     │    │
│  │ (SQLAlchemy) │  │  (SQLite/     │  │  (Redis/      │    │
│  │              │  │   PostgreSQL) │  │   Memory)    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Presentation Layer
- **Templates**: Jinja2 templates for HTML rendering
- **Static Files**: CSS, JavaScript, images
- **API Documentation**: Swagger/OpenAPI docs

### 2. Route Layer (Blueprints)
- Handle HTTP requests/responses
- Request validation
- Authentication/Authorization
- Call service layer

### 3. Service Layer
- Business logic
- Transaction management
- Orchestration of multiple repositories
- Audit logging

### 4. Repository Layer
- Database access abstraction
- CRUD operations
- Query building
- No business logic

### 5. Validation Layer
- Input validation using Pydantic
- Data transformation
- Schema validation

### 6. Data Layer
- SQLAlchemy models
- Database connection
- Caching layer

## Security Layers

1. **Authentication**: Flask-Login
2. **Authorization**: Role-based (admin, officer, viewer)
3. **CSRF Protection**: Flask-WTF
4. **Rate Limiting**: Flask-Limiter
5. **Input Sanitization**: Bleach
6. **2FA**: pyotp
7. **Password Policy**: Custom validation

## Data Flow Example: Create Camera

```
1. User submits form → Route Layer (camera_bp.create)
2. Route validates request → Validation Layer (CameraCreateSchema)
3. Route calls service → Service Layer (CameraService.create_camera)
4. Service calls repository → Repository Layer (CameraRepository.save)
5. Repository saves to DB → Data Layer (SQLAlchemy)
6. Service logs audit → Security Layer (log_audit)
7. Service returns result → Route Layer
8. Route renders response → Presentation Layer
```

## Testing Strategy

- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test API endpoints
- **E2E Tests**: Test complete user flows with Selenium

## Dependencies

- **Flask**: Web framework
- **SQLAlchemy**: ORM
- **Flask-Login**: Authentication
- **Pydantic**: Validation
- **Flask-RESTX**: API documentation
- **pytest**: Testing framework
