# MyHR Frontend

Next.js App Router frontend for the MyHR web platform.

## Current status

The frontend is an intentionally small Phase 1 scaffold. It builds successfully
with TypeScript, Tailwind CSS and Framer Motion. Authenticated application
screens are deferred until the FastAPI authentication and endpoint contracts
are implemented. The current page is not a production deployment.

## Development

```powershell
npm ci
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
