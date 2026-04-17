---
title: System Architecture
tags: [architecture, backend, overview]
---

# System Architecture

High-level overview of the project structure and design decisions.

## Stack

| Layer       | Technology        |
|-------------|-------------------|
| API         | Node.js / Express |
| Auth        | JWT + Redis        |
| Database    | PostgreSQL         |
| Cache       | Redis              |
| Queue       | BullMQ             |
| Frontend    | React + Vite       |

## Service Map

```
Client
  └── API Gateway (Express)
        ├── Auth Service → [[auth]]
        ├── User Service
        ├── Payment Service
        └── Notification Service
```

## Design Principles

1. Each service owns its own data store
2. Services communicate via events (BullMQ)
3. All state mutations are logged for auditability

## Related Notes

- [[auth]]
- [[api]]
- [[release-2-known-weaknesses]]
