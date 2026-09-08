# Local infrastructure

The scaffold binds both services to 127.0.0.1. SQLite is created under data/local on first API start. No containers, cloud resources or external AI providers are required.

Before shared hosting: implement authentication and tenant authorization; move to PostgreSQL plus private object storage; use versioned migrations; introduce an ingestion queue; cap request bodies at the reverse proxy; add malware scanning, audit, backup/restore and retention/deletion. Do not expose this local development server to a public network.
