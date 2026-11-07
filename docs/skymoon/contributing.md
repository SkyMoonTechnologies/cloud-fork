# Contributing to SkyMoon Cloud

These instructions complement, rather than replace, the inherited Apache [CONTRIBUTING.md](../../CONTRIBUTING.md), [LICENSE](../../LICENSE), [NOTICE](../../NOTICE), and [security guidance](../../SECURITY.md).

## Work on a ticket

1. Select an open issue in [SkyMoon's backlog](https://github.com/SkyMoonTechnologies/cloud/issues/2). Read its dependencies and linked epic.
2. Record your understanding of the current behavior and the observed gap. Issue paths are starting points, not necessarily all files that need edits.
3. Create a feature branch from the latest `main`:
   ```bash
   git fetch origin
   git switch main
   git pull --ff-only origin main
   git switch -c feature/SKY-001-external-vm-trace
   ```
   Substitute your issue number and short slug. Do not push directly to `main`.
4. For behavioral changes, add failing tests/fixtures first where practical. Keep new provider behavior gated behind a capability or explicit configuration, with legacy CloudStack behavior intact.
5. Execute tests described in [testing.md](testing.md), document exactly what ran and what could not be run.
6. Open a PR against `SkyMoonTechnologies/cloud:main`; include `Refs #N`, or `Fixes #N` **only if the issue is actually complete**. Seek review before merge.

## Pull request checklist

- [ ] Issue link, rationale, and summary of changed behavior.
- [ ] Explains impact on KVM/Core/Edge, external hypervisor and other providers.
- [ ] Lists changed API/database schema and any migration/rollback plan.
- [ ] Includes positive tests, negative tests, and exact commands/results.
- [ ] Describes timeouts, retries, idempotency, resource cleanup and audit logging where applicable.
- [ ] No provider tokens, private keys, userdata, customer data, or untracked credential files.
- [ ] No unexpected provider charges; live actions explicitly identified and cleaned up.
- [ ] UI screenshots or API response examples if visible behavior changed.
- [ ] Docs and capability matrix updated if APIs or supported operations changed.

## Design principles

- **Preserve default behavior.** Provider-managed mode must be opt-in; do not make standard KVM zones depend on an external API.
- **Use existing abstractions first.** The External planner/template adapter and NetworkOrchestrator exist. Investigate them before adding another framework.
- **Be honest about unsupported features.** If provider snapshots or CloudStack-owned public IP allocation are not supported, reject/hide them.
- **Make operations replay-safe.** A timeout after VM creation must never blindly create a second billable VM.
- **Keep identifiers scoped.** Track SkyMoon resource ID, provider account, region, provider ID and lifecycle checkpoint.
- **Separate environments.** Never use production provider credentials in local dev or CI.
- **Keep source provenance.** Apache CloudStack licensing/attribution still applies to inherited files; new SkyMoon documentation must not falsely claim upstream endorsement.

## Research-only tickets

Spikes, including [SKY-001](https://github.com/SkyMoonTechnologies/cloud/issues/3), close when their documented evidence and acceptance criteria exist. Do not require a code change to close a research ticket.

A substantive new architecture decision belongs in an ADR with **Proposed** status first, the alternatives and risks, and explicit review before marking **Accepted**.

## Definition of done

A ticket is complete only when its stated acceptance criteria have verifiable evidence, tests are executed or justified as not applicable, docs are updated, and its PR is merged. Publishing an unmerged documentation PR does not itself mean the ticket is done.

If an issue uncovers unknown foundational behavior, update that issue and dependencies first instead of silently expanding implementation scope.
