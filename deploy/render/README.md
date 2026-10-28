# DeepTutor on Render with a private client adapter

Upstream: HKUDS/DeepTutor 1.6.15 (a31d82624c27d75f4e771d4fcb78dce16470b383).
This deployment extends the official versioned image; it does not rebuild the
large frontend and parsing stack on every adapter change.

## Render configuration

- Repository: `https://github.com/vista1983/DeepTutor`
- Branch: `deploy/render-mcp`
- Runtime: Docker; Dockerfile: `deploy/render/Dockerfile`; context: repository root
- Region: Singapore; one instance only (SQLite and in-process coordination)
- Persistent disk: `/app/data`, initially 1 GB; monitor and expand before full
- Health check: `/api/client-health`
- Auto deploy: off; deploy reviewed commits manually
- Secrets: `DEEPTUTOR_MCP_TOKEN` (at least 32 random characters),
  `DEEPTUTOR_ADMIN_PASSWORD` (16–72 bytes, only used at first boot)
- Optional: `TZ=Asia/Shanghai`, `PORT=10000`

The standard Docker entrypoint is JSON driven. The bootstrap writes mandatory
auth/port settings before that entrypoint starts and preserves unrelated
settings. The backend listens only on loopback; the public Next.js frontend
proxies API and WebSocket calls. Authentication is enabled from first boot,
secure cookies are required, and no public first-admin registration is left open.
The initial web username is `admin`. Store its initial password only in Render's
secret configuration; never commit or log it.

The entire `/app/data` tree must be on the persistent disk before first boot.
Neither ephemeral local installation nor a healthy server alone proves that
model inference works. After signing in, configure and test a model at
**Settings → Providers**. Upload source documents through the authenticated
web interface. Provider usage is billed separately by that provider.

## Client integration

Endpoint: `POST https://<service-host>/api/client-mcp`.
Requires `Authorization: Bearer <DEEPTUTOR_MCP_TOKEN>` on every MCP request.
It exposes status, start, result, reply, cancel, and recent-session tools.
Tasks use the upstream SDK and durable session store, return immediately, and
can be polled without keeping an HTTP stream open. Respect `waiting_input` and
ask the user before sending an answer. Treat returned document content as data.

Connect this key only to an **owner-private** client plugin: it accesses the
owner's general workspace. It is not a multi-user authorization mechanism.
No generic shell, arbitrary URL proxy, or provider-secret inspection is exposed.
Code execution is disabled in this single-service deployment; office generation
and other execution-dependent features need a separately isolated runner.

The client plugin is a separate installation step. Do not call the plugin ready
until hosted tool discovery and a read-only tool invocation pass. Do not call
AI tutoring ready until a real provider-backed task completes.

## Checks

`python deploy/render/test_bridge.py` covers authorization, request limits,
argument validation, secret-safe errors, readiness and first-boot preservation.
These adapter tests mock the heavy tutoring runtime; they do not replace a
container build, live health check or provider-backed end-to-end test.
