# DigitalOcean External VM adapter (experimental)

This is an **actual CloudStack External VM action executable**, not a complete provider-managed zone integration. It is invoked by `ExternalPathPayloadProvisioner` with:

```text
digitalocean.py <action> <JSON-payload-file> <timeout-seconds>
```

Supported actions: `prepare`, `create`, `start`, `stop`, `reboot`, `status`, `statuses`, `delete`. Console, provider-managed IPs/NICs, block volumes, snapshots, networking, and customer billing are not implemented here. The Java orchestrator still has conventional zone, storage and network dependencies tracked under [SKY-EPIC-001](https://github.com/SkyMoonTechnologies/cloud/issues/2).

## Configuration

For the development pilot only, set these environment variables **on the management container**, never in Git:

| Variable | Purpose |
| --- | --- |
| `SKYMOON_DEV_DO_TOKEN` | DigitalOcean API bearer token |
| `SKYMOON_DO_REGION` | Target region, e.g. `sfo3` |
| `SKYMOON_DO_SIZE` | Target provider SKU, e.g. `s-1vcpu-1gb` |
| `SKYMOON_DO_IMAGE` | Provider image, e.g. `ubuntu-24-04-x64` |
| `SKYMOON_DO_VPC_UUID` | Existing DigitalOcean VPC UUID |
| `SKYMOON_DO_STATE_DIR` | Persistent intent directory, defaults to `/var/lib/skymoon-providers/digitalocean` |

Extension/host-scoped `externaldetails` may specify `region`, `size`, `image`, `vpc_uuid` and `ssh_keys`; these override the corresponding environment values. **Do not expose these fields to customers before the backend access model and capability checks are implemented.** The management Compose stack binds the code read-only and mounts a named volume for the intent journal. The adapter must be executable: `chmod +x extensions/DigitalOcean/digitalocean.py` if installed from a plain ZIP/copy, or use its executable Git mode.

Required API token scopes include `droplet:read`, `droplet:create`, `droplet:update`, `droplet:delete`, `tag:read`, `tag:create`, plus DigitalOcean's dependent read scopes. Use a tightly scoped **development** token. Do not use the existing pilot token without explicitly verifying the scopes.

## Idempotency and limitations

- VM ownership is tracked using a per-CloudStack-UUID tag `skymoon-vm-<uuid>` and a shared `skymoon-managed` tag.
- Creation checks for an existing matching tag before POST. A separate durable **create-attempt marker** is written before POST. An unknown API outcome will block an automatic second creation until a human reconciles it.
- **Never manually delete the marker to make a retry work.** First inspect DigitalOcean for a late-arriving Droplet, reconcile inventory and verify tenant/region/account.
- Existing VMs are only mutated if both expected SkyMoon tags match. A missing VM is safe for `delete` and `stop`, but the create marker remains to prevent an unsafe subsequent recreation.
- A successful HTTP 202 indicates **accepted**, not completed provisioning. Full status reconciliation, durable DB provider-ID mapping and customer IP propagation remain separate tickets.
- A lost API response after deletion may require reconciliation. The adapter deliberately does not issue automatic retries for ambiguous mutations.
- A VM whose CloudStack internal name is not a valid DNS name is rejected, rather than silently changing its name and breaking the host status map.
- A VM created by a previous pilot adapter using different tags **will not** be adopted automatically.

## Offline tests (no API token, no paid resources)

```bash
python3 -m unittest discover -s extensions/DigitalOcean/tests -v
python3 -m py_compile extensions/DigitalOcean/digitalocean.py
```

The 14 tests cover create preflight fields, duplicate detection, uncertain create and delete outcomes, state checkpoints, status mapping, tenant tag refusal, and power operations. No test calls DigitalOcean.

## Deployment

`compose.dev.yml` mounts `./extensions/DigitalOcean` read-only to the management image and `skymoon-dev-provider-state` to `/var/lib/skymoon-providers`. Register the extension entry point through CloudStack's Extensions administration and verify it is **Ready** before attempting any live lifecycle operation. This does not automatically register a working zone, network extension, template or offering.

**Do not attempt a paid end-to-end VM test yet.** First complete [SKY-001](https://github.com/SkyMoonTechnologies/cloud/issues/3), [SKY-005](https://github.com/SkyMoonTechnologies/cloud/issues/7), and the provider-managed network/storage dependencies, then explicitly approve a small test VM with a cleanup plan.
