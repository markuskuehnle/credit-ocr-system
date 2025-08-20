# Database Directory

This directory contains all database-related files for the credit OCR system.

## Structure

```
database/
├── schemas/          # Database schema definitions
│   └── schema.sql   # Initial database schema
├── migrations/       # Database migration files (future use)
├── seeds/           # Seed data files (future use)
└── README.md        # This file
```

## Usage

### Schemas
- `schemas/schema.sql` - Contains the initial database structure
- Mounted into PostgreSQL container at `/schema`
- Automatically loaded when the database container starts

### Migrations (Future)
- Place database migration files here when implementing version control
- Use tools like Alembic or Flyway for managing schema changes

### Seeds (Future)
- Place initial data files here for populating the database
- Useful for development and testing environments

## Docker Integration

The `compose.yml` file mounts the `schemas/` directory into the PostgreSQL container, making the schema files available for initialization.
