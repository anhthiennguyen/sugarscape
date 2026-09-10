# sugarscape — working notes for Claude

This is a fork of the Epstein & Axtell Sugarscape ABM (`upstream` =
nkremerh/sugarscape, `origin` = anhthiennguyen/sugarscape). Nearly all local work
is on the **`locke` branch**: an agent-based reading of Locke's *Second Treatise
of Government*, built entirely inside `ethics.py`'s `class Locke(agent.Agent)`.

## The one rule: citation honesty

Every Locke mechanic is either tied to a **specific numbered section** of the
Second Treatise or **explicitly marked a design choice** where Locke is silent.
`PROPERTY.md` is the living, method-by-method reference for this — read it before
touching `class Locke`, and update it in the same change.

- Do not add Locke behavior without grounding it in a section or labelling it a
  design choice.
- Be precise about which section actually supports a claim. Past corrections in
  this repo: §122 is "tacit compliance ≠ membership" (not "joiners accept
  standing law" — that's §97); §125's "indifferent judge" is *not* satisfied by
  self-judgment (that's §240); a per-harvest levy that funds nothing is the §138
  wrong, not §140 legislation.
- The PDF is at `~/Locke Second Treatise of Government.pdf`.
- `PROPERTY.md` header points to `git show 9a70cff:GOVERNMENT.md` for the frozen
  Phase-2 snapshot (that file was removed from the working tree).

## Single class

All Locke sub-concepts — claims, trust, government, the founding votes, the levy,
grievance, the executor — live as methods and a `self.locke` dict on `class
Locke`. **Do not add new classes** for Locke concepts (e.g. no `Government`
class; a government is a bare `set()` of member agents).

## Architecture

- `ethics.py` `class Locke` (~`552`–end) — everything Locke, including
  trespass detection and debt enforcement (see below) — nothing Locke-
  specific lives in `agent.py` at all as of the current design.
- `agent.py` — base `Agent`. `doTimestep` calls two no-op hooks —
  `doGovernment()` right after `doTrading()`, `doProperty()`
  right after `updateValues()`, same gating as those calls — so a decision
  model with extra per-timestep behavior that isn't trading or value-updating
  (Locke's land/government/debt machinery) doesn't have to override
  `doTrading`/`updateValues` themselves. Only `Locke` overrides the hooks; every
  other decision model inherits the no-op unchanged. `doSteal(self, cell,
  amount)` is a new, generic (non-`Locke`-specific), non-lethal sibling to
  the pre-existing `doCombat`: loots up to `amount` from `cell.agent`,
  capped at what they hold, returns `(sugarLoot, spiceLoot)`, doesn't kill
  or relocate anyone. `Locke` is currently its only caller, but it carries
  no Locke-specific knowledge.
- `recordLandTrespassIfOwned` is **`Locke`-only, not universal**, and lives
  entirely under `class Locke`, called directly from `Locke`'s own
  `collectResourcesAtCell` override (not from any `agent.py` call site or
  hook — `agent.py`'s `collectResourcesAtCell` is completely untouched).
  `doForcefulDebtCollection` enforces via `doSteal` (non-lethal, amount
  capped at what's actually owed). A non-`Locke` agent can graze
  Locke-claimed land with zero consequence, and only `Locke` debtors are
  ever targeted. See the recurring-pattern bullets below for the
  tradeoffs made, why, and the two intermediate designs (a `doCombat`-based
  lethal version, and briefly a no-op-stub-on-`Agent` version) this
  superseded.
- `PROPERTY.md` — the citation-honesty reference. Line numbers drift; keep the
  ones for entries you rewrite accurate, don't chase the rest.
- `README`, `config.json`, `sugarscape.py`, `examples/locke_basic.json` — see
  config plumbing below.
- `gui.py` — Tkinter viewer. Coloring modes (`configureAgentColorNames` /
  `configureEnvironmentColorNames` + `lookupFillColor` branches) are kept **flat
  and single-signal**: each mode fully replaces the cell colour, no blending with
  the sugar/spice gradient, no two signals on one cell. Per-owner blending and a
  Property+Government overlay were both built and reverted. New *peer* modes
  (e.g. "Branches") are fine; overlays are not. A "Territory" environment
  mode (claimed land colored by owning government) was added and then
  removed by request; "Government"/"Branches" (agent modes) and
  `findGovernmentColor` are unaffected. "Branches"
  (agent mode, renamed from "Executor") uses one flat tone per branch of a
  Locke government an agent holds — executor gold, legislature pale green,
  ordinary member teal, non-member gray — checked in that priority order
  since an executor is often also a legislature member. Locke state is read
  duck-typed (`getattr(agent, "locke", None)`), `gui.py` does not import `ethics`.

### Recurring patterns

- **Six founding votes** (`voteGovernmentForm`, `voteReparationRate`,
  `voteRedistribution`, `voteExecutor`, `votePayFraction`,
  `voteLevyFraction`), voted in `attemptGovernmentFormation`, stored per
  member (`governmentForm` / `governmentRate` /
  `governmentRedistribution` / `governmentExecutor` /
  `governmentExecutorPay` / `governmentLevyFraction`), copied onto
  joiners in `addToGovernment` (§97) with no re-vote triggered by an
  ordinary join (see the reconvening-interval bullet below). (A seventh,
  `voteLandUse` — a toll-vs-`"closed"` policy — was removed; every
  non-owner harvest on owned land is now unconditionally a trespass debt,
  see the recurring-pattern bullet on the expected-cost value function.)
  `voteGovernmentForm` runs first and decides `findLegislature` — who
  actually casts the other five votes (full membership under
  `"democracy"` or the literal config sentinel
  `environmentLandLegislatureSize: "all"`, which forces `"democracy"`
  unconditionally regardless of the vote outcome; the top-K landholders
  under `"oligarchy"`/`"monarchy"` otherwise — both the same mechanism at
  different K). `voteReparationRate` and `voteLevyFraction` share one
  quantile-bracket mechanism (`findQuantileChoice`/
  `voteByQuantileBracket`): each voter's claims are ranked by
  fractional-position interpolation against a reference population's
  sorted claims to pick a menu choice, then the median of voters' choices
  wins. `voteLevyFraction` deliberately uses the *whole government* as
  its reference population rather than the (possibly size-1, under
  monarchy) legislature — a size-1 reference collapses every quantile
  breakpoint to that one value, always producing the mildest choice
  regardless of actual wealth. `voteReparationRate` and
  `voteGovernmentForm` itself are frozen at founding (§149 — dissolution
  — is the only way a government's form ever changes); `voteRedistribution`,
  `voteExecutor`, `votePayFraction`, and `voteLevyFraction` are re-voted
  at every legislative reconvening (see the interval bullet below).
- **Legislature-exclusive payout under restricted forms**: under
  `"oligarchy"`/`"monarchy"`, every member is still taxed by the levy,
  but only `governmentLegislature` members are paid back — a
  non-legislature member gets `0.0` regardless of the redistribution
  rule (`runLevyPass`). Under `"democracy"` (including the `"all"`
  sentinel, which forces it) payout still reaches everyone, unchanged
  since Phase 3/5.
- **Legislative reconvening is scheduled, not per-join or purely
  threshold-driven**: `environmentLandLegislativeReviewInterval`
  timesteps must pass since a government's `lastLegislativeReviewTimestep`
  before `reviewLegislature`/`reviewRedistribution`/`reviewExecutor`/
  `reviewExecutorPay`/`reviewLevyFraction` all run together again (§153
  — "not necessary... always in being"); a value of `1` reproduces "every
  timestep." An ordinary join is no longer itself an occasion — a joiner
  just inherits current law values. Death and consent withdrawal still
  force an *immediate* reconvening regardless of the interval.
- **Three grievance channels**: `grievance` (withdrawal §240 + dissolution
  §211) — fed by the redistributive levy (§138/199, now measured against
  the *whole* government even when a small legislature casts the vote —
  see `voteRedistribution`), by executor partiality (§199, in
  `doForcefulDebtCollection`), and by executor pay above
  `environmentLandExecutorMaintenanceFraction` (§138, in `runLevyPass`);
  `executorGrievance` (unenforced debt, §156) → executor replacement only
  (§152); `legislatureGrievance` (§199, accrued per timestep by a member
  excluded from the legislature under a restricted form and taxed but
  never paid) → once the government's summed `legislatureGrievance`
  crosses `environmentLandLegislatureGrievanceThreshold`, it forces an
  early reconvening ahead of the interval, distinct from both other
  channels (`doGovernanceReview`).
- **Rare-mechanism findings**: `executorGrievance` and `restrained` are
  coherent and scratch-tested but seldom fire in practice. Treat that
  rarity as a Lockean result (§225/§230 — rebellion is a last resort), not
  a bug to force. (`restrained` has churned: briefly removed as dead code
  under a lethal `doCombat`-based debt collection that let no debtor
  survive to be restrained, restored with the non-lethal `doSteal`, then
  its *effect* changed — it's no longer a hardcoded avoid-all-foreign-land
  override, just one weighted term in `findEthicalValueOfCell`'s
  expected-cost sum. The field and its setter are unchanged throughout.)
- **Fixed finding: movement valuation ignored the toll-paying lawful-access
  path, suppressing reproduction enough to tip marginal populations into
  extinction**. `findEthicalValueOfCell` used to score *every* foreign
  claimed cell at `0` for movement purposes, whether the owning
  government's `governmentLandUse` was `"closed"` or a paid toll — even
  though `agent.py`'s `recordLandTrespassIfOwned` already implements
  lawful, toll-paying entry (§119/124) that leaves a net positive gain.
  Since the valuation never reflected that net gain, agents never chose
  to enter toll-payable land, needlessly shrinking their forageable range
  to their own plot plus the shrinking unclaimed commons. A 100-seed run
  of `config.json`'s pure-`"locke"` population found most seeds crashing
  to extinction well before timestep 500, with `restrained` and
  outstanding debts both ~zero throughout every doomed run (ruling out
  trespass punishment or debt seizure); a matched, same-seed comparison
  against the `"none"` decision model isolated the cause to reproduction:
  Locke agents generated ~40-60% as many compatible-neighbour
  reproduction opportunities as otherwise-identical plain agents, and
  several seeds that recover under `"none"` reliably went extinct under
  `"locke"` for exactly this reason. Fix: a non-member entering under a
  toll price (not `"closed"`) now scores the cell at
  `(sugar + spice) * (1 - landUse)` — the same fraction the agent would
  actually keep after paying — rather than `0`; `"closed"` policy, a
  fellow member on a co-member's own specific claim, and a restrained
  agent's blanket avoidance are all unchanged. See
  `findEthicalValueOfCell`'s PROPERTY.md entry for the full verification.
  Does not fully eliminate extinction risk — `config.json`'s own
  demographic parameters (`agentReplacements: 0`, tight fertility
  windows) already put even the `"none"` baseline in a boom-or-bust
  regime with real extinction odds and no Locke mechanics involved.
  *(Superseded: the toll mechanic this fix was about no longer exists —
  `findEthicalValueOfCell` is now a benefit-minus-expected-cost sum, see
  the value-function bullet below. Kept as history.)*
- **Negative result: strengthening the "enough, and as good" proviso to
  also check neighbors' vision (`leavesEnoughForNeighbors`) did not
  measurably help.** Extinction stayed effectively unchanged (100/100 on
  a 100-seed run, vs. 94/100 before). The proviso only blocks a claim
  once land is *already* locally scarce, but the damage was already done
  during the initial land-grab, when land looks abundant by any
  vision-local metric — a stricter proviso threshold can't retroactively
  fix over-claiming that already happened while the check trivially
  passed. Still kept as a genuine citation-honesty improvement (Sect. 27's
  proviso is textually about the position of *others*, not just the
  claimant), just not the fix for extinction.
- **Fixed finding: unbounded per-agent claim accumulation was the
  dominant cause of excess mortality, not any single ancillary
  mechanic.** An empirical trace found individual agents holding up to
  12 simultaneous claims, with the population average climbing toward
  7-8 within 30 timesteps — the map wasn't fragmented by ~250 claims
  (one per agent), it was fragmented by several times that. A decisive
  ablation (disabling claim acquisition outright, leaving trust,
  government, the levy, and debt collection all active) dropped a
  30-seed extinction rate from 94% to 17% — *below* the `"none"`
  baseline of 45% — isolating unconstrained accumulation, not the levy,
  trust, or government formation, as the driver. Fix:
  `environmentLandMaxClaimsPerAgent` (default `1`) caps how many cells
  one agent may hold claimed at once, checked in `collectResourcesAtCell`
  alongside (not instead of) the proviso — grounded in Sect. 36's own
  argument that a person's labour and consumption naturally bound their
  just holdings to "a small part," made explicit here as a hard cap since
  an agent's vision/movement/lifespan let it wander far past that.
- **Added, then removed: desperation overriding moral restraint
  (`isDesperate`).** Originally: a Locke agent about to end the timestep
  with negative sugar or spice on its current holdings alone treated every
  cell at full value, foreign or not, closed policy or not, restrained or
  not — literal starvation overriding both the ordinary exclusion and the
  restrained penalty, grounded in Locke's First Treatise Sect. 42 (the
  "charity" right to another's plenty in extreme want — flagged as
  unverifiable against the locally available PDF, which is Second
  Treatise only). **Removed** after an ablation showed it hurts aggregate
  survival rather than helping it: a 25-seed same-seed sample (reproduced
  identically across two independent reruns per condition, unusually
  stable for this codebase) found 8/25 extinct (32%) with it active vs.
  4/25 extinct (16%) ablated — removing it roughly halved the extinction
  rate; consent withdrawal also fired less often without it (~7.4/seed vs.
  ~5.6/seed), while government dissolution was unaffected (~41.2 vs.
  ~40.2/seed). Plausible mechanism (not independently confirmed further):
  a desperate trespass still creates a violation debt on non-toll land and
  unconditionally resets every witnessing neighbor's trust in the
  trespasser, so a population where starving agents periodically incur
  debt and wreck their own trust standing this way ends up less resilient
  in aggregate than one where they simply starve without those
  liabilities — even though the override clearly helped the individual
  agent survive that one timestep.
- **Added, then removed: consent-based co-ownership grants
  (`doLandConsentGrants`).** Originally: once a claim had gone unharvested
  for more than half of `environmentLandDecayTimesteps`, its owner
  granted the most-trusted cell-adjacent neighbor (same trust bar as
  founding a government, and below their own claims cap) an even
  co-ownership share, hedging against the claim decaying to non-use since
  a co-owned cell only decays if *neither* owner ever tends it. Grounded
  in Sect. 28 (disposing of one's property by consent) and Sect. 38
  (spoilage risk), split ratio and trigger both flagged as design
  choices. **Removed by request.** Co-ownership survives via
  `doInheritance` (splitting a deceased owner's claim among heirs); only
  this voluntary trust-based path to creating it is gone.
- **Combined verification (toll valuation + neighbor-vision proviso +
  claims cap + desperation + consent grants) — 100-seed run, `"locke"`
  population, timestep 500: 67/100 survived** (median final population
  948), **33/100 extinct** (median extinction timestep 183) — a full
  reversal from the 94-100% extinction measured for each earlier partial
  version of this fix, and better than the matched `"none"` baseline's
  55% survival over the identical 100 seeds. The per-agent claims cap was
  already independently confirmed as the dominant lever; desperation and
  consent grants were added afterward per direct request and verified
  together with everything else in this one run, not each in its own
  isolated ablation.
- **Removed: the debt-collection grace period
  (`environmentLandForcefulCollectionGraceTimesteps` /
  `environmentLandExecutorNeglectGraceTimesteps`)** — both were already
  documented as a pure, ungrounded design choice ("Locke specifies no
  time period at all before force becomes legitimate"), so removing them
  isn't a citation-honesty regression. A debt is now collectible,
  pursuable (`findEnforcementTarget`), and countable as neglect
  (`doGovernanceReview`) starting the instant it's created. A 20-seed
  same-seed comparison found this measurably helps survival: 13/20 with
  the grace windows vs. 16/20 without, at timestep 500 — faster,
  more certain enforcement keeps less wealth tied up in unresolved
  trespass debt during the population's fragile early window. Kept as an
  addition on top of the combined-verification fixes above, not
  re-verified together with them in one run.
- **Refactored: `Locke` no longer overrides `doTrading`/`updateValues`.**
  Replaced with `agent.py`-level no-op hooks `doGovernment`/
  `doProperty`, called at the same points under the same
  death-gating; `Locke` overrides the hooks instead, with the exact same
  method calls in the exact same order. Every other decision model
  inherits the no-op unchanged. Verified via a deterministic scratch test
  of call order/gating (not seed comparison — see next bullet for why)
  plus a 25-seed extinction-rate check (7-8/25 extinct across two
  identical-code reruns vs. 10/25 post-refactor — within the noise
  established by the identical-code reruns themselves) and the full
  29-config smoke suite.
- **Important methodological finding: single-seed population comparison
  is not a valid verification technique on this branch.** Rerunning
  byte-identical code, same seed, same config, in a fresh process was
  found to produce different final populations and even different
  survive/extinct outcomes for the *same* seed (e.g. one run extinct,
  an immediate rerun of the identical code `pop=887`). Root cause: a
  government is a bare `set()` of member agents (see "Single class"
  above); Python's default object hash is identity/address-based, so a
  `set`'s iteration order isn't reproducible across process runs even
  under a fixed `random.seed()` (`PYTHONHASHSEED` doesn't fix this — it
  only governs `str`/`bytes` hashing). This predates and is unrelated to
  any change made this session; it just means **only aggregate stats
  across a seed sample** (extinction rate, median population) are a
  sound basis for comparing two versions of the code — never a single
  seed's exact outcome, and even aggregate stats need a same-code
  rerun as a noise baseline before trusting a small observed gap.
- **Redesigned: `recordLandTrespassIfOwned` moved from a universal
  base-`Agent` check to a `Locke`-only method, an explicit tradeoff, not
  a citation-honesty improvement.** The original version's whole point was
  Sect. 6 universality — it fired for any decision model trespassing on
  Locke-claimed land. Moved into `class Locke` at the caller's request (to
  keep all property logic in one place). Consequence, deliberately
  accepted: a non-`Locke` agent can graze Locke-claimed land with zero
  consequence — no toll, no debt, no trust reset. A 16-seed
  `["locke", "none"]` run confirmed the mechanism directly (tens of
  thousands of free harvests per seed that used to hit the toll/violation
  pipeline) but found no clean, one-directional population effect —
  consistent with this simulation's established chaotic sensitivity to
  any code change. **Final wiring** (after an intermediate no-op-stub-on-
  `Agent` design): `agent.py`'s `collectResourcesAtCell` is completely
  untouched; `Locke`'s own pre-existing `collectResourcesAtCell` override
  (already there for claim creation) calls `recordLandTrespassIfOwned`
  directly — no hook, no stub, no base-class involvement of any kind.
- **Redesigned twice: forceful debt collection's enforcement mechanism.**
  Original: manual `neighbor.sugar -=`/`creditor.sugar +=` number
  manipulation — no attack, no confrontation, nothing the base engine
  recognized as a modeled event; from the debtor's perspective,
  indistinguishable from theft. **First redesign** (superseded): routed
  through the base engine's pre-existing `doCombat(cell)` — reused engine
  code with no new `agent.py` method, but `doCombat` is unconditionally
  lethal with loot capped by a flat `maxCombatLoot` unrelated to the debt,
  so every collection killed the debtor regardless of how small the debt
  was. This made the `restrained` flag (Sect. 12's non-lethal restraint,
  set only on a survivor) permanently unreachable — removed as dead code,
  along with its read site in `findEthicalValueOfCell`. **Final design**:
  a new, minimal, generic `agent.py` method, `doSteal(self, cell, amount)`
  — mirrors `doCombat`'s structure (a real, modeled event, loots up to a
  cap, transfers to the caller) but takes `amount` as a parameter instead
  of a flat constant, doesn't kill, doesn't relocate the attacker (the
  victim is still on that cell). `doForcefulDebtCollection` calls it with
  `amount = debt["amount"]`, so a poor debtor pays what they can and the
  remainder stays outstanding rather than the whole debt vanishing either
  way. This let `restrained` come back too, since a debtor can survive
  collection again. Citation payoff: Sect. 12's proportionality cap
  ("sufficient to make it an ill bargain... give him cause to repent") is
  now honored literally — recover up to what's owed, no more, no killing
  — resolving the tension the `doCombat` version had knowingly accepted.
  Verified via scratch tests (full and partial recovery, `restrained`
  set, `doSteal` itself unit-tested) and a 25-seed same-seed sample of
  pure-`"locke"`: 28% extinct, the low end of (not outside) the 28-40%
  noise band every version of this method has landed in across several
  same-seed reruns this session — no version has ever been shown to
  differ from another beyond that noise.
- **Redesigned: `findEthicalValueOfCell` is now benefit-minus-expected-cost,
  and the toll/`"closed"` land-use vote is gone entirely.** `findEthicalValueOfCell`
  used to be hardcoded overrides — a flat `-(sugar+spice)-1` for a
  `restrained` agent, a `* (1 - landUse)` toll discount for lawful paid
  entry, a flat `0` for everything else. Now: `cellValue = sugar + spice -
  findExpectedViolationCost(cell, owners)`, where the cost is an additive
  sum of four weighted terms (`environmentLand*CostWeight` keys) — owner
  count, whether the land is governed at all, the owner's reparation rate,
  and the agent's own `restrained` status. Deliberately reads **nothing**
  an agent couldn't plausibly know: no executor-presence check, no
  government-size check — a Locke agent is blind to another government's
  internal enforcement capacity (the real `doForcefulDebtCollection` still
  only works where an executor exists; this is only about ex-ante belief).
  `restrained` is folded in as one weighted term, not a separate override
  — its field/setter are unchanged, but it no longer *guarantees*
  avoidance: enough food outweighs it. `voteLandUse`/`governmentLandUse`/
  `environmentLandUseChoices` and the whole toll-vs-`"closed"` concept are
  removed (the vote had collapsed into a proxy for government size, per a
  user-reported finding); `recordLandTrespassIfOwned` now makes *every*
  non-owner harvest on owned land a trespass debt, with compensated access
  happening only after the fact via `settleDebtsVoluntarily`. Also removed
  in the same change: `doLandConsentGrants`, `territoryGovernmentFor`.
  Six founding votes now, not seven.

## Config plumbing (load-bearing gotcha)

A config key is only honored if it **already exists in the hardcoded defaults
dict** in `sugarscape.py` (the `configuration = {...}` at ~line 1845; the
`environmentLand*` block is ~line 1914). A key present only in `config.json` /
an example is silently ignored. So every new option needs, in sync:

1. `sugarscape.py` defaults dict, 2. `README` entry (alphabetical among
`environmentLand*`, with `Note: Only relevant to the "locke" decision model.`),
3. `config.json` and `examples/locke_basic.json` if the scenario sets it,
4. a `PROPERTY.md` entry.

`config.json` and `examples/*.json` use **compact arrays** (`[1, 2]` on one
line). Do not reformat them with `json.dump(..., indent=4)` — hand-edit.

## Running & testing

- No unit-test framework. `make test` (from `tests/`) runs every
  `examples/*.json` headless for 200 steps as a smoke test — passes = no crash.
  It calls `os.get_terminal_size()`, so run it under a pty:
  `cd tests && script -q /dev/null python test.py --conf ../config.json`.
- `python sugarscape.py --conf <cfg>` — **without `"headlessMode": true` it opens
  a Tkinter GUI and hangs** in a headless environment. Always set
  `headlessMode: true` + `debugMode: ["none"]` (or `["agent"]` for the
  per-agent trace) for scripted runs.
- **Verify Locke mechanics with scratch assertion scripts** in the scratchpad:
  build lightweight stand-ins (a fake `cell`/`agent` with just the attributes a
  method reads), call the real `ethics.Locke.method(fakeSelf, ...)`, assert.
  `agent.Agent.doInheritance = lambda self: None` stubs out the heavy base call
  when testing the Locke tail. When you add a `self.locke` key or a method that
  reads `vision`/`movement`, the older scratch tests' fake agents need the new
  field too.
- Debug-run findings (dynamics, rates) go in the plan / PROPERTY.md, tuned
  against a ~250-step run.

## Git

- Branch `locke`. Commit / push only when asked. Commits so far: Phase 1
  (property), Phase 2 `9a70cff` (trust/government), Phase 3 `9facb82`
  (legislation/levy/withdrawal). The executor work is uncommitted as of this
  note.
- `origin` is the user's fork; pushing needs explicit approval (the auto-mode
  classifier blocks `git push`).
