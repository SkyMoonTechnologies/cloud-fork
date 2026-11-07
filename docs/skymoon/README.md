# SkyMoon Cloud contributor handbook

> **Status:** SkyMoon is an evolving fork of Apache CloudStack. This handbook describes the current repository and an *experimental* development deployment, not a production-ready public cloud. The existing upstream CloudStack documentation remains relevant for the inherited subsystems.

## What we're building

SkyMoon aims to expose a unified customer portal, API, and billing/control plane for cloud products supplied by multiple providers and, later, infrastructure operated by SkyMoon. Customers select products, sizes and regions; SkyMoon selects the underlying provider. The current platform is a modified CloudStack monorepo. Its existing zone/pod/cluster/host and External hypervisor abstractions are **not yet proven** to support a fully provider-managed zone without conventional CloudStack networks/storage/system VMs.

Read the [provider-managed VM epic](https://github.com/SkyMoonTechnologies/cloud/issues/2). Do not mistake draft issue proposals for implemented behavior.

## Recommended reading order

1. This handbook and [architecture map](architecture.md).
2. [Development and testing](testing.md) and [contribution standards](contributing.md).
3. [ADR-0001: proposed provider-managed zone mode](decisions/ADR-0001-provider-managed-zones.md).
4. [Current development stack instructions](../../management/dev/README.md).
5. Upstream [installation](../../INSTALL.md), [contribution](../../CONTRIBUTING.md), [security](../../SECURITY.md), and [threat model](../../THREAT_MODEL.md) references.

## Repository map

| Path | Responsibility |
| --- | --- |
| `ui/` | Vue 3 customer/admin web interface. |
| `api/` | CloudStack management API commands and response definitions. |
| `server/` | User VM operations, zone configuration, network and account services. |
| `engine/orchestration/` | Network, storage and volume orchestration. |
| `plugins/hypervisors/external/` | Existing External VM planner, template adapter, resource/discoverer and executable provisioner. |
| `framework/extensions/` | Extension management and network orchestration hooks. |
| `extensions/` | Example implementations such as Proxmox and Hyper-V; **no committed DigitalOcean adapter on main at the time of writing**. |
| `developer/`, `management/dev/`, `compose.dev.yml` | Development DB bootstrap and source-built control plane. |
| `usage/` | CloudStack usage processing (not a finished SkyMoon customer billing integration). |

## First day: safe setup

1. Obtain authorized access to `SkyMoonTechnologies/cloud` and a development workstation with Git, Docker Engine + Compose, enough disk/RAM for a **large Maven build**, and Node.js/npm for the UI. The current management Dockerfile uses **Maven 3.9 + Java 17**, and the Compose database is **MySQL 8.4**.
2. Clone the SkyMoon repository, not the upstream Apache repository:
   ```bash
   git clone https://github.com/SkyMoonTechnologies/cloud.git
   cd cloud
   git switch -c feature/SKY-001-external-vm-trace
   ```
3. Read [management/dev/README.md](../../management/dev/README.md) before starting the backend. Replace the sample issue branch name with your ticket ID and short slug. Use a private LAN/Tailscale environment, never a public deployment.
4. Supply distinct, strong `SKYMOON_DEV_DB_PASSWORD` and `SKYMOON_DEV_DB_ROOT_PASSWORD` through Komodo or a **local untracked** environment file. Both are currently required to be alphanumeric by `management/dev/start.sh`. Do not paste them into tickets or commits.
5. Inspect the Compose config *before* any build or `up`. Run the non-destructive commands from [testing.md](testing.md).
6. Work on **one issue/branch**, document observed behavior and link your pull request to that issue. Prefer a spike/research ticket if runtime assumptions have not been verified.

**Do not** run `docker compose down --volumes` or `mvn -Pdeveloper -pl developer -Ddeploydb` against an existing database without an explicit backup/reset decision. The developer startup script currently invokes schema initialization only when its `cloud.configuration` table is missing; that is not a tested migration or recovery system.

## Current environment facts vs open gaps

- **Documented in the repository:** three Compose services (MySQL, Java management server, nginx-served Vue UI); frontend host port `5081`; a persistent named MySQL volume; the management server is not directly published; the Vue proxy routes `/client/` to the backend.
- **Previously observed on a development server, not independently reproduced here:** login to the development management API and successful DigitalOcean API credential check.
- **Not yet guaranteed:** full clean install on every workstation, real provider zone creation, provider-owned VM disks/IP integration, billing, secure production operation.
- **DigitalOcean adapter status:** development experiment from an earlier session. The GitHub `main` directory listing did **not** contain `extensions/DigitalOcean`; a newcomer must not assume the experiment is in source control. See [SKY-018](https://github.com/SkyMoonTechnologies/cloud/issues/20).

## Where to start contributing

- [SKY-001](https://github.com/SkyMoonTechnologies/cloud/issues/3): trace the current External VM lifecycle before changing core logic.
- [SKY-002](https://github.com/SkyMoonTechnologies/cloud/issues/4): define the provider-neutral contract after the trace.
- [SKY-003](https://github.com/SkyMoonTechnologies/cloud/issues/5): validate safe database persistence/restart before stateful tests.
- [SKY-004](https://github.com/SkyMoonTechnologies/cloud/issues/6): establish mocked tests instead of using paid provider APIs in CI.

For a new contributor, start with one of these foundational issues, not with a large change to storage, zones or the scheduler.
