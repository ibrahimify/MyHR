import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(frontendRoot, "..");
const backendRoot = path.join(repositoryRoot, "backend");
const runtimeDirectory = path.join(frontendRoot, ".playwright");
const databasePath = path.join(runtimeDirectory, `employees-${process.pid}.db`);
const databaseUrl = `sqlite:///${databasePath.replaceAll("\\", "/")}`;
const python = process.env.PYTHON_BIN || "python";
const port = process.env.E2E_API_PORT || "8100";

mkdirSync(runtimeDirectory, { recursive: true });
rmSync(databasePath, { force: true });

const environment = {
  ...process.env,
  MYHR_CORS_ORIGINS: "http://127.0.0.1:3100",
  MYHR_DATABASE_URL: databaseUrl,
  PYTHONPATH: [repositoryRoot, process.env.PYTHONPATH]
    .filter(Boolean)
    .join(path.delimiter),
};

function runPython(arguments_) {
  const result = spawnSync(python, arguments_, {
    cwd: backendRoot,
    env: environment,
    stdio: "inherit",
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

runPython(["-m", "alembic", "upgrade", "head"]);
runPython([
  "-m",
  "scripts.seed_local_demo",
  "--database-url",
  databaseUrl,
]);

const server = spawn(
  python,
  [
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    port,
  ],
  { cwd: backendRoot, env: environment, stdio: "inherit" },
);

let stopping = false;
function stop(signal = "SIGTERM") {
  if (stopping) return;
  stopping = true;
  server.kill(signal);
  setTimeout(() => server.kill("SIGKILL"), 3_000).unref();
}

process.on("SIGINT", () => stop("SIGINT"));
process.on("SIGTERM", () => stop("SIGTERM"));
server.on("error", (error) => {
  console.error(`Could not start the test API: ${error.message}`);
  rmSync(databasePath, { force: true });
  process.exit(1);
});
server.on("exit", (code) => {
  rmSync(databasePath, { force: true });
  process.exit(stopping ? 0 : (code ?? 1));
});
