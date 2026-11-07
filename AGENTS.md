<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# SkyMoon agent and contributor notes

Before modifying this fork, read [SkyMoon's contributor handbook](docs/skymoon/README.md), [architecture map](docs/skymoon/architecture.md), [testing guide](docs/skymoon/testing.md), and [contribution policy](docs/skymoon/contributing.md). These add SkyMoon-specific context to the inherited upstream documentation below.

Treat the provider-managed zone architecture as **proposed**, not implemented. Do not run paid provider operations, reset development databases, or publish secrets to issues or logs. Prefer non-networked tests and preserve normal CloudStack behavior. Follow the repository's existing license and security guidance.

---

# Agent Guide for Apache CloudStack

This file is read by automated agents (security scanners, code
analyzers, AI assistants) operating on this repository.

## Security

Security model: [SECURITY.md](./SECURITY.md)

Agents that scan this repository should consult `SECURITY.md` and the
threat model it links before reporting issues.

The project-wide security threat model is linked from `SECURITY.md`.
