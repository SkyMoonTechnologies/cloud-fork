# SkyMoon offline External VM provider

This **mock VM provider** emulates CloudStack External hypervisor actions using only Python's standard library and a local JSON state directory. No provider account, network access, token or paid resource is needed.

Supported actions: `prepare`, `create`, `start`, `stop`, `reboot`, `delete`, `status`, `statuses`. Return shapes follow `ExternalPathPayloadProvisioner`: `prepare` returns a VM details patch, `status` returns `power_state`, `statuses` returns a map of internal VM names to `PowerOn`/`PowerOff`, and successful actions return JSON with `status:success`. The adapter is intentionally an **action-level emulator**, not an implementation of CloudStack zones, networking, or storage.

## Offline tests

```bash
python3 -m unittest discover -s extensions/MockProvider/tests -v
python3 -m py_compile extensions/MockProvider/mock_provider.py
```

Run the executable directly with an isolated JSON payload and directory:

```bash
export SKYMOON_MOCK_PROVIDER_STATE_DIR="$(mktemp -d)"
printf '%s\n' '{"virtualmachineid":"cafebabe-0101-0202-0303-d4d4d4d4d4d4","virtualmachinename":"i-2-VM"}' >/tmp/skymoon-mock.json
python3 extensions/MockProvider/mock_provider.py prepare /tmp/skymoon-mock.json 10
python3 extensions/MockProvider/mock_provider.py create /tmp/skymoon-mock.json 10
python3 extensions/MockProvider/mock_provider.py statuses /tmp/skymoon-mock.json 10
python3 extensions/MockProvider/mock_provider.py delete /tmp/skymoon-mock.json 10
```

The state directory is protected with a process-level file lock; updates are atomic. It should never be shared by customer tenants or used as production storage. The default is `/tmp/skymoon-mock-provider`, or set `SKYMOON_MOCK_PROVIDER_STATE_DIR`. VM identities must be UUIDs; state files aren't interpreted as trusted customer input.

To register as a CloudStack External extension, use the executable path `extensions/MockProvider/mock_provider.py` with an executable mode. The file mode is tracked in Git.

**Known limitation:** Current SkyMoon's full no-hardware zone → cluster → network → storage → VM integration still requires implementation. These tests validate only the extension's action protocol. They do not close [SKY-034](https://github.com/SkyMoonTechnologies/cloud/issues/36) or [SKY-004](https://github.com/SkyMoonTechnologies/cloud/issues/6) until actual management API integration is exercised.
