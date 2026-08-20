# Infrastructure

Infrastructure owns local and deployment configuration for the independently deployed
frontend, backend, databases, and AI Service.

The deployment topology and environment naming are documented in
[`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md) and will become executable through
issue #24. Secrets remain outside the repository; use environment variables or a
secret manager at runtime.
