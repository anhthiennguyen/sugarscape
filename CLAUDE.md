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

- `ethics.py` `class Locke` (~`552`–end) — everything Locke.
- `agent.py` — base `Agent`. Two methods carry Locke-relevant logic because any
  decision model can trespass: `recordLandTrespassIfOwned` (trespass detection,
  witness trust reset, territory-toll interception — all duck-typed via
  `getattr(x, "locke", None)` since `agent.py` cannot import `ethics.py`) and
  `collectResourcesAtCell` (records `lastHarvest`, gates claim creation on a
  non-zero harvest).
- `PROPERTY.md` — the citation-honesty reference. Line numbers drift; keep the
  ones for entries you rewrite accurate, don't chase the rest.
- `README`, `config.json`, `sugarscape.py`, `examples/locke_basic.json` — see
  config plumbing below.
- `gui.py` — Tkinter viewer. Coloring modes (`configureAgentColorNames` /
  `configureEnvironmentColorNames` + `lookupFillColor` branches) are kept **flat
  and single-signal**: each mode fully replaces the cell colour, no blending with
  the sugar/spice gradient, no two signals on one cell. Per-owner blending and a
  Property+Government overlay were both built and reverted. New *peer* modes
  (e.g. "Territory", "Executor") are fine; overlays are not. Locke state is read
  duck-typed (`getattr(agent, "locke", None)`), `gui.py` does not import `ethics`.

### Recurring patterns

- **Seven founding votes** (`voteGovernmentForm`, `voteReparationRate`,
  `voteLandUse`, `voteRedistribution`, `voteExecutor`, `votePayFraction`,
  `voteLevyFraction`), voted in `attemptGovernmentFormation`, stored per
  member (`governmentForm` / `governmentRate` / `governmentLandUse` /
  `governmentRedistribution` / `governmentExecutor` /
  `governmentExecutorPay` / `governmentLevyFraction`), copied onto
  joiners in `addToGovernment` (§97) with no re-vote triggered by an
  ordinary join (see the reconvening-interval bullet below).
  `voteGovernmentForm` runs first and decides `findLegislature` — who
  actually casts the other six votes (full membership under
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
  regardless of actual wealth. `voteReparationRate`, `voteLandUse`, and
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
- **Rare-mechanism findings**: several mechanisms (`restrained`, the
  `executorGrievance` channel) are coherent and scratch-tested but seldom fire in
  practice. Treat that rarity as a Lockean result (§225/§230 — rebellion is a
  last resort), not a bug to force.
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
- **Added: desperation overrides moral restraint (`isDesperate`).** A
  Locke agent about to end this timestep with negative sugar or spice on
  its current holdings alone treats every cell at full value, foreign or
  not, closed policy or not, restrained or not — literal starvation
  overrides both the ordinary exclusion and the stricter restrained
  penalty. Grounded in Locke's First Treatise Sect. 42 (the "charity"
  right to another's plenty in extreme want) — flagged as unverifiable
  against the locally available PDF, which is Second Treatise only (see
  the citation-honesty section above); sourced from general familiarity
  with the passage. The trespass itself is still recorded and still
  accrues a debt exactly as any other trespass would — desperation
  changes the *decision* to enter, not the consequences of having
  entered.
- **Added: consent-based co-ownership grants (`doLandConsentGrants`),
  motivated by guarding against decay.** Once a claim has gone unharvested
  for more than half of `environmentLandDecayTimesteps`, its owner looks
  for the most-trusted cell-adjacent neighbor (same bar as founding a
  government) who isn't already an owner and is below their own
  `environmentLandMaxClaimsPerAgent`, and splits the cell evenly with
  them if one exists. A cell with two owners only decays if *neither*
  ever tends it, since either one harvesting resets the shared
  `lastHarvestedTimestep` — the actual mechanism this is meant to
  exploit for survival, per the user's own framing. Grounded in Sect. 28
  (an owner's standing to dispose of what's his by consent) and Sect. 38
  (the same non-use/spoilage risk `processLandAbandonment` already
  enforces) — the split ratio and the risk-based trigger point are design
  choices, since Locke specifies neither.
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
