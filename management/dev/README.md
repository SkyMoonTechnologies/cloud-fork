# SkyMoon local development control plane (experimental)

This is a **source-built development prototype**, not a verified production
deployment. It provides three services from one Compose file:

- Vue frontend on host port 5081 (the existing port 5080 demo remains untouched).
- Java management backend, built from SkyMoon's current monorepo source.
- Persistent MySQL 8.4 database, private to the Compose network.

Unlike the existing `compose.demo.yml`, the UI proxies `/client/` to the local
Java backend rather than to Apache's public QA simulator.

## Deploy through Komodo

Create a **new** Stack named `skymoon-dev` using the same Komodo Local server.
Set Git repo `SkyMoonTechnologies/cloud`, branch `main`, and Compose File Path
`compose.dev.yml` (note **.yml**, not .yaml).

Set these **environment variables in Komodo, not Git**:

- `SKYMOON_DEV_DB_PASSWORD`: a unique random alphanumeric string (32+ chars).
- `SKYMOON_DEV_DB_ROOT_PASSWORD`: a different random alphanumeric string.

Save and Deploy. The initial Maven build is much heavier than the UI-only build.
You will need generous free storage and RAM for the Maven compiler and database.
Open `http://<your-komodo-server-ip>:5081` after the services are healthy.

If the API does not start, inspect the `skymoon-management` container logs.
The first run uses the existing `mvn -Pdeveloper -pl developer -Ddeploydb`
database setup and `mvn -pl :cloud-client-ui jetty:run` developer server
commands documented in this repository's `INSTALL.md`.

## Boundaries

- Keep this server LAN/Tailscale-only. This developer flow is not hardened for
  paying customers; existing development credentials may be insecure.
- Do not use `docker compose down --volumes` unless you intentionally want
  to **delete the development database**.
- A successful API start does not configure compute/networking/storage.
  Host registration is a separate step after the management API works.
- This stack does not expose host-agent control ports. Host integration requires
  additional routing/network and agent configuration.
- Source builds and database initialization have **not** been verified in the
  user's Komodo environment. Capture logs if the first build/start fails.


## Database bootstrap safety (SKY-003)

On startup, `management/dev/db-init-guard.sh` counts the development database tables and
checks `cloud.configuration`, `cloud.user`, and `cloud.data_center`.
It only permits `mvn ... -Ddeploydb` when the `cloud` schema has **zero tables**.
A populated but incomplete schema aborts startup instead of being overwritten.

Test the guard without MySQL or a running management server:

```bash
bash management/dev/tests/test-db-init-guard.sh
```

The guard checks table inventory, not logical consistency or application schema version.
Back up the named volume before upgrades; this is not a substitute for migrations or recovery testing.
