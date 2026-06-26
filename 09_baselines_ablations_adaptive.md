# 09. Baselines, Ablations, and Adaptive Attacks

This section fixes the two things that most threaten the paper: **strawman baselines** and **mischaracterized prior systems**. Baselines are anchored on the *correctly identified* adjacent work (§12), each configured to its real mechanism, under an explicit **three-tier reproduction policy**, with an **oracle-vs-automatic provenance** axis, a fully specified **ProofObjectRemoved** ablation, and **shell/canonicalization** adaptive attacks.

## 9.1 Baseline reproduction policy (label every result with its tier)

| Tier | Definition | Reporting rule |
|---|---|---|
| **Original** | The authors' released implementation, run on our harness, same backbone/budget | Cite the paper; results are the system's |
| **Faithful reimplementation** | Reimplemented from the paper, **calibrated on a subset of the source paper's own benchmark** to reproduce its reported behavior before use | Cite the paper; label "(faithful reimpl)"; must pass calibration or be downgraded |
| **Representative** | A technique-class implementation when no code exists / full reproduction is infeasible; **fully described** in an appendix and **not attributed** to the named system's numbers | Label "(representative <class>)"; **do not claim to beat the original system** |

We never claim to beat a system we could only implement representatively; we say "a representative <class> configuration."

## 9.2 Baseline set (correctly identified, configured to real mechanism)

**Main baselines** (the comparison the contribution stands or falls on; in the kill test and the full study):

| Baseline | Tier (target) | Configured mechanism (must match the real system) |
|---|---|---|
| **Native (ReAct)** | Original | no defense — risk floor |
| **CaMeL** | Original (else faithful, calibrated) | P-LLM/Q-LLM isolation; capability metadata on values; data-flow graph via the custom interpreter; security policies at tool calls. **Taken seriously, tuned, not strawmanned** — the load-bearing comparison and an *adopted* component for G4 |
| **PACT-oracle** | Faithful/representative | Argument-level provenance with **oracle** source labels; authority-bearing-argument roles (target/command/credential/content/selector/control) — PACT's ceiling |
| **PACT-auto** | Faithful/representative | Same, with **automatic** provenance — the deployable PACT number |
| **AUTHGRAPH-style** | Faithful/representative | Clean **Authorization Graph** + **Injected Reasoning Graph**; **tool-level** + **parameter-source alignment** |
| **CLAWGUARD-style** | Faithful/representative | Deterministic tool-call boundary + rule enforcement + approval; covers content injection / MCP poisoning / skill injection. **A strong MCP/skill defense — treat it as such**; we do **not** expect to out-ASR it on MCP/skill, we measure the extra (proof/endorsement/scoping/audit) |
| **CapProof-oracle / CapProof-auto** | Ours | CapProof with **oracle** vs **automatic** provenance — ceiling vs deployable; head-to-head with PACT |

**Auxiliary baselines** (breadth / specific-channel comparators; reported where relevant, not the core comparison):

| Auxiliary | Tier (target) | Why it is included |
|---|---|---|
| **DRIFT-style** | Faithful/representative | **Memory isolation** — the honest comparator on the Memory suite; keeps "we solve memory" from being overclaimed |
| **PFI-style** | Faithful/representative | Trusted/untrusted agent + Data ID + DataGuard/CtrlGuard — the closest comparator on the Delegation suite. **Real adjacent work**; auxiliary in the MVP due to an architectural mismatch (privilege separation is coarser than per-argument consumption), but **promoted to a main baseline on the Delegation and data-injection suites if implementation resources allow**, or at minimum evaluated on a subset of those suites |
| **AgentArmor-related subset** | Representative (trace-analysis) | CFG/DFG/PDG over the runtime trace + graph annotator/inspector — a **trace-analysis** point of comparison; included as a related-work configuration on a subset, **not** a main baseline (it detects from the trace post-hoc; CapProof acts pre-execution) |
| **Task Shield** | Original (else faithful) | Test-time task-alignment scoring |
| **PromptArmor-style** | Representative | Input/instruction cleaning before the agent |

### Oracle-vs-automatic provenance axis
Provenance quality confounds every provenance-based defense. PACT and CapProof are each run with **oracle** (ground-truth source labels) and **automatic** provenance, so we separate the *mechanism's ceiling* from the *deployable* number and compare PACT-vs-CapProof on equal provenance footing. This pairs with the provenance-sensitivity sweep (§08).

## 9.3 Ablations (≥10; removed mechanism → expected failure → target → metric)

| # | Variant | Removes | Expected failure | Target suite | Metric |
|---|---|---|---|---|---|
| 1 | NoArgRole | authority-bearing-argument typing | recipient/path/cmd/endpoint laundering | Argument | ASR↑ |
| 2 | NoMemoryStrip | memory authority stripping | stored values become authority | Memory | ASR↑ |
| 3 | NoDelegCert | delegation certificates | NL relay grants authority | Delegation | ASR↑ |
| 4 | NoOneShot | one-shot endorsement | approval replay/widening | Endorsement | ASR↑ |
| 5 | NoCapConsume | consumption (caps reusable) | replay succeeds | Arg/Endorse | replay-rej↓, ASR↑ |
| 6 | NoTaskBinding | task_id binding | cross-task cap reuse | all | ASR↑ |
| 7 | NoAgentBinding | subject_agent binding | cross-agent cap reuse | Delegation | ASR↑ |
| 8 | NoMetadataNonAuthority | metadata/skill = non-authority | metadata mints authority | MCP/Skill | ASR↑ |
| 9 | LLMVerifier | deterministic monitor → LLM judge | fake-proof / proof-injection | all | ASR↑ |
| 10 | WeakCanonicalization | per-role canonicalizer → identity | alias/punycode/symlink/traversal/redirect bypass | Arg/MCP | ASR↑ (ties to bypass gate) |
| 11 | **ProofObjectRemoved** | carried proof DAG → monitor searches state | *no* security change; latency/explainability/localization/audit/replay change | all | see §9.4 |
| 12 | NoFaithfulnessConfirm | high-impact `inferred` minted without §3.11 | ambiguity-exploit over-broadens | Arg/Memory + ambiguity set | over-broadening↑, ASR↑ |

## 9.4 ProofObjectRemoved — does the explicit proof object earn its place?

Because **PCAA** already owns proof-carrying (§12.4), CapProof must justify carrying an explicit proof DAG on grounds beyond novelty. This ablation compares **CapProof-with-proof** (agent emits a proof DAG; monitor verifies it) against **CapProof-search** (monitor searches store/provenance state for a justification; no carried proof) on six axes:

| Axis | Measurement | Hypothesis |
|---|---|---|
| **Security** | ASR / Secure-Utility across suites | **No change** — the monitor re-derives either way; a change means the proof is load-bearing in an unintended way (a bug) |
| **Latency** | verifier p50/p95/p99 on **shallow** (1 arg, no derivation) vs **deep** (multi-step derivation / delegation chain) actions | benefit concentrated on deep actions (verify-vs-search) |
| **Explainability** | can a human read *why* an action was authorized from the artifact? | carried proof gives a structured rationale; search gives a monitor trace |
| **Failure localization** | precision of identifying *which* binding/cap/receipt failed on denial | carried proof **names the failing step**; measure vs monitor re-derivation |
| **Auditability** | completeness of the post-hoc authorization record | carried proof is a portable, signed-evidence-referencing artifact |
| **Replayability** | cost to re-validate an unchanged prefix after replanning | carried proof enables cheap re-check (Prefix Soundness) without re-search |

**Pre-committed rule (and its risk, stated plainly).** The likely outcome is that **Security is unchanged and CapProof-search is no slower (or faster)** on most actions, because the monitor re-derives the authorization either way. **If so, the paper must NOT present "proof-carrying" as its identity** — the main line stays **capability-consuming authorization** (consume a scoped capability; deterministic verifier checks the authorization chain), and the explicit proof DAG is demoted to an *optional artifact* whose value, if any, is confined to **auditability, replayability, failure localization, and decoupled construction** (synthesizer separate from verifier). Only if the deep-action latency benefit or the audit/localization benefit is **material and measured** do we retain the proof object as a named component — and even then positioned relative to PCAA, never as the contribution. We follow the data; we do not let a buzzword survive a null result.

## 9.5 Adaptive attacks (≥12; attacker knowledge → strategy → expected baseline failure → CapProof denial)

Attacker knows the public spec/schemas/rules/APIs and (in the "full reason" condition) denial reasons; cannot read the store or keys.

| # | Attack | Strategy | Expected baseline failure | CapProof denial reason |
|---|---|---|---|---|
| 1 | Fake proof injection | NL "authorization proof" in a page/tool output | LLM-judge configs (Task Shield; ablation #9) may accept | `ProofNotCanonical`/`NoCap` |
| 2 | Capability forgery | guessed/forged `cap_id` | n/a to non-cap baselines | `NoCap` (MAC/lookup fail) |
| 3 | Capability replay | resubmit consumed cap / old proof | non-consuming baselines (CLAWGUARD approval, AUTHGRAPH detect) reuse | `ConsumedCap` |
| 4 | Scope confusion | use a recipient cap to reach an attacker address | provenance-only baselines may bind wrong value | `CapPredicateMismatch` |
| 5 | Task confusion | reuse cap across tasks | no-task-binding baselines | `TaskMismatch` |
| 6 | Agent confusion | use agent A's cap as B | PFI without per-cap agent binding | `AgentMismatch` |
| 7 | Memory authority replay | write authority to memory, fire next turn | baselines that do not, by default, carry authority across turns (PACT/AUTHGRAPH/CLAWGUARD as configured) | `MemoryAuthorityUse` |
| 8 | Delegation amplification | child cap exceeds parent | no-cert baselines; PFI coarse separation | `DelegationAmplification` |
| 9 | Endorsement widening | reuse/persist/widen one-shot approval | approval-gate (CLAWGUARD) / certificate (PCAA) configs | `EndorsementScopeError`/`DataClassMismatch`/`ConsumedCap` |
| 10 | MCP metadata minting | metadata declares an authorized endpoint/recipient | metadata-trusting / graph-seeded-from-metadata baselines | `MetadataCannotMintAuthority` |
| 11 | Skill workflow minting | skill frames exfil as a workflow stage | alignment baselines accepting "documented step" | `NoCap(endpoint/command)` |
| 12 | Tool alias bypass | exfiltrate via `http_post` instead of `send_email` | tool-name-keyed rule baselines | `NoCap(external_endpoint)` (role-keyed) |
| 13 | Canonicalization bypass | punycode/IDN, `@`-userinfo, symlink, `..`, 302 redirect, look-alike host | weak-canonicalization baselines; naive host allowlists | `CanonicalizationMismatch`/`CapPredicateMismatch` (post-redirect) |
| 14 | Derived-content confusion | claim a forbidden value is a "safe derivative" | provenance baselines accepting the claim | `BadDerivation` (no signed receipt) |
| 15 | **Ambiguity exploit** (elicitation) | inject **no** instruction; shape context so an ambiguous request resolves to an attacker value | **every** intent-trusting defense, incl. CapProof with §3.11 OFF | mitigated by §3.11; **measured** in `AUTHSPEC_FAITHFULNESS_GATE.md`, not claimed defeated |
| 16 | **Shell env/cwd/stdin side channel** | influence a `run_shell` effect via `env`/`cwd`/`stdin` without changing `command`; `sh -c`, pipe, redirect, base64 | baselines checking only the `command` string | denied by **template env/cwd/stdin contract**; `sh -c`/pipe/redirect/base64/network → deny or endorsement (`CommandTemplateViolation`) |
| 17 | **Template-argument injection** | shell metacharacters in an allowlisted template hole (`msg="ok; rm -rf /workspace"`) | baselines allowing free-form shell | rejected by typed hole `string_no_shell_meta` (`TemplateArgRejected`) |

## 9.6 Attack generation protocol
- **Template-based** (held-out red team) + **LLM-based adaptive** (attack LLM gets task, schema, public rules, prior denial reason; ≤5 mutation rounds).
- **Denial-reason conditions:** full vs coarse reason; report ASR delta (does telling the attacker *why* help?). If full reasons help materially, recommend coarse external reasons + full internal logs.
- **Held-out authorship:** adaptive attacks for reported numbers are authored/run by someone who did not build the defended components.

## 9.7 Pre-registered falsification conditions
- If **DRIFT-style memory isolation**, **AUTHGRAPH-style**, or **PACT-auto** (extended across turns) matches CapProof on the **Memory** suite at comparable utility → the memory contribution collapses; pivot to delegation+endorsement (`KILL_TEST_PLAN.md` §5).
- If **CLAWGUARD-style** matches CapProof on **MCP/skill** ASR (expected — it is a strong MCP/skill defense) **and** CapProof shows no usability or proof/auditability advantage there → drop any MCP/skill *security* claim; keep only the proof/endorsement/scoping/audit framing on those suites.
- If **CaMeL**, suitably policy-configured, blocks the cross-boundary suites at similar utility and comparable over-asking → narrow the claim to the consuming-authorization calculus + `G*`-relative soundness (formal-methods-leaning), or pivot to the usability/auditability story.
- If **CapProof-auto** ASR approaches Native → impractical; reframe as oracle-provenance-dependent and report the gap.
- If dynamic-task endorsement count is high (> ~2/task) → narrow to static/high-impact settings.
- If **ProofObjectRemoved** shows no security change and no material latency/audit/localization benefit (§9.4) → the proof object is not the identity; keep capability-consuming authorization as the main line.
