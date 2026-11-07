# Development environments and test guide

**Scope:** safe developer commands documented from the current SkyMoon repo. A reproducible fully mocked CloudStack VM deployment **does not exist yet**; see [SKY-034](https://github.com/SkyMoonTechnologies/cloud/issues/36) and [SKY-004](https://github.com/SkyMoonTechnologies/cloud/issues/6). Commands below are classified by risk and validation status.

## Current source-built environment

`compose.dev.yml` defines:
- `skymoon-db`: MySQL 8.4, persistent volume `skymoon-dev-mysql`.
- `skymoon-management`: Java 17 / Maven 3.9 source build, internal port 8080, development Jetty runtime.
- `skymoon-ui`: Vue UI served by nginx at host port 5081, proxying `/client/` to management.

The complete source-build command in `management/dev/Dockerfile` is:
```bash
mvn -B -Pdeveloper -DskipTests -pl :cloud-client-ui,:cloud-developer -am clean install
```
It is **expensive**; do not treat it as a quick documentation check. Maven 3.9 and Java 17 are the verified container toolchain selections. This guide has not independently built the image or run live VM provisioning.

## Safe preflight (no infrastructure changes)

From the repository root, confirm Docker/Compose availability:

```bash
docker compose version
git status --short
git rev-parse --abbrev-ref HEAD
```

For `docker compose config`, set local variables **without putting secrets into a checked-in file**, or use Komodo's configured environment. To avoid expanding secrets in terminal output, use `--quiet`:

```bash
# In a private development shell with the values already provided:
docker compose -f compose.dev.yml config --quiet
```

This validates Compose syntax and environment-variable presence; it **does not** prove the app will start.

## Frontend checks

The following scripts were verified as *present in* `ui/package.json` on `main`; they have **not been executed in this review**.

```bash
cd ui
npm ci
npm run lint
npm run test:unit
npm run build
```

Run them in your own workstation/CI context and record Node/npm versions and exit codes. This UI uses a Vue CLI + Webpack 4 toolchain; some Node versions may require compatibility adjustments. Do not assume a Node 24 build works without checking. The UI demo image may have its own Dockerfile configuration.

## Backend checks

Do targeted Maven tests when a change affects Java modules. For example, start by reading the module's POM and tests, then run the relevant Maven reactor selection with test execution enabled. Document the exact command and environment in the PR. Do not run `-DskipTests` and report it as test coverage.

For shell/Python provider adapters, prioritize non-networked test doubles. The current `main` repository contains sample extensions in `extensions/Proxmox`, `extensions/HyperV`, and `extensions/MaaS`; it **does not** contain the DigitalOcean pilot adapter in `extensions/DigitalOcean`. The only externally hosted provider account should be used in an explicitly approved manual test.

## Startup and persistence risks

From a trusted local environment with proper credentials, `docker compose -f compose.dev.yml up -d` can build/start the development stack and may run expensive DB initialization. It is not a harmless test command; don't run against shared customer or production data.

`management/dev/start.sh`:
1. validates two DB password variables (alphanumeric currently required);
2. generates local DB connection configuration for `skymoon-db`;
3. calls developer `deploydb` **only when** the `cloud.configuration` table is absent;
4. launches Jetty on port 8080.

This conditional is a rudimentary initial bootstrap check, **not** a migration strategy or assurance of restart safety. [SKY-003](https://github.com/SkyMoonTechnologies/cloud/issues/5) still owns validation of reset/recovery scenarios.

**Never run** these without an explicit reset/backup decision:
```text
docker compose down --volumes
mvn -Pdeveloper -pl developer -Ddeploydb
```

Do not publish `5081` or `/client/` to the public internet in the existing developer configuration; use LAN/Tailscale or equivalent private access.

## Test tiers and evidence

| Tier | Intended scope | Must not do |
| --- | --- | --- |
| Documentation/static | Links, file references, Git branch and Compose `config --quiet` | Run live billing/provider operations |
| UI/unit | Vue lint/unit/build | Assume browser or backend API passed |
| Backend unit | Targeted Maven/JUnit for changed Java module | Reset shared DB implicitly |
| Provider contract | Mock extension payloads, errors, timeouts and idempotency | Use a real token in CI |
| Integration | Disposable test DB + fake or replayed provider | Touch production endpoints |
| Manual live pilot | One authorized small VM, explicit budget cap, verified teardown | Create assets automatically in CI |

For each PR, include commands, environment versions, test outputs and known untested paths.

## What SKY-034 must deliver before it can close

- A documented, automated **no-cost** local setup with repeatable management API login/health and no external provider credentials.
- A scripted/mock provider VM lifecycle that runs against the real CloudStack API path (not merely a standalone Python unit test).
- Setup/teardown that preserves unrelated data, with deterministic cleanup and no duplicate billable VM.
- CI coverage plus exact re-run instructions for a new developer.

This file documents current limits; it does not claim that these acceptance tests have already passed.
