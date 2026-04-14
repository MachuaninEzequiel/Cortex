---
title: Authentication System
tags: [auth, security, backend]
---

# Authentication System

This document describes the auth architecture used in the project.

## Overview

The auth system uses JWT-based refresh tokens with a middleware layer that validates sessions on every protected route.

## Key Components

- **auth.ts** — Express middleware for token validation
- **refresh_token.ts** — Handles token rotation and expiry
- **session.ts** — Session management utilities

## Login Flow

```
User → POST /auth/login
     → validate credentials
     → issue access_token (15min) + refresh_token (7 days)
     → store refresh_token hash in Redis
```

## Refresh Flow

```
Client → POST /auth/refresh
       → validate refresh_token
       → rotate: issue new pair
       → invalidate old refresh_token
```

## Common Issues

- Tokens not being rotated → caused by missing middleware in [[api]] routes
- Race condition on concurrent refresh → resolved by Redis lock

## Related Notes

- [[api]]
- [[architecture]]
