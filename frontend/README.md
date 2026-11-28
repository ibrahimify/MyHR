# MyHR Frontend

Next.js App Router frontend for the MyHR web platform.

## Current status

The responsive employee directory supports list, detail, search, filtering,
create and update workflows. Supabase email/password sign-in, session tracking,
sign-out and bearer-token API requests are implemented. Hosted use requires a
linked MyHR profile; local browser tests use the isolated development mode.

## Development

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Checks

```powershell
npm run lint
npm run build
```

## Boundaries

- Reuse the established MyHR information architecture and terminology.
- Treat the FastAPI OpenAPI contract as the source of truth for server data.
- Never place Supabase service-role keys or database credentials in frontend
  environment variables.
- Browser-visible Supabase values must be limited to intentionally public
  configuration, with authorization enforced by the backend and RLS.
- Do not expose desktop demonstration credentials in the web interface.

See the repository [README](../README.md) and
[Web Port Handover](../docs/WEB_PORT_HANDOVER.md) for architecture and roadmap.
