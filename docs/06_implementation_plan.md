# 06. Implementation Plan

## 6.1 Build order (what must exist before submission, what can wait)

**Tier 0 — must exist, no LLM needed (the TCB core and Layer-A experiments depend on it):**
1. **Capability Store** with atomic two-phase consumption (`reserve`/`commit`/`consume`/`release`), nonce, TTL, revocation, idempotency (§03.5). Property-tested under concurrency.
2. **Reference Monitor** `verify()` implementing §3.13 deterministically. Kept small; LoC reported as TCB size.
3. **Canonicalizer** with per-role modules and a `total: bool` declaration (§6.4).
4. **Tool Contract Registry** + adapters for the 5 MVP tools, with coverage `κ` instrumentation (§6.2–6.3).
5. **Receipt Store** + signing/verification.
6. **Capability Minting Service** + minting key.

**Tier 1 — must exist, exercises the mechanism:**
7. **Provenance Runtime** in *both* oracle and automatic modes (§3.6).
8. **Memory Authority Stripper** (§3.9).
9. **Controlled Endorsement Manager** with canonical-action challenges (§3.11).
10. **AuthSpec Builder** (LLM) with `binding_status` discipline + high-impact confirmation (§3.3).

**Tier 2 — needed for the multi-agent claim, can be staged:**
11. **Delegation Manager** + agent PKI (§3.10, §6.5).
12. **Proof Synthesizer** as a separate module (initially the agent emits the witness; a standalone synthesizer is an optimization). The `ProofObjectRemoved` ablation (§09) decides how much to invest here.

**Tier 3 — adopted component:**
13. **Data-flow / readers capability** layer (CaMeL-style) for the exfiltration dimension (G4). Integrate CaMeL's open implementation rather than reimplement.

## 6.2 MVP tool contracts (every authority-bearing field declared)

The contract is the trusted declaration the monitor checks against. Missing fields are the #1 bypass; we enumerate them and instrument coverage.

```text
read_file:
  args:        path:file_path[read]
  side_effects: reads(path)
  authority:   {file_path(read)}
  coverage_fields: {path}

summarize:
  args:        input:data
  side_effects: none (pure)
  authority:   {}                 # transform; governed by DERIVE-CONTENT + receipts
  coverage_fields: {input}

send_email:
  args:        to:recipient, cc:recipient[], bcc:recipient[], reply_to:recipient,
               subject:data, body:data, headers:map, attachments:file_path[read][]
  side_effects: egress(to ∪ cc ∪ bcc), reads(attachments)
  authority:   {recipient(to,cc,bcc,reply_to), file_path(attachments,read), data(body,subject)}
  coverage_fields: {to, cc, bcc, reply_to, headers, attachments}   # bcc/headers are classic gaps

write_file:
  args:        path:file_path[write], content:data, mode:control,
               overwrite:bool, symlink_policy:control   # follow/deny/resolve-and-check
  side_effects: writes(path)
  authority:   {file_path(write, post-symlink-resolution)}
  coverage_fields: {path, mode, overwrite, symlink_policy}   # overwrite & symlink are authority-bearing (clobber / escape-scope)

memory_write:
  # memory is data, never authority; this contract makes that explicit and observable
  args:        content:data, authority_claims:control, provenance:control,
               persistence_flag:control       # persistent authority requires explicit endorsement (§03.9), default OFF
  side_effects: persists(content) with stored trust-root label
  authority:   {}    # writing memory mints NO authority; MEMORY-STRIP demotes any authority_claims to inert content
  coverage_fields: {content, authority_claims, provenance, persistence_flag}   # authority_claims/persistence_flag are the laundering vectors (KE-3); must be surfaced so they can be stripped
  note:        on read, stored value resolves to its recorded untrusted root unless an explicit persistent endorsement exists (§03.9); persistence_flag=true without endorsement is denied

delegate:
  # cross-agent authority transfer; attenuation-only, certificate-bound (§03.10)
  args:        parent_agent:control, child_agent:control, delegated_scope:control,
               TTL:control, redelegation:bool
  side_effects: issues a signed DelegationCert
  authority:   {delegation(child ⊆ parent, TTL(child) ≤ TTL(parent), redelegation only if explicitly preserved)}
  coverage_fields: {parent_agent, child_agent, delegated_scope, TTL, redelegation}   # each is authority-bearing; a missing field = silent over-delegation

run_shell:
  # NOT arbitrary strings — allowlisted command templates only (`CANONICALIZATION_BYPASS_GATE.md`)
  accepts:     CommandTemplate { template, arg_types, allowed_env, allowed_cwd, stdin_policy }
  authority:   {command(template-membership), file_path(cwd∈allowed_cwd), env⊆allowed_env, stdin per policy}
  coverage_fields: {command, cwd, env, stdin}     # all four are authority-bearing; see `CANONICALIZATION_BYPASS_GATE.md`
```

If an HTTP tool appears (it does in MCP-metadata tasks), its contract must cover `url:external_endpoint, method:control, headers:map, follow_redirects:bool, body:data` — `follow_redirects` is an endpoint-laundering vector (redirect to an unauthorized host); see KE-10 and `CANONICALIZATION_BYPASS_GATE.md`.

## 6.3 Measuring adapter coverage on real tools (residual sets, not a probability)

A first-class experiment (full protocol in `TCB_AND_ADAPTER_COVERAGE.md`, results in §08), not an afterthought:
1. Assemble a corpus of real MCP servers / common tool wrappers.
2. For each, estimate `F(t)` (true authority-bearing fields) by (a) reading docs/JSON schema, (b) adapter fuzzing that perturbs candidate fields and observes side effects.
3. Report **`Residual(t) = F(t)\O(t)` as a set per tool**, plus aggregate frequency of each residual field. We *expect* common gaps (bcc, headers, env, redirect-following) and will show them. This grounds **Characterization 1′** (§05.6) in reality — exposure equals the unobserved fields — and is a defensible standalone contribution ("real agent tool adapters systematically under-declare these authority-bearing fields"). We report sets, **not** a coverage probability (the discarded `Σ(1−κ)` bound, see `TCB_AND_ADAPTER_COVERAGE.md`).

## 6.4 Canonicalizer (per-role, with honest decidability)

| Role | Canonical form | `total`? | Residual risk |
|---|---|---|---|
| `recipient` | lowercased, IDN→ASCII, confusable-folded, plus-addressing normalized | **yes** | provider-specific aliasing (documented) |
| `file_path` | realpath after symlink/`..` resolution, scoped to allowed subtree | **partial** | **TOCTTOU**: path resolved at verify can change before execute → resolve-and-open atomically in the adapter; report residual |
| `external_endpoint` | punycode→unicode, lowercased host, resolved redirect target, port-explicit | **partial** | DNS rebinding / redirect-after-check → re-resolve at egress in adapter |
| `command` | best-effort tokenization | **NO (undecidable in general)** | semantic-equivalence (eval, base64, `$IFS`, var splicing) cannot be canonicalized |

**Consequence for `run_shell` (stated, not hidden):** because `command` has no total canonical form, CapProof does **not** claim soundness for arbitrary shell. `run_shell` accepts only **allowlisted command templates** — a fixed program+flags with typed, shell-metachar-free holes, an explicit `allowed_env`/`allowed_cwd`/`stdin_policy` contract (full schema in `CANONICALIZATION_BYPASS_GATE.md`). A capability's predicate is "matches an admin-approved template with valid holes and an in-contract environment"; anything else (raw command, extra env var, metacharacter in a hole, out-of-scope cwd) is denied. This converts undecidable canonicalization into decidable membership + typed-hole validation, at the cost of generality — stated plainly, and tested by the template-argument-injection and env/cwd/stdin attacks (§09 #16–17, `CANONICALIZATION_BYPASS_GATE.md`). More credible than pretending `CanonicalizationMismatch` solves shell.

## 6.5 Key management and agent identity (was missing entirely)

- **Minting key** signs/MACs capabilities. Held by the Minting Service; never exposed to the agent. Rotated per deployment; capabilities carry a key-id.
- **Receipt-signing key** signs receipts; verified by the monitor.
- **Agent identity keys** back `subject_agent` binding and delegation-cert signatures: each agent has a keypair; the Delegation Manager verifies cert signatures and the monitor verifies `subject_agent` against the presenting agent's authenticated identity. Without this, `AgentMismatch` is unenforceable — so the agent PKI is a prerequisite for Theorem 3, and we say so.
- Threat: key compromise = total break (in the TCB; §02.3). We do not claim defense against key compromise.

## 6.6 Two-phase execution and anti-replay (implementation notes)

- `reserve` = atomic CAS on `status`, storing `(action_hash, nonce, lease_expiry)`.
- Executor must present the `nonce` and a signed outcome to `commit`; a stale/duplicate `nonce` is idempotently ignored.
- Lease expiry auto-`release`s reservations to avoid capability lockup on crashes.
- Proof `action_hash` must equal `H(canonical_action)` and the reserved `action_hash`, binding the witness, the reservation, and the executed action together (defeats replay/scope-confusion).

## 6.7 Sandboxing and safety of the harness

- `run_shell` executes in a network-isolated container with a read-only FS except a scratch mount; commands restricted to the allowlist.
- All "external endpoints" in experiments are **mock** servers; no real egress.
- Email is mocked; "sends" are recorded, not delivered.
- This keeps the adaptive-attack experiments safe and reproducible (§08, §11).

## 6.8 Milestones (suggested 6-month track)

| Month | Deliverable |
|---|---|
| 1 | Tier-0 core (store + monitor + canonicalizer + 5 adapters + receipts + minting); Layer-A mechanism suite passing |
| 2 | Tier-1 (provenance oracle+auto, memory strip, endorsement, AuthSpec builder); AuthLaunderBench v0 (Argument + Memory suites) |
| 3 | CaMeL + PACT-style + AUTHGRAPH-style + CLAWGUARD-style + PFI-style + Task Shield baselines integrated (originals where available, faithful reimpls calibrated on the source benchmark subset otherwise per §09.1); kill test (`KILL_TEST_PLAN.md`) run; AgentDojo run |
| 4 | Tier-2 (delegation + agent PKI); AuthLaunderBench full 6 suites; adapter-coverage corpus measured |
| 5 | All 12 ablations + 14 adaptive attacks (held-out red team); multi-model runs; statistics |
| 6 | Artifact hardening (Docker, traces, oracles, proof DAGs); writing; rebuttal experiments |
