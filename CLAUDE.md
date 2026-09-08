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
