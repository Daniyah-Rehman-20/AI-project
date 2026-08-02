# Contributing

## Branching

- Feature branches: `cursor/<short-description>-xxxx`
- PRs target `main`
- CI must be green (lint, tests, Docker build)

## Backend standards

- Type hints on all public functions
- No business logic in routers
- Repository for persistence; Service for orchestration
- Raise `AppException` subclasses for expected errors
- Add unit/API tests with every module change

## Frontend standards

- Strict TypeScript
- Feature folders under `features/`
- Shared UI in `components/ui`
- Prefer TanStack Query for server state; Zustand for auth/UI only

## Commit messages

Use imperative mood: `Add incident analysis worker`, `Fix JWT refresh rotation`.
