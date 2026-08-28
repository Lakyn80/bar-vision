# Universal Production Execution & Verification Protocol

> **Purpose:** Universal engineering execution protocol for production software projects.
>
> Use this document as a mandatory operating standard for coding agents, developers, and automated implementation workflows.
>
> This protocol is intentionally technology-agnostic. Project-specific architecture, infrastructure, providers, models, databases, deployment targets, and business rules belong in separate project documentation such as `PROJECT_RULES.md`, `ARCHITECTURE.md`, `AGENTS.md`, or equivalent.

---

## 1. Production Standard

Treat every repository using this protocol as a real production system, not a prototype, demo, throwaway script, or isolated coding exercise.

The solution must be designed for:

- long-term maintainability
- modularity
- scalability
- security
- testability
- observability
- reliability
- explicit architecture boundaries
- safe deployment
- future extension
- predictable failure behavior
- reproducible verification

Every implementation task must be handled as a controlled production change with explicit scope, validation, tests, runtime verification, security review, Git verification, and rollback awareness.

No task is complete merely because the code compiles or the happy path works.

---

# 2. Core Engineering Rules

Follow these rules for every implementation task.

1. Do not make quick hacks.
2. Do not solve the task only for the currently visible case.
3. Keep architecture explicit, modular, maintainable, and easy to reason about.
4. Preserve existing behavior unless the task explicitly requires changing it.
5. Do not add unrelated features.
6. Do not refactor unrelated code.
7. Validate inputs at trust boundaries.
8. Use explicit errors and safe failure modes.
9. Avoid hidden side effects.
10. Avoid hidden global state unless the project architecture explicitly requires it.
11. Keep code easy to extend later.
12. Prefer explicit, typed, readable code over clever shortcuts.
13. Preserve existing architectural boundaries.
14. Keep business logic out of infrastructure and transport layers.
15. Keep infrastructure concerns out of domain logic where practical.
16. Do not silently introduce fallback behavior that hides real failures.
17. Do not silently switch providers, services, databases, models, storage backends, queues, caches, APIs, or algorithms.
18. Do not weaken linting, typing, tests, security controls, import rules, or CI quality gates merely to make checks pass.
19. Do not hardcode secrets.
20. Do not expose secrets, credentials, private tokens, or sensitive payloads in logs.
21. Handle timeouts, retries, permissions, failure cases, and cleanup explicitly for network, database, filesystem, cache, queue, background job, subprocess, model, or external API operations.
22. Add or update tests whenever behavior changes.
23. Do not change anything outside requested scope unless technically necessary.
24. If an out-of-scope change is necessary, explain why.
25. Before finalizing, verify that the implementation matches the exact task.
26. Do not commit generated artifacts, local IDE files, caches, temporary logs, runtime state, local secrets, or unrelated files.
27. Never claim that something was tested, verified, deployed, migrated, or executed unless it actually was.
28. Never mark a task complete while a known relevant verification failure remains unresolved.
29. Prefer deterministic behavior where possible.
30. Fail explicitly rather than silently corrupting state.

The target is production-quality code suitable for a growing real-world system.

---

# 3. Mandatory Step-by-Step Control Process

Every implementation task must be split into explicit controlled steps.

For each significant step, report:

```text
Step:
Goal:
Files inspected:
Files changed:
Behavior changed:
Tests added/updated:
Verification command:
Result:
Risk:
Next step:
```

A step is not complete without verification.

If verification fails:

1. identify the cause,
2. fix it if within scope,
3. rerun the verification,
4. report the real result.

Do not hide failed checks.

---

# 4. Before Starting Any Task

Before changing code:

```text
1. Confirm the current project path.
2. Confirm the current Git branch.
3. Run git status --short.
4. Run git log -1 --oneline.
5. Identify uncommitted files.
6. Classify uncommitted files:
   - intended code
   - intended tests
   - intended documentation
   - generated artifacts
   - local noise
   - unknown / risky
7. Read the relevant project architecture documentation.
8. Read project-specific agent/developer rules.
9. Read the current project progress/status document if one exists.
10. Identify the last completed task.
11. Identify the exact new task.
12. Define allowed scope.
13. Define explicitly what must not be touched.
14. Identify relevant quality gates.
15. Identify runtime dependencies needed for verification.
```

Recommended project-specific files may include:

```text
ARCHITECTURE.md
docs/architecture.md
PROJECT_RULES.md
AGENTS.md
CLAUDE.md
PROJECT_PROGRESS.md
README.md
```

If the worktree is dirty, do not blindly continue.

Explain:

- what is dirty,
- whether it belongs to the current task,
- whether it is safe to preserve,
- whether it must remain untouched.

Never overwrite unknown user work.

---

# 5. Scope Control

Every task must define explicit scope.

Example:

```text
In scope:
- exact modules
- exact endpoints
- exact services
- exact scripts
- exact database changes
- exact tests
- exact documentation

Out of scope:
- unrelated refactors
- unrelated UI changes
- unrelated infrastructure changes
- unrelated provider changes
- unrelated database changes
- unrelated deployment changes
- unrelated performance work
- unrelated dependency upgrades
```

If implementation requires touching an out-of-scope file:

1. stop treating it as implicit,
2. explain why it is necessary,
3. keep the change minimal,
4. document it in the final report.

---

# 6. Architecture Control

Before implementation, identify where the change belongs.

The project-specific architecture is authoritative.

Typical responsibility boundaries may include:

```text
Transport / Router / Controller
    ↓
Application / Service layer
    ↓
Domain logic
    ↓
Repository / Persistence abstraction
    ↓
Database / Storage / External infrastructure
```

External systems should normally be isolated behind explicit interfaces, adapters, providers, gateways, or clients.

Examples of architecture violations:

```text
Business logic inside HTTP controllers
SQL queries inside presentation/UI code
Direct database access from unrelated modules
Infrastructure-specific behavior embedded in domain models
External API calls spread across business logic
Hidden cross-module imports
Circular dependencies
Cache treated as durable source of truth without explicit design
Repository methods performing application decisions
Controllers performing transactions directly
```

The implementation must preserve the dependency direction defined by the project.

If the project has static architecture checks such as import-linter, dependency-cruiser, ArchUnit, lint rules, or custom scripts, they must remain green.

---

# 7. Data and State Safety

For any persistent or shared state, identify the source of truth.

Explicitly classify relevant systems, for example:

```text
Primary database = durable source of truth
Object storage = durable binary storage
Cache = optimization / temporary state
Queue = delivery / execution mechanism
Search index = derived retrieval structure
Analytics store = reporting / derived metrics
External provider = remote system of record or integration
Filesystem = local runtime state only unless explicitly designed otherwise
```

Do not silently treat a cache, search index, queue, or local filesystem as the authoritative source of truth.

For data-changing tasks, consider:

- transaction boundaries
- idempotency
- duplicate requests
- retries
- partial failure
- rollback behavior
- migration compatibility
- concurrency
- stale writes
- deletion behavior
- auditability
- retention
- privacy requirements

---

# 8. Database Rules

When database work is involved:

1. Use explicit transaction boundaries.
2. Avoid hidden commits.
3. Ensure rollback behavior is defined.
4. Validate migrations against a clean database where applicable.
5. Do not rely on runtime schema auto-creation as a replacement for production migrations unless the project explicitly does so.
6. Test constraints and indexes where they affect correctness.
7. Avoid destructive migrations without explicit review.
8. Consider backward compatibility during rolling deployments.
9. Do not expose ORM/database entities directly through public APIs unless the architecture explicitly permits it.
10. Test failure paths, not only successful queries.

For every schema change report:

```text
Migration:
Forward migration verified:
Rollback/downgrade behavior:
Data migration required:
Backward compatibility:
Risk:
```

---

# 9. External Services and Provider Rules

For any external dependency such as:

```text
HTTP APIs
AI providers
payment providers
email providers
object storage
databases
message brokers
caches
search engines
authentication providers
cloud services
webhooks
third-party SDKs
```

handle explicitly:

- configuration
- authentication
- secrets
- timeouts
- retries
- rate limits
- error mapping
- circuit/failure behavior where relevant
- idempotency where relevant
- observability
- test doubles/stubs where practical
- version pinning where required
- provider-specific limits

Do not silently switch to another provider when the configured provider fails.

---

# 10. Input Validation and Trust Boundaries

Treat all external input as untrusted.

Validate as appropriate:

```text
HTTP request bodies
query parameters
headers
cookies
JWT claims
uploaded files
filenames
filesystem paths
URLs
webhooks
external API responses
queue messages
database data crossing module boundaries
CLI arguments
environment configuration
user-generated content
```

Where relevant verify:

- type
- size
- allowed format
- range
- enum values
- path safety
- MIME type
- content signature
- encoding
- authorization
- ownership

Avoid unsafe dynamic imports, arbitrary command execution, path traversal, injection, and implicit deserialization of untrusted data.

---

# 11. Test Requirements

Every behavior-changing task must include tests.

At minimum decide which of these are relevant:

```text
Unit tests
Integration tests
Endpoint/API tests
Repository/database tests
Service tests
Script/CLI tests
Smoke tests
Regression tests
Negative/error-path tests
Authorization tests
Authentication tests
Security tests
Cache tests
Queue/background-worker tests
Storage tests
Frontend tests
Contract tests
Migration tests
Concurrency/idempotency tests
Docker/runtime smoke
Performance tests
Load tests
```

For every relevant test group report:

```text
Command:
Result:
Number of tests passed:
Warnings:
Failures:
Warnings blocking: yes/no
```

If a relevant test is not run, explicitly state why.

Never claim a test result from inspection alone.

---

# 12. Negative and Error-Path Testing

Do not test only happy paths.

Evaluate relevant failures such as:

```text
invalid input
missing required input
unauthorized request
forbidden request
expired credentials
malformed credentials
database unavailable
cache unavailable
queue unavailable
storage unavailable
external API timeout
external API 4xx
external API 5xx
rate limit reached
duplicate request
invalid configuration
missing environment variable
corrupt file
unsupported file type
transaction failure
worker unavailable
migration failure
partial dependency outage
restart during operation
```

Critical failure paths must be deterministic and explicit.

---

# 13. Security Requirements

Every task must evaluate relevant security risks.

## Secrets

Confirm:

```text
No secrets hardcoded
No secrets committed
Local .env files ignored
Example env files contain placeholders only
Credentials come from approved configuration
Secrets are not printed in logs
Secrets are not exposed through API responses
```

## Authentication and Authorization

When relevant verify:

```text
Authentication is required where expected
Authorization is enforced server-side
Role/permission checks are tested
Expired credentials are rejected
Malformed credentials are rejected
Privilege escalation is prevented
Sensitive actions are audited
```

## Sensitive Data

Do not log or expose:

```text
passwords
password hashes
access tokens
refresh tokens
API keys
private keys
session secrets
authorization headers
payment secrets
raw private documents
sensitive personal data unless strictly necessary and approved
temporary signed URLs unnecessarily
```

## Dependency Security

Where supported, use the project's existing dependency/security scanning tools.

Do not introduce unnecessary dependencies.

---

# 14. Privacy Rules

When personal, customer, employee, financial, legal, health, biometric, or otherwise sensitive data is involved:

- minimize collection
- minimize logging
- define retention
- define deletion
- restrict access
- avoid unnecessary replication
- protect storage
- protect transport
- avoid exposing raw data in metrics
- consider audit requirements
- preserve tenant/user isolation

Project-specific privacy requirements override generic defaults.

---

# 15. Observability and Logging

Runtime-facing changes must include enough observability to diagnose failures safely.

Useful fields may include:

```text
trace_id
request_id
route
operation
service
module
status
duration_ms
dependency name
retry count
cache hit/miss
queue task id
job id
safe entity identifiers
error category
```

Avoid logging:

```text
raw secrets
full authorization headers
passwords
tokens
private keys
full sensitive payloads
large document bodies
private customer content
unnecessary personal data
```

Prefer structured logging where the project supports it.

Every externally reachable request or significant background operation should be traceable through a request/trace/job identifier where practical.

---

# 16. Error Handling

Errors must be:

- explicit
- safe
- actionable
- typed or categorized where appropriate
- mapped correctly at system boundaries

Client-facing errors must not expose:

```text
internal stack traces
database credentials
filesystem paths
private infrastructure details
secret configuration
internal implementation details that increase attack surface
```

Technical detail belongs in logs, not public responses.

Do not hide operational failures behind fake successful responses.

---

# 17. Concurrency, Idempotency, and Retries

For operations that may run more than once or concurrently, evaluate:

```text
Can this request be retried safely?
Can duplicate messages occur?
Can two workers process the same job?
Can two requests update the same entity?
Is a distributed lock required?
Is an idempotency key required?
Can retries duplicate side effects?
What happens after partial success?
```

Retries must not blindly duplicate:

- payments
- emails
- external mutations
- resource creation
- database inserts
- irreversible operations

---

# 18. Background Jobs and Queues

For worker/task systems verify:

- task serialization
- retry strategy
- timeout
- idempotency
- duplicate delivery behavior
- dead-letter/failure behavior where supported
- observability
- task result handling
- worker restart behavior
- broker outage behavior
- dependency outage behavior

A task is not verified merely because it can be imported.

Where runtime verification is required, execute it through a real worker or equivalent execution environment.

---

# 19. Cache Rules

If cache behavior is involved:

1. State what is cached.
2. State whether the cache is optional or required.
3. State the cache key semantics.
4. Define TTL/invalidation.
5. Define stale data behavior.
6. Define behavior when cache is unavailable.
7. Do not treat cache as source of truth unless explicitly designed.
8. Test hit, miss, expiry, and failure behavior where relevant.

Cache failures must not silently change business correctness.

---

# 20. Filesystem and Upload Safety

For file operations verify:

```text
safe filenames
path traversal protection
file size limits
MIME validation
magic byte/content validation where required
storage permissions
temporary file cleanup
duplicate handling
hashing if required
private/public access policy
retention/deletion behavior
```

Never trust the uploaded filename alone.

---

# 21. Docker and Runtime Verification

For backend/runtime/infrastructure tasks, runtime smoke verification is required unless technically impossible.

Typical checks:

```text
docker compose ps
relevant service logs
direct API smoke
database connectivity
cache connectivity
queue connectivity
storage connectivity
worker execution
application restart
health endpoint
readiness endpoint
```

Check for:

```text
restart loops
permission errors
connection failures
migration failures
stack traces
unexpected downloads
unexpected external calls
missing environment variables
resource exhaustion
port conflicts
```

If Docker is not used by the project, perform the equivalent runtime verification for the project's actual environment.

---

# 22. Port and Runtime Dependency Audit

Before starting or changing local infrastructure:

1. inspect currently used ports,
2. inspect running containers/processes,
3. inspect existing service mappings,
4. do not assume default ports are free,
5. do not kill unrelated services,
6. choose safe alternative host ports where needed,
7. document the actual mapping used.

Example:

```text
Host PostgreSQL 5433 -> Container PostgreSQL 5432
Host API 8010 -> Container API 8000
```

Internal service ports should normally remain standard unless the architecture requires otherwise.

---

# 23. Configuration Management

Configuration must be explicit.

Separate when applicable:

```text
build-time configuration
runtime environment configuration
secret configuration
database-backed runtime settings
feature flags
provider configuration
deployment configuration
```

Do not mix unrelated configuration layers.

Validate required configuration at startup or the appropriate boundary.

Invalid critical configuration should fail clearly.

---

# 24. Documentation Requirements

Every completed implementation task should update the project's progress or change tracking document when the repository uses one.

Recommended:

```text
PROJECT_PROGRESS.md
```

Each entry should include:

```text
Task number/name
Date/time
Goal
What changed
Why it changed
Files changed
Tests run
Runtime smoke
Known limitations
Next recommended task
```

Documentation must reflect reality.

If documentation claims that a script, endpoint, migration, test, or feature exists, the corresponding implementation must exist and be committed.

Do not document incomplete work as completed.

---

# 25. Git Rules

Before staging:

```bash
git status --short
git diff --stat
```

Inspect the actual diff.

Stage only intended files.

Never stage or commit unless explicitly intended:

```text
.env
IDE metadata
local caches
temporary logs
runtime databases
Docker volumes
build outputs
test caches
model caches
temporary artifacts
generated secrets
local scratch files
downloaded private data
```

Before commit:

```bash
git status --short
```

Commit message must describe the real change.

Push only after all required checks and runtime smoke pass.

After commit:

```bash
git log -1 --oneline
git status --short
```

Final report must include:

```text
branch
commit hash
push result
files changed
tests run
smoke result
remaining uncommitted files
known limitations
next recommended task
```

---

# 26. CI Rules

CI is a verification system, not a substitute for local reasoning.

CI should include relevant automated quality gates such as:

```text
lint
format validation
type checking
architecture/import checks
unit tests
integration tests
security checks
dependency checks
build verification
migration verification
```

Do not weaken CI just to obtain a green result.

A green CI result does not override a known runtime or architectural failure.

---

# 27. CI/CD Separation

CI and CD should be treated as separate concerns.

Recommended principle:

```text
Push / Pull Request
    ↓
CI verification
    ↓
STOP
```

Deployment should require an explicitly defined deployment trigger according to project policy.

For projects that require manual deployment:

```yaml
on:
  workflow_dispatch:
```

A normal code push must not implicitly deploy to production unless the project explicitly defines and authorizes that behavior.

Before any deployment, verify:

- correct environment
- correct revision
- migrations
- secrets/configuration
- health checks
- rollback path
- deployment authorization

Never deploy merely because implementation work is finished.

---

# 28. Deployment Verification

When deployment is explicitly in scope:

Before deployment:

```text
Confirm target environment
Confirm branch/revision
Confirm artifact/image version
Confirm configuration
Confirm migration plan
Confirm rollback plan
Confirm health checks
Confirm authorization to deploy
```

After deployment:

```text
Verify service health
Verify readiness
Verify logs
Verify critical API smoke
Verify database state
Verify background workers
Verify monitoring
Verify error rate
Verify rollback remains possible
```

Do not claim deployment success from a command exit code alone.

---

# 29. Rollback Awareness

Every production-impacting change must consider rollback.

Evaluate:

```text
Can code be rolled back independently?
Can schema be rolled back?
Is the migration backward compatible?
Will old code work with new schema?
Will new code work before migration completes?
Are background jobs compatible during rollout?
Can external side effects be reversed?
```

If rollback is unsafe, state this explicitly before deployment.

---

# 30. Performance and Scalability Review

For changes that may affect load or throughput, evaluate:

```text
database query count
N+1 queries
connection pool behavior
cache behavior
queue throughput
worker concurrency
memory usage
CPU usage
external API rate limits
large payload handling
pagination
batching
indexes
locking
horizontal scaling
```

Do not prematurely optimize unrelated code, but do not introduce obvious scalability bottlenecks.

---

# 31. Dependency Management

When dependencies change:

1. justify the dependency,
2. prefer maintained libraries,
3. pin/version according to project policy,
4. update lockfiles,
5. run relevant tests,
6. inspect license/security implications if required,
7. avoid adding a package for trivial functionality,
8. do not perform unrelated bulk upgrades.

Report added/removed dependencies in the final report.

---

# 32. API Compatibility

For public or internal APIs with consumers:

- avoid accidental breaking changes,
- preserve response contracts unless intentionally changed,
- version APIs according to project policy,
- validate serialization,
- test error responses,
- consider old clients,
- update API documentation where necessary.

If a breaking change is required, state it explicitly.

---

# 33. Frontend Changes

When frontend work is involved, evaluate:

```text
type safety
API contract compatibility
loading states
error states
empty states
authorization behavior
accessibility
responsive behavior
state synchronization
security-sensitive rendering
frontend build
frontend tests
runtime smoke
```

Do not expose secrets or trust client-side authorization alone.

---

# 34. Senior Enterprise Review Checklist

Before finalizing any task, perform the relevant parts of this review.

## Architecture

```text
Does the change belong in the correct module?
Are responsibility boundaries clean?
Is dependency direction correct?
Is there hidden coupling?
Are abstractions justified?
Will the design remain understandable as the system grows?
```

## Scalability

```text
Does it work with multiple application instances?
Does it work with multiple workers?
Are local filesystem assumptions avoided where inappropriate?
Are connection pools and concurrency controlled?
Are rate limits respected?
Are expensive operations bounded?
```

## Reliability

```text
What happens if the database is down?
What happens if the cache is down?
What happens if the queue is down?
What happens if object storage is down?
What happens if an external API is down?
What happens after restart?
What happens on cold start?
What happens on partial failure?
```

Only evaluate dependencies actually used by the project.

## Security and Privacy

```text
Are secrets protected?
Are permissions enforced?
Are inputs validated?
Are logs safe?
Is sensitive data minimized?
Can users access another user's/tenant's data?
Are destructive actions protected?
```

## Testability

```text
Can core logic be unit tested?
Can external services be mocked/stubbed?
Can failure paths be reproduced?
Are regressions covered?
Are tests deterministic?
```

## Observability

```text
Can a failed request be traced?
Can a failed background job be traced?
Can dependency failures be identified?
Can latency be measured?
Can cache/queue/database behavior be diagnosed safely?
```

## Maintainability

```text
Is the code explicit and typed?
Are names clear?
Are functions/classes focused?
Is duplicated logic avoided?
Is configuration explicit?
Is there hidden state?
Is there a clear next step?
```

---

# 35. Definition of Done for Every Task

A task is complete only when all relevant items are true:

```text
Scope was respected.
Architecture is clean.
Behavior is implemented.
Behavior is tested.
Important error paths are tested.
Required static checks pass.
Runtime smoke passed where applicable.
Security review passed.
Privacy requirements were respected.
Logs are safe and useful.
No unrelated files were changed.
No generated/local artifacts were committed.
Documentation/progress state is accurate.
Git state is understood.
Required commit was created.
Required push succeeded.
CI is green where applicable.
Deployment status is explicitly known.
Known limitations are documented.
Final report is complete.
```

If any relevant item is not true, the final report must say what is incomplete and why.

---

# 36. Mandatory Final Report Format

Every implementation task must end with a report containing at least:

```text
Task:
Phase/Milestone:

Project path:
Branch:
Commit:
Push:
CI:

Summary:

Scope:
- In scope completed:
- Out-of-scope changes:

Files changed:
- path -> reason

Behavior changed:

Behavior preserved:

Architecture:
- boundaries preserved:
- deviations:

Dependencies:
- added:
- removed:
- updated:

Database:
- schema changed:
- migration:
- migration verified:
- rollback/backward compatibility:

Tests:
- command -> result
- passed:
- failed:
- warnings:
- warnings blocking:

Static checks:
- lint:
- formatting:
- typing:
- architecture/import checks:
- security checks:

Smoke/runtime:
- action -> result

Runtime dependencies:
- database:
- cache:
- queue:
- object storage:
- external APIs:
- other:

Security/privacy:
- secrets exposed: yes/no
- sensitive values logged: yes/no
- authorization tested: yes/no/not applicable
- input validation tested: yes/no/not applicable

Failure modes verified:
- dependency unavailable:
- invalid input:
- invalid credentials:
- partial failure:
- restart/cold start:
- other:

Observability:
- trace/request/job correlation:
- safe logging:
- relevant metrics/logs:

Git:
- remaining uncommitted files:
- generated files accidentally committed:

Deployment:
- deployment in scope: yes/no
- deployment executed: yes/no
- environment:
- rollback verified/planned:

Known limitations:

Definition of Done:
PASS / FAIL

Next recommended task:
```

Fields that do not apply should be marked:

```text
not applicable
```

Do not silently omit an important failed check.

---

# 37. Project-Specific Overlay

This protocol is deliberately universal.

Every real project should define a separate project-specific rules document, for example:

```text
PROJECT_RULES.md
```

That document should specify:

```text
project architecture
technology stack
module boundaries
source-of-truth systems
database rules
cache rules
queue rules
external providers
security invariants
privacy requirements
deployment policy
CI/CD policy
required quality gates
project-specific tests
business invariants
forbidden operations
```

Recommended rule for coding agents:

```text
Before every implementation task, read and follow:

1. UNIVERSAL_EXECUTION_PROTOCOL.md
2. PROJECT_RULES.md
3. architecture documentation
4. current project progress/status
```

The project-specific rules may strengthen this protocol.

They must not silently weaken production safety requirements.

---

# 38. Conflict Resolution Order

If instructions conflict, use this order unless the repository defines a stricter policy:

```text
1. Explicit current user/task instruction
2. Security and legal constraints
3. Project-specific rules/invariants
4. Project architecture documentation
5. This Universal Execution Protocol
6. Existing implementation conventions
```

Never resolve ambiguity by silently introducing behavior-changing assumptions.

---

# 39. Final Principle

The objective is not merely to produce working code.

The objective is to produce a controlled, auditable, testable, secure, maintainable production change whose behavior is understood before it is committed, pushed, or deployed.
