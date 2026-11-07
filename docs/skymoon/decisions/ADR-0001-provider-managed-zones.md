# ADR-0001: Provider-managed VM zones and capabilities

**Status:** Proposed. **Decision owner:** SkyMoon maintainers. **Date:** 2026-11-06. **Do not treat this as an accepted or implemented design.**

## Context

SkyMoon begins with third-party VM infrastructure and intends to expand into owned regions. The existing CloudStack codebase has an External VM hypervisor implementation and a separate NetworkOrchestrator extension framework, but its Core zone wizard and backend still have conventional network, pod, host, storage and system-VM assumptions.

During the DigitalOcean pilot, a conventional Advanced Core zone wizard requested CloudStack-owned public IP ranges. DigitalOcean's VPC and Droplet-assigned public addresses cannot be represented honestly by entering fabricated network pools. A provider-owned VM may also have no local CloudStack primary storage pool.

## Proposed decision

Add an explicit, opt-in **ProviderManaged** capability/mode to selected Core zones or associated infrastructure configuration, with provider-owned networking and root-disk integration, while retaining logical zone/pod/cluster/host inventory for existing scheduling and authorization. Reuse the existing VM Orchestrator and NetworkOrchestrator extension hooks where they actually support the required lifecycle. A provider adapter implements capability-specific operations; all unsupported features remain unavailable.

Do not equate `External` hypervisor with provider-managed networking: other external hypervisors may still rely on conventional CloudStack network/storage services.

## Alternatives

1. **Use conventional KVM-backed Core zone only:** fewer core changes, but requires running infrastructure solely to satisfy system-VM and networking assumptions, which does not meet the provider-only target.
2. **Use Edge zone as-is:** current Edge semantics and supported hypervisors have different requirements; do not silently overload them without proof.
3. **Replace CloudStack with a new control plane:** broader scope and rewrite risk; deferred.
4. **Use invented IP pools/storage hosts:** rejected, because misleading records can route incorrectly, leak addresses, and break reconciliation.

## Guardrails

- Feature flag/mode is explicit and defaults **off** for existing zones.
- SkyMoon's VM ID is stable; provider ID must be persistently mapped with provider account/region.
- Provider calls must be replay-safe. Ambiguous create and delete results require reconciliation.
- Keep provider API secrets separate by environment, never commit them.
- Never bill or claim supported features until the actual provider resource and its state are validated.
- Never automatically delete imported/preexisting provider VPCs or unknown VMs.
- Normal Core/KVM, storage and network operation must pass regressions.

## Open questions before acceptance

- Which exact API/storage schema should hold mode, provider details and identifiers?
- Can a Core zone/pod/host be created without traditional system networks/VMs *without* breaking CloudStack services?
- Where do actual IPs/NICs and provider-owned root disks enter CloudStack inventory correctly?
- Can the current network extension cover provider VPC and firewall semantics without pretending to support virtual-router services?
- Which operations are synchronous vs asynchronous, and what responses does the Java provisioner accept?
- Which metering and cost protections are required before allowing paying users?
- How does the solution upgrade/rollback alongside upstream CloudStack changes?

## Validation plan

1. SKY-001: produce a runtime-verified call graph.
2. SKY-002: define provider-neutral contract and capability matrix.
3. SKY-005 through SKY-009 and SKY-012: prove provider-managed zone/pod/cluster and extension binding.
4. SKY-010 through SKY-019: prove one no-hardware VM end to end.
5. SKY-023, SKY-024 and SKY-028: confirm tenant/security/cost/regression gates.

**Acceptance requires maintainers' review with trace evidence**. Update status only after the proposed mode is validated; do not infer acceptance from this ADR being present in `main`.
