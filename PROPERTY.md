# Property (the `locke` decision model)

A complete, source-order reference to every file the `locke` branch has ever
touched (per `git diff a46ec6f..HEAD --stat`, the commit before the `Locke`
class existed), every class in those files that changed, and every method in
those classes — or, for single-line/config changes, the line itself.

This supersedes the former `GOVERNMENT.md` (a frozen snapshot of the Phase 2
government commit `9a70cff`); for that commit's original per-method citations see
`git show 9a70cff:GOVERNMENT.md`.

## `ethics.py` — `class Locke(agent.Agent)` (`ethics.py:552-1225`)

- **`__init__(self, agentID, birthday, cell, configuration)`** (`553-561`) —
  Calls `super().__init__` for standard agent setup, then adds `self.locke`,
  the agent's own political/property bookkeeping: `claims`, `debtsReceivable`,
  `trust` (`{otherID: score}`), `trustThreshold` (drawn once at birth from
  `environmentLandTrustThresholdRange`), `government` (the shared `set()`, or
  `None`), `governmentRate` (the reparation multiplier its government voted),
  `restrained` (the Sect. 12 restraint flag),
  `governmentRedistribution` (`"equal"`/`"proportional"` — how the
  Sect. 138 levy is paid back out), `grievance` (`0.0`; cumulative net loss
  under `proportional`, the fuel for Sect. 240 withdrawal), `lastHarvest` (this
  timestep's gross harvest, for the levy), `lastLevyTimestep` (idempotence
  guard for the once-per-timestep levy pass), `governmentExecutor` (a
  `frozenset` of the member(s) appointed to collect on the society's
  behalf — Sect. 126/130), and
  `executorGrievance` (`0.0`; a separate accumulator for the Sect. 156
  complaint, drives executor replacement only, never withdrawal),
  `governmentExecutorPay` (the fraction of the levy pool paid to the
  executor(s), one entry from `environmentLandExecutorPayChoices` —
  Sect. 140 maintenance up to a point, Sect. 138 beyond it),
  `governmentForm` (`"democracy"`/`"oligarchy"`/`"monarchy"` — Sect. 132's
  taxonomy of who holds legislative power, decided once at founding and
  never re-voted), `governmentLegislature` (a `frozenset` of the
  members currently holding that power — the full membership under
  democracy, the top-`environmentLandLegislatureSize` landholders
  otherwise, or the full membership regardless of form when that config
  is the string `"all"`; recomputed on roster change even though
  `governmentForm` itself doesn't change), `governmentLevyFraction` (the
  levy rate the legislature voted, one entry from
  `environmentLandLevyFractionChoices`), `lastLegislativeReviewTimestep`
  (idempotence marker for the scheduled reconvening, analogous to
  `lastLevyTimestep`), and `legislatureGrievance` (`0.0`; accrues only on
  a payout-excluded subject under a restricted form, forces an early
  reconvening — a third channel, distinct from both `grievance` and
  `executorGrievance`).
  *Design choice — bookkeeping structure, no textual analog. `trustThreshold`, `restrained`, `grievance`, `executorGrievance`, `legislatureGrievance` are all per-agent and never inherited (Sect. 116/118 for political disposition; Sect. 12 restraint and one's own grievance are personal). The government-law fields (rate, redistribution, executor, executor pay, form, legislature, levy fraction) are copied from existing members on join (Sect. 97), not from a parent.*
- **`cellOwners(self, cell)`** (`557-560`) — Lazily creates and returns
  `cell.owners` (a `{agent: share}` dict) the first time it's touched. The
  central accessor for reading ownership anywhere in the class.
  *Design choice — lazy accessor plumbing for the ownership concept grounded in Locke, Sect. 27: "every man has a property in his own person... the labour of his body, and the work of his hands, we may say, are properly his."*
- **`cellPendingViolations(self, cell)`** (`569-572`) — Lazily creates and
  returns `cell.pendingViolations`, the list of thefts not yet converted
  into debt.
  *Design choice — accessor plumbing.*
- **`agentLandDebtsOwed(self, agent)`** (`577-580`) — Lazily creates and
  returns `agent.landDebtsOwed` on **any** agent object passed in, not just
  `Locke` instances. This single line is what lets a non-`Locke` agent carry
  land debt at all.
  *Design choice — accessor plumbing; the underlying reparation debt it stores is grounded in Locke, Sect. 10 (see `convertViolationsToDebts` below).*
- **`claimCellFor(self, cell, owner)`** (`579-581`) — Sets
  `cell.owners = {owner: 1.0}` (100% single ownership) and stamps
  `lastHarvestedTimestep` to the current timestep. The ownership-establishing
  primitive, used when a cell is first claimed. Does **not** touch
  `pendingViolations` — a trespass against a *prior* epoch's owner is still
  owed to that owner (see `convertViolationsToDebts`, which credits the
  snapshotted owner, not the current one), so wiping the list here would
  erase a legitimate outstanding claim whenever a decayed cell is re-taken.
  *Locke, Sect. 32: "As much land as a man tills, plants, improves, cultivates, and can use the product of, so much is his property. He by his labour does, as it were, inclose it from the common."*
- **`forfeitCellClaim(self, cell)`** (`583-585`) — The inverse of
  `claimCellFor`: wipes `cell.owners` back to `{}` and resets
  `lastHarvestedTimestep` to `-1`. Leaves
  `pendingViolations` in place for the same reason as `claimCellFor` — the
  wronged prior owner may still recover the debt if they (or anyone) re-touch
  the cell.
  *Locke, Sect. 38: "if either the grass of his enclosure rotted on the ground, or the fruit of his planting perished without gathering... this part of the earth, notwithstanding his enclosure, was still to be looked on as waste, and might be the possession of any other."*
- **`convertViolationsToDebts(self, cell, timestep)`** (`587-624`) — For
  every pending violation on the cell, splits the stolen `amount` across the
  owners **snapshotted at trespass time** (`violation["owners"]`, falling back
  to current owners for pre-snapshot records) proportional to share, **scaled
  by a reparation rate above parity** — the crediting owner's `governmentRate`,
  or `min(choices)` from `environmentLandReparationRateChoices` for an owner
  not in a government. Skips any snapshotted owner who is the trespasser or is
  no longer alive. Creates one debt record per (owner, trespasser) pair
  (`creditor`, `debtor`, `cell`, `amount`, `createdTimestep`, and
  `executorRecognized` — `False` until an executor's collection pass adjudicates
  it, see `doForcefulDebtCollection`), files
  it on both the creditor's `debtsReceivable` and the debtor's `landDebtsOwed`,
  resets that owner's trust in the trespasser (moment of discovery), then
  clears `pendingViolations`.
  *Locke, Sect. 10: "he who hath received any damage, has... a particular right to seek reparation from him that has done it." Sect. 11 grounds crediting the owner *at the time of the wrong*, not the current claimant — reparation runs offender → injured party, so a decayed-and-re-taken cell must not book a debt against (or, if the re-claimant is the original trespasser, to) the wrong agent. Sect. 12 grounds sizing the debt above parity: the penalty must be "sufficient to make it an ill bargain to the offender" — a net-zero return costs the trespasser nothing. Sect. 11 also grounds the owner trust reset here: the injured party learns of the trespass when it lands on the ledger, wherever they stood when it happened (see `resetTrustIn`).*
- **`removeSettledDebt(self, debt)`** (`610-617`) — Removes one fully-paid
  or otherwise-discharged debt from both the creditor's `debtsReceivable`
  and the debtor's `landDebtsOwed` lists.
  *Design choice — ledger cleanup once reparation (Sect. 10) has already been satisfied; no distinct textual basis of its own.*
- **`acquireLandClaim(self, cell)`** (`654-658`) — Thin wrapper calling
  `claimCellFor(cell, self)` and appending the cell to
  `self.locke["claims"]` — the actual "claim this cell" action, reached from
  `collectResourcesAtCell` only after a non-zero harvest.
  *Locke, Sect. 27/28: property is made from what a man "removes out of the state that nature hath provided" — "that labour... added something to them more than nature... and so they became his private right." No removal, no claim; the harvest gate in `collectResourcesAtCell` is what enforces this.*
- **`collectResourcesAtCell(self)`** (`656-669`) — Override of the base
  harvesting method. Captures `cell.sugar` and `cell.spice` separately
  **before** `super().collectResourcesAtCell()` (the parent zeroes the
  cell at the end, so the amounts can't be read afterwards), records
  their sum as `self.locke["lastHarvest"]` every timestep — before the
  gate, so a no-harvest timestep records `0.0` and is not levied on a
  stale value — then calls `recordLandTrespassIfOwned(sugarCollected,
  spiceCollected)` with the same snapshotted amounts (the snapshot is
  needed because `super()` zeroes the cell), **unconditionally** (even on
  a zero harvest, matching this call's behavior from when it lived in
  `agent.py` — see that method's own entry). Then it **returns
  immediately if nothing was harvested**. Only on a non-zero harvest
  does it dispatch: claim an unclaimed cell if `self` is currently below
  `environmentLandMaxClaimsPerAgent` **and** `leavesEnoughForNeighbors`
  says the proviso is satisfied — both conditions, not either — or, if
  `self` is already an owner, call `processReturnToOwnedLand`. The cap
  check runs first (cheaper to evaluate than the proviso, which scans
  every cell-adjacent neighbor's own vision range) but either one alone
  blocks the claim; an agent already at its cap is not stopped from
  gathering here, only from *claiming* it — the harvest itself, and the
  spoilage-proviso consequences of one already at the cap, are
  unaffected. **Fixed finding**: before the cap existed, a single agent
  could accumulate many scattered claims over its lifetime with nothing
  bounding how many — an empirical trace found individual agents holding
  up to 12 simultaneous claims, with the population average climbing
  toward 7-8 within the first 30 timesteps of a typical run. A decisive
  ablation (disabling claim acquisition outright, leaving every other
  Locke mechanic active) dropped a 30-seed extinction rate from 94% to
  17% — *below* the `"none"`-model baseline of 45% — isolating
  unconstrained property accumulation, not any of the other mechanics, as
  the dominant driver of Locke's excess mortality relative to a no-ethics
  population. Capping accumulation per agent, rather than removing
  claiming outright, is the version of that finding that keeps exclusive
  property itself intact.
  *Locke, Sect. 27 (claim creation) and Sect. 38 (claim retention) both key on gathering, not presence — "if... the fruit of his planting perished without gathering... this part of the earth, notwithstanding his enclosure, was still to be looked on as waste." Standing on a depleted cell is not gathering, so it neither creates nor refreshes a claim. Sect. 36 grounds the cap itself: "no man's labour could subdue, or appropriate all; nor could his enjoyment consume more than a small part; so that it was impossible for any man, this way, to intrench upon the right of another" — Locke's own argument for why unbounded appropriation shouldn't happen is that one person's labor and consumption naturally can't stretch that far; a hard cap makes that boundary explicit in a model where an agent's vision, movement, and lifespan let it wander far past what it could plausibly use. The specific cap value is a design choice — Locke names no number, only the qualitative bound. The dispatch targets each carry their own further citation.*
- **`leavesEnoughForNeighbors(self, cell)`** (`673-680`) — The "enough, and
  as good" proviso check gating claim creation. Requires an unclaimed
  alternative (other than `cell` itself, since the check runs *before*
  `cell` is claimed and would otherwise still read as unclaimed) within
  **both** `self`'s own vision-and-movement range (`findCellsInRange`,
  capped by whichever is smaller) **and** every cell-adjacent neighbor's
  own range (`neighbor.findCellsInRange()`, computed from *their* current
  cell, unaffected by `self`'s hypothetical claim). If any one of them —
  `self` included — would be left with nothing else reachable, the claim
  is refused and the harvest still happened (Sect. 38's gathering already
  occurred) but creates no new exclusion. **Fixed finding, replacing a
  self-only check**: the original implementation asked only whether
  `self` had an unclaimed alternative nearby, never whether the claim
  would leave a neighbor boxed in. A 100-seed run of `config.json`'s
  pure-`"locke"` population (with the era's `findEthicalValueOfCell`
  foreign-land valuation fix already applied) still showed the large majority of seeds going
  extinct well before timestep 500, while a matched `"none"`-model
  baseline over the identical seeds went extinct in less than half as
  many; a decisive ablation — disabling claim acquisition outright while
  leaving every other Locke mechanic (trust, government, the levy, debt
  collection) active — dropped the extinction rate *below* the `"none"`
  baseline, isolating property exclusion itself, not any of those other
  mechanics, as the dominant cause. That result sits in real tension with
  Locke's own claim: Sect. 37 argues enclosure "does not lessen but
  increase the common stock of mankind," not shrink the population able
  to live off it — a self-only proviso check licenses claiming almost
  anywhere as long as the claimant personally has *some* unclaimed
  fallback, which let the map fragment into a fine patchwork (roughly a
  third of all cells claimed within the first 10 timesteps of a typical
  run) long before land was actually scarce for the population as a
  whole, walling off far more forageable land than a genuine "enough and
  as good left for others" test would ever license. Checking every
  adjacent neighbor's own range, not just the claimant's, is a much
  closer reading of "for others" specifically. See the verification
  section of this change for the full before/after seed comparison.
  *Locke, Sect. 27: property claiming is licensed "at least where there is enough, and as good left in common for others" — the clause is explicitly about the position of others, not solely the claimant's own remaining options, which is exactly what the self-only version missed. Sect. 33 restates the same qualifier ("as good left, as before"). Cell-adjacency as the "who counts as an affected other" boundary, and each such neighbor's own vision-and-movement range as the measure of "enough... left," are both design choices — Locke names no radius or population for either; the choice mirrors the same range concept `findCellsInRange` already uses for the claimant, so the same standard applies whether asking "is this too little for me" or "is this too little for someone else."*
- **`processReturnToOwnedLand(self, cell)`** (`679-683`) — Re-stamps
  `lastHarvestedTimestep` and calls `convertViolationsToDebts` — the "owner
  comes back and gathers from land that was stolen from" moment. Only reached
  after a non-zero harvest (see `collectResourcesAtCell`), so an owner parked
  on an exhausted cell no longer holds the claim against `processLandAbandonment`.
  *Design choice — the specific "wait until the owner returns" timing is invented; the reparation right it triggers is grounded in Sect. 10, and the harvest gate in Sect. 38 (see `collectResourcesAtCell`). Consequence: pending violations on a claim the owner only ever revisits without gathering are not booked until someone next harvests the cell (still credited to the snapshotted victim via `convertViolationsToDebts`), or are lost if the claim decays first — consistent with an abandoning owner forfeiting the claim going forward.*
- **Removed: `doLandConsentGrants(self)`.** Let an owner voluntarily
  grant a cell-adjacent, sufficiently-trusted neighbor (below their own
  `environmentLandMaxClaimsPerAgent` cap) co-ownership of a claim that had
  gone unharvested for more than half `environmentLandDecayTimesteps` —
  hedging against the claim decaying entirely to non-use, since a
  co-owned cell only decays if *neither* owner ever tends it. Grounded in
  Sect. 28 (an owner's standing to dispose of what's his by consent) and
  Sect. 38 (the same spoilage risk `processLandAbandonment` enforces),
  with the split ratio and trigger point both flagged as design choices.
  **Removed by request.** Co-ownership itself survives: `doInheritance`
  still creates multi-owner cells by splitting a deceased owner's claim
  among their living Locke children, and `processLandAbandonment`'s "a
  co-owned claim doesn't decay while any one owner tends it" behavior is
  unchanged — only the voluntary, trust-based path to *creating* that
  co-ownership is gone. This mechanic was part of the "combined
  verification" 100-seed run recorded under `collectResourcesAtCell`'s
  claims-cap finding; that run's headline result (the per-agent claims
  cap as the dominant survival lever) is unaffected by removing this
  ancillary piece.
- **`processLandAbandonment(self)`** (`715-729`) — Runs every timestep for
  every claim the agent holds; forfeits any cell the *owner* hasn't
  harvested in `environmentLandDecayTimesteps` steps, otherwise keeps it in
  the agent's claims list. A trespasser harvesting the
  cell does not reset this clock (see `recordLandTrespassIfOwned` above)
  — a claim under continuous theft still decays; a
  claim under **co-ownership** does not, as long as any one owner tends
  it (co-ownership now arises only through `doInheritance`, see below).
  *Locke, Sect. 38 (see `forfeitCellClaim` above) grounds losing land through non-use; the specific numeric timestep threshold (`environmentLandDecayTimesteps`) is a design choice — Locke never puts a number on it.*
- **`settleDebtsVoluntarily(self)`** (`672-693`) — Runs every timestep; for
  every debt the agent owes, pays down as much as it can from sugar/spice
  above its own metabolic need (sugar first, then spice), removing the debt
  once fully paid. No proximity requirement.
  *Locke, Sect. 37: "the intrinsic value of things... depends only on their usefulness to the life of man," combined with Sect. 47: "And thus came in the use of money, some lasting thing that men might keep without spoiling, and that by mutual consent men would take in exchange for the truly useful, but perishable supports of life." Together these ground value as commensurable across different useful goods, but it's a stretched analogy: Locke's money is valuable specifically because it is NOT one of the perishable staples, whereas sugar and spice here are the staples themselves — the "same nominal value regardless of resource" rule has no tight single-passage match.*
- **`doForcefulDebtCollection(self)`** (`766-813`) — Runs every timestep; for
  every neighboring agent, for every debt that neighbor owes — collectible
  starting the very timestep it's created, no grace period — enforces the
  debt by calling the base engine's `agent.Agent.doSteal(cell, amount)`
  with `amount = debt["amount"]`: the debtor survives, `doSteal` returns
  the actual sugar/spice recovered (capped at what the debtor holds, so a
  poor debtor may only partially satisfy the debt), and the debt's
  `amount` is reduced by exactly that much — `removeSettledDebt` only
  fires once it reaches zero, so an insolvent debtor keeps the remainder
  outstanding for a future attempt. `doSteal` always pays whoever calls
  it, so when `self` isn't the creditor (the executor collecting for a
  fellow member, or an assisting member), the recovered amount is
  forwarded from `self` to the actual `creditor` afterward. **Two prior
  designs superseded, in order**: first, manual `neighbor.sugar -=`/
  `creditor.sugar +=` number manipulation with no attack at all — from the
  debtor's own perspective indistinguishable from theft, nothing the base
  engine recognized as a modeled event; then a version routed through the
  base engine's existing `doCombat(cell)`, reusing engine code with no new
  `agent.py` method, but `doCombat` is unconditionally lethal and its loot
  is capped by `maxCombatLoot`, not the debt — every collection killed the
  debtor regardless of how small the debt was, which is a poor fit for
  Sect. 12's proportionality ("sufficient to make it an ill bargain...
  give him cause to repent"). `doSteal` is new, minimal `agent.py` code
  (`agent.py:300-311`, mirroring `doCombat`'s structure but parameterized
  by `amount` instead of a flat environment-wide cap, no `doDeath` call,
  no `gotoCell` relocation since the victim is still occupying the cell)
  written specifically to fix this: it makes enforcement a real, modeled
  event like `doCombat` does, while letting the caller decide how much to
  take and leaving the target alive — the closest fit yet to Sect. 12's
  actual proportionality reading. Written generically (no debt-awareness,
  no `Locke` reference) so any decision model could reuse it, matching how
  `doCombat` itself is written for any aggressive agent, not one decision
  model. The gate, in order: **`self` is the creditor** (ungated self-help);
  or **`self` is one of its government's `governmentExecutor` set and the
  creditor is a fellow member**; or — new — **`self` is a non-executor
  member, the creditor is a fellow member, the government has at least one
  sitting executor, and the debt is already flagged `executorRecognized`**.
  Anything else does nothing; a governmentless agent still collects only
  its own. **Recognition**: whenever any executor's own pass reaches a debt
  it is entitled to collect (its own, if it is the executor; or any fellow
  member's), it stamps
  `debt["executorRecognized"] = True` — the executive's adjudication that this
  is a valid society debt to enforce — whether or not it can seize anything that
  step (the debtor may be momentarily empty). The executor only encounters
  debts of agents adjacent to it, so recognition spreads as it moves; the flag,
  once set, persists on the debt record until the debt is settled. When a
  steal lands on a `Locke` debtor its `restrained` flag is set (Sect. 12)
  — **restored** after being removed as dead code during the brief
  `doCombat`-based design above, since a debtor who survives collection is
  exactly the scenario this flag exists for; see `findEthicalValueOfCell`'s
  entry for what it does.
  **Partiality**: immediately after any executor successfully seizes on its
  *own* debt, it checks every other government member for a debt
  receivable of their own that is already collectible (alive and solvent
  debtor) but hasn't been reached — for each such member found, it
  accrues `environmentLandExecutorPartialityPenalty` to *that member's*
  ordinary `grievance` (the same field the levy's `"proportional"` wrong
  feeds, not `executorGrievance`, which is replacement-only). An executor
  serving itself while a fellow member visibly waits is evidence of power
  used for private advantage, not mere delay — it is graver than the
  `doGovernanceReview` neglect channel's passive "hasn't reached it yet"
  reading of the same debt, though both now use the identical, gate-free
  collectibility test. **Fixed finding**: this and the two sites below
  used to gate on `environmentLandForcefulCollectionGraceTimesteps` (and,
  for the neglect channel specifically, an additional
  `environmentLandExecutorNeglectGraceTimesteps` window on top) — a
  minimum age a debt had to reach before any of this could fire at all.
  Both keys were already documented as a pure, ungrounded design choice
  (no textual basis for *any* waiting period). Removing them entirely — a
  debt is now collectible, pursuable, and countable-as-neglected starting
  the instant it exists — measurably improved survival on a 20-seed
  sample of `config.json`'s pure-`"locke"` population: 13/20 survived
  with the grace windows in place, 16/20 survived with them removed, at
  timestep 500. Faster, more certain enforcement keeps less wealth tied
  up in unresolved trespass debt during the population's fragile early
  window.
  **`doSteal` redesign, verified**: scratch tests confirm `doSteal` itself
  (unit-tested directly: caps loot at the requested `amount` and at what
  the target actually holds, transfers to the caller, never kills, never
  relocates the caller) and `doForcefulDebtCollection`'s use of it (a full
  recovery discharges the debt and sets `restrained`; a partial recovery —
  debtor has less than owed — leaves the remainder outstanding and does
  *not* call `removeSettledDebt`). A 25-seed same-seed sample of
  `config.json`'s pure-`"locke"` population found 18/25 survived at
  timestep 500 (28% extinct) — the low end of, not outside, the 28-40%
  extinction band already established for this method's prior versions
  across several same-seed reruns this session (see `CLAUDE.md`'s
  methodological note on single-seed noise: this simulation is not
  reproducible run-to-run even for byte-identical code, so no version of
  this method has ever been shown to differ from another by more than
  that noise band). Not verified against a mixed `["locke", "none"]`
  population specifically for this change, since `recordLandTrespassIfOwned`
  being `Locke`-only (see its own entry) already means debts, and
  therefore this method, never touch non-`Locke` agents at all.
  *Sect. 19 grounds why self-help force is legitimate at all — there is no common judge/magistracy to appeal to. Sect. 12 grounds the cap: "sufficient to make it an ill bargain to the offender" — `doSteal`'s `amount` parameter lets the caller honor this literally (recover up to what's owed, no more), unlike the `doCombat`-based version this superseded, whose flat `maxCombatLoot` cap and mandatory killing had no relationship to the actual debt. Sect. 11 grounds the ungated **self**-collection: the injured party's right to reparation is gated by nothing. Sect. 126 grounds the appointment itself — the state of nature "wants power... to give [the sentence] due execution", so the society names an executor. Sect. 130 grounds a member assisting at all — on entering society he "engages his natural force... to assist the executive power of the society, as the law thereof shall require", the opposite of freelancing. Sect. 88 grounds gating that assistance on the executor's recognition: the member "has given a right to the common-wealth to employ his force, for the execution of the judgments of the common-wealth, whenever he shall be called to it" — the force executes a judgment already made, not the member's "own private judgment", which Sect. 88 says he "has thereby quitted"; an unrecognized debt has no such judgment for the member to execute, so acting on it would be the Sect. 125 wrong of being judge in one's own society's cause with no indifferent judge. The `executorRecognized` flag is that judgment made concrete; requiring the executor to have physically reached the debt to make it is design-choice plumbing. An earlier "member-visible ledger" version let every member collect for every fellow member on their own initiative; the executor plus this recognition gate supersedes it (Sect. 130/88's step Locke actually describes). The partiality grievance is Sect. 199: the executor exercising its enforcement power "to his own private separate advantage" — the same citation already grounding `"proportional"` redistribution's wrong in `runLevyPass`, feeding the same rebellion pathway (Sect. 240) rather than a new one. Penalizing every currently-neglected member per occurrence, rather than a single representative case, is a design choice. No grace period gates any of this: Locke gives reparation no waiting period (Sect. 12/19), so instant enforcement is, if anything, the more literal reading, not a departure from one.*
- **`doTrustAccrual(self)`** (`793-806`) — Runs every timestep for every
  cell the agent owns; every neighbor of that cell who is alive, not a
  co-owner, and didn't trespass on it *this* timestep earns one trust point
  from the owner (via `increaseTrust`) — the literal complement of the
  trespass check `recordLandTrespassIfOwned` already performs,
  reusing the same `cellPendingViolations`/`findNeighborAgents` primitives
  rather than re-scanning adjacency separately.
  *Design choice — no textual analog for a quantified trust-building period; Locke never describes trust or reputation being built up numerically before political society forms.*
- **`increaseTrust(self, candidate, cell)`** (`735-739`) — Increments
  `self.locke["trust"][candidate.ID]` by 1, and — only if
  `candidate` is itself a `Locke` instance — checks whether this increment
  just completed mutual threshold-crossing (`attemptGovernmentFormation`).
  The `isinstance(candidate, Locke)` check here is also what satisfies
  "exclusion follows from incapacity to consent, not discrimination": a
  non-`Locke` agent simply has no `.locke` dict to reciprocate through, so
  it's structurally never reachable past this point — no
  characteristic-based check (race/sex/tribe/tag) exists anywhere in this
  path.
  *Design choice for the mechanic itself; the exclusion principle above is Locke, Sect. 60's logic (exclusion from full agency grounded in incapacity — "lunatics and ideots are never set free... but continued under the tuition... of others, all the time their own understanding is uncapable") applied here to consent rather than reason.*
- **`attemptGovernmentFormation(self, other)`** (`892-926`) — Called from
  `increaseTrust` with `self` = the agent whose trust toward `other` just
  crossed its own `trustThreshold`. Returns early if that threshold isn't met.
  Then: if `self` is already in a government, does nothing (one at a time). If
  `other` is in a government, `self` joins it (`addToGovernment`) on its own
  consent alone. Otherwise, only if `other`'s trust toward `self` has also
  crossed `other`'s threshold, founds a new government — a bare `set()` — and
  votes **six** laws over the founders, in order: `voteGovernmentForm`
  (democracy or restricted — resolved to `"monarchy"`/`"oligarchy"` by
  `environmentLandLegislatureSize`, or forced to `"democracy"` outright
  when that config is `"all"`), then `findLegislature` picks who
  actually gets a say in the rest; only then `voteReparationRate` (the
  reparation multiplier),
  `voteRedistribution` (equal/proportional, judged against the
  *whole* founding pair regardless of who's voting), `voteExecutor` (who
  collects on the society's behalf), `votePayFraction` (what the
  executor(s) are paid from the levy), and `voteLevyFraction` (the levy
  rate itself, judged against the whole founding pair the same way
  `voteRedistribution` is) are all cast by `legislature`, not
  necessarily both founders. Every founder still gets every resulting
  value written to their `locke` dict regardless of whether they were in
  the legislature that decided it — non-legislature members are bound
  subjects, not voters. Sets `lastLegislativeReviewTimestep` to the
  founding timestep so the first scheduled reconvening doesn't fire
  immediately. Zeros both founders' `grievance`, `executorGrievance`,
  and (implicitly, via `__init__`'s default) `legislatureGrievance`.
  *Locke, Sect. 95-99 grounds forming political society by mutual consent — "when any number of men have so consented to make one community or government, they are thereby presently incorporated" — and is why a government is a bare `set()`, not a class: nothing more than its members' collected consent. Sect. 99 grounds the bilateral requirement for **founding** (each founder consents); Sect. 89 grounds **joining** an existing body on the joiner's consent alone ("men being... by nature all free, equal, and independent, no one can be... subjected to the political power of another, without his own consent"). The one-government-at-a-time rule is a design choice — Sect. 121 is about a tacit consenter's freedom to leave versus an express consenter's binding, not about exclusivity. Binding non-legislature founders to laws they didn't vote on is the same Sect. 97 logic that already binds ordinary joiners.*
- **`voteGovernmentForm(self, founders)`** (`938-945`) — The Sect. 132
  founding law: a binary vote (`"democracy"` or `"restricted"`) over the
  two founders. Each founder's own preference is keyed to an *absolute*
  stake threshold — `environmentLandReparationStakeReference`, the same
  constant `voteReparationRate` compares against — not to which founder
  holds relatively more than the other: a founder whose own claim count is
  at or above that reference prefers `"restricted"`, below it prefers
  `"democracy"`. The government adopts the median of the two picks
  (favoring `"democracy"` on disagreement, same tie-break direction as
  every other menu vote), so `"restricted"` only wins when **both**
  founders are independently landed. A *relative* preference rule (whoever
  of the two holds more land) was considered and rejected: with exactly
  two founders one is always relatively dominant, so a relative rule would
  resolve every disagreement to the same label every time, making the
  other label permanently unreachable. Reusing the founders' land
  stake against a fixed reference avoids that.
  *Locke, Sect. 132 names all three forms as legitimate outcomes of the majority's founding choice ("may place [legislative power]... into the hands of a few select men... or else into the hands of one man... and this is a democracy, oligarchy, or a monarchy") without ranking them or supplying a decision procedure — §107 (custom) and §110 (choosing "the wisest and bravest") both describe historical drift toward monarchy but neither is mechanizable as a per-founder preference rule. Keying preference to accumulated stake is a design choice — the same stake-driven self-interest logic already used for `voteReparationRate`'s harshness scaling and `votePayFraction`'s role-conditioning, extended here to a Sect. 132 decision Locke leaves procedurally open. This vote is only ever cast by the two founders and never re-run (see "Permanence" in `reviewLegislature`'s note below) — see PROPERTY.md's phase notes for the two known consequences of that: founding legislatures are behaviorally identical between `"restricted"` and `"democracy"` whenever `environmentLandLegislatureSize ≥ 2` (top-K selection caps at the 2 founders regardless of K), and the founding-form split is expected to skew heavily toward one label rather than balance.*
- **`findLegislature(self, members, form)`** (`947-953`) — Returns
  `frozenset(members)` for `"democracy"`; otherwise sorts `members`
  descending by `(len(claims), -member.ID)` — same clamp-and-slice shape
  as `voteExecutor`, keyed on land stake instead of reach — and returns
  the top `environmentLandLegislatureSize` (clamped to
  `[1, len(members)]`). One mechanism produces both oligarchy (`K > 1`)
  and monarchy (`K = 1`); nothing distinguishes how a monarch is chosen
  from how an oligarchy's members are chosen beyond the configured count.
  *Locke, Sect. 132's "few select men" and "one man" are both instances of the same underlying "who holds legislative power" question — treating monarchy as oligarchy-at-K=1 rather than inventing a separate selection rule is a design choice, since the text doesn't describe a selection mechanism for either.*
- **`reviewLegislature(self, government)`** (`955-969`) — Mirrors
  `reviewExecutor`'s structure exactly: guard on `len(list(government)) <
  2` (total government size — a legislature of size 1 under monarchy is
  the intended steady state, not a viability problem, so the guard must
  not be on the legislature's own size), recompute via `findLegislature`,
  compare by value, write to every member, debug-print on change. Called
  at every site `reviewExecutor` is (`addToGovernment`, `doInheritance`'s
  survivor block, both `doGovernanceReview` branches), and always
  **before** `reviewRedistribution`/`reviewExecutor`/`reviewExecutorPay`
  at each of those sites, since all three now read `governmentLegislature`
  rather than full membership. `governmentForm` itself is never
  re-examined here or anywhere else — only *who* currently holds the
  power the form grants can change.
  *Design choice — pure call-sequencing and selection-recomputation plumbing; the substantive content (who holds power, and that it can shift as circumstances change) is grounded in `findLegislature` and `voteGovernmentForm` above.*
- **`findQuantileChoice(self, member, choices, referenceGroup)` /
  `voteByQuantileBracket(self, voters, choices, referenceGroup)`**
  (`857-873`) — Shared mechanism now behind both `voteReparationRate` and
  `voteLevyFraction`. Sorts `referenceGroup`'s claims and computes, for
  each of the `len(choices)-1` boundaries, a breakpoint at the
  corresponding fractional rank (`k/len(choices)` of the way through the
  sorted reference claims, linearly interpolated between the two nearest
  values when that position doesn't land exactly on one — the same
  technique `numpy.percentile`'s default interpolation uses, not naive
  index rounding). Each `voter`'s own claims are looked up against those
  breakpoints for their one preferred choice; the government adopts the
  median of all voters' preferred choices (lower-of-tie).
  *Design choice — the quantile-ranking mechanism itself has no textual analog; Locke never specifies a menu-vote procedure. It generalizes the "compare stake to something, pick a menu entry" shape every earlier menu vote in this file already used, but ranks each voter against an actual population's distribution rather than a fixed external number.*
- **`voteReparationRate(self, founders)`** (`875-878`) — Calls
  `voteByQuantileBracket(founders, choices, founders)` — the founders are
  both the voters and their own reference population, since no larger
  group exists yet at founding. Stored as `governmentRate`.
  **A real consequence, found while testing this change**: because the
  reference group is always just the two founders, and quantile ranking
  is purely relative, two founders with *equal* claims — whether that's
  1 each or 1000 each — always land on the mildest choice; there is no
  variance within the reference group left to rank against, so no signal
  about either founder's *absolute* holdings survives. This is a real
  change from the previous absolute-reference mechanism (which scaled
  with holdings regardless of the co-founder), documented here rather
  than patched — consistent with this file's practice of reporting real
  degeneracies (the K≥2 founding-legislature finding under
  `voteGovernmentForm`, the milder-wins tie-break every menu vote shares)
  rather than re-engineering around every one.
  *Locke, Sect. 12 gives only a floor ("an ill bargain"), not a number, so the rate is set by collective decision. Sect. 95-96: one equal vote each, the body moving "whither the greater force carries it, which is the consent of the majority" — hence the median. Sect. 138 grounds keying the preference to holdings, though under this mechanism that's now relative standing within the founding pair, not absolute holdings. The choice menu remains a design choice; `environmentLandReparationStakeReference` no longer grounds this vote specifically (see that key's README entry — it now grounds only `voteGovernmentForm`).*
- **Removed: `voteLandUse(self, members)`.** Was one of the founding
  votes: a single vote over a menu of `"closed"` or a per-harvest toll
  fraction, setting `governmentLandUse` — the standing rule (Sect.
  119/124) binding non-members in the territory. **Removed by request,
  along with the whole toll/`"closed"` concept.** The problem it had:
  keyed purely to a member's own claim count (bigger landholder → more
  exclusion), the vote's practical meaning had collapsed into a proxy
  for government size rather than the actual Lockean question of whether
  compensated access beats total exclusion. Rather than redesign the
  vote's inputs, the toll mechanic is gone entirely: every non-owner
  harvest on owned land is now a trespass generating a reparation debt at
  the owner's `governmentRate` (unchanged — `convertViolationsToDebts`),
  collectible via the existing executor/`doSteal` machinery and payable
  after the fact via `settleDebtsVoluntarily` — which is the compensated
  access "toll" used to provide, just always retrospective rather than
  paid up front. `governmentLandUse` and `environmentLandUseChoices` are
  removed from all plumbing.
- **`voteRedistribution(self, votingMembers, allMembers)`** (`1052-1055`) —
  The contested law: how the per-timestep levy is paid back out. The
  comparison mean is computed over `allMembers` — the *whole* government,
  not just whoever is voting — and each member of `votingMembers` votes
  `"proportional"` if their **own** claims strictly exceed that mean,
  `"equal"` otherwise; majority, tie → `"equal"`. Re-voted whenever the
  roster changes (`addToGovernment`, `doInheritance`) or grievance forces
  a review — the one of the three legislature-scoped laws with its own
  extra wrinkle: judging a legislator against the body it governs, not
  against the (possibly much smaller) legislature casting the vote, is
  what makes the vote meaningful once `governmentForm` is
  `"oligarchy"`/`"monarchy"` — comparing a legislature against its own
  mean would make a size-1 legislature's vote a mathematical certainty
  (a lone member's claims always equal a mean computed over just
  themselves), which would test the selection rule, not Sect. 138. Under
  `"democracy"`, `votingMembers` and `allMembers` are the same collection
  by construction, so this is provably identical to the pre-Phase-5
  formula.
  *Locke, Sect. 138/139: "the supreme power cannot take from any man any part of his property without his own consent" — the levy is exactly that, a taking the aggrieved minority did not consent to. `"equal"` returns each member its own levy (the power held, not abused); `"proportional"` moves value from the land-poor to the land-rich — Sect. 199, power "to his own private separate advantage." So this is Lockean not as legitimate legislation (Sect. 140 taxation funds operations; this funds nothing) but as the wrong of Sect. 222 ("they endeavour to take away, and destroy the property of the people"), which forfeits trust and licenses withdrawal (Sect. 240). Comparing the legislator against the whole governed body is the textually precise reading of Sect. 138's actual worry — a legislature "variable" or not, "having a distinct interest from the rest of the community" is exactly "holds more than the community it governs, on average"; the legislature's own internal mean cannot measure that once the legislature is a strict subset. The mean-relative vote and the whole levy amount remain design choices.*
- **`voteExecutor(self, members)`** (`960-964`) — The fourth of six founding
  laws (Sect. 126). Preference does **not** track landholding — §126's defect is
  inability to *reach* the transgressor, so the pick is the top
  `environmentLandExecutorCount` members (clamped to at least 1, at most
  `len(members)`) ranked by reach = `findVision() + findMovement()`, ties
  broken by lowest ID, returned as a `frozenset`. Because reach is an
  objective shared fact the ballot is degenerate (every member ranks the
  same members in the same order) and it reduces to an arg-top-N — kept in
  vote form for parity with the others, noted here. At the default
  count of `1` this is exactly the single-executor argmax the mechanic
  originally shipped with.
  *Locke, Sect. 126 grounds the appointment (the state of nature "wants power... to give [the sentence] due execution"). Sect. 152 grounds its being an office, replaceable "at pleasure", not a right — hence the deterministic tie-break rather than a natural entitlement. The vision+movement metric is a design choice standing in for "capacity to execute a judgment on a distant party." Sect. 126 establishes that an executive power must exist, not how many people hold it — the count itself is a design choice, hence configurable.*
- **`votePayFraction(self, members, executor)`** (`980-985`) — The fifth
  founding law: how much of the levy pool the executor(s) are paid, one
  entry from `environmentLandExecutorPayChoices`. Unlike the other menu
  votes (`voteReparationRate`), preference here isn't
  stake-scaled — it's purely role-based: a member currently *in* `executor`
  prefers the highest choice on the menu, everyone else prefers the lowest.
  The government adopts the median (lower of the two middle choices on a
  tie), matching every other vote's tie-break direction. Because preference
  depends entirely on executor membership, outcomes are majority-driven by
  government *size*: with `environmentLandExecutorCount` fixed, a small
  government (executors are a majority of it) votes high pay; a large one
  (executors are a minority) votes low; an exact tie favors low. `executor`
  is passed in explicitly rather than read from `self.locke` because at
  founding it isn't stored on the founders yet when this vote runs.
  *Sect. 140: "it is fit every one who enjoys his share of the protection, should pay out of his estate his proportion for the maintenance of it" — a purpose (funding the Sect. 126 office) and majority consent (the vote itself) make this legitimate taxation, unlike the ordinary levy. But Locke never discusses executive compensation, and gives no basis for who should prefer what rate — the role-based preference rule (executor wants more, everyone else wants less) is this codebase's own construction, not textual, placed here as underdetermined. Executors voting themselves a raise is Sect. 199's "private separate advantage" in the most literal form the model has; whether that's an abuse depends on where the outcome lands relative to `environmentLandExecutorMaintenanceFraction` (see `runLevyPass` below).*
- **`addToGovernment(self, government, newMember)`** (`990-1006`) — Adds
  `newMember` to the shared `set()`, points their `locke["government"]` at it,
  copies every standing government-law field onto them verbatim —
  `governmentRate` / `governmentRedistribution` /
  `governmentExecutor` / `governmentExecutorPay` / `governmentForm` /
  `governmentLegislature` / `governmentLevyFraction` /
  `lastLegislativeReviewTimestep` — zeros their `grievance` and
  `executorGrievance` (`legislatureGrievance` already defaults to `0.0` in
  `__init__`). **Does not** trigger any review immediately (a Phase 6
  change — it used to call `reviewLegislature`/`reviewRedistribution`/
  `reviewExecutor`/`reviewExecutorPay` right here): the joiner simply
  waits, bound by the standing laws, for the next scheduled or
  legislature-grievance-forced reconvening in `doGovernanceReview` like
  every other member — a join is no longer itself an occasion.
  *Locke, Sect. 97 grounds binding the joiner to the standing laws without a re-founding: consenting to incorporate "puts himself under an obligation... to submit to the determination of the majority." (Not Sect. 122 — that is about tacit compliance not conferring membership.) Sect. 153's "not necessary... that the legislative should be always in being" grounds not treating an ordinary join as its own occasion — real legislatures reconvene on a schedule, not continuously in response to every incremental change in membership.*
- **`reviewRedistribution(self, government)`** (`1101-1112`) — Re-runs
  `voteRedistribution` — the vote itself is cast by `governmentLegislature`,
  judged against the *whole* `government` (the fix described under
  `voteRedistribution` above); if the rule changed, writes it to every
  member and returns `True`. A no-op if the land-rich/land-poor balance
  among the legislature (relative to the whole body) is unchanged — so
  under a stable roster and holdings, `"proportional"` persists and
  grievance climbs to withdrawal (Sect. 222–243: dissolution, not reform,
  is the remedy for a legislature turned to faction advantage).
  *Sect. 153: "it is not necessary... that the legislative should be always in being" — it meets on occasion; since Phase 6 that occasion is `environmentLandLegislativeReviewInterval`'s schedule or a `legislatureGrievance` threshold, not an ordinary roster change by itself (see `doGovernanceReview`).*
- **`reviewExecutor(self, government)`** (`1015-1024`) — Re-runs
  `voteExecutor` over `governmentLegislature`, not full membership — under
  `"restricted"` forms, only the legislature gets a say in who executes,
  even though the executor (once chosen) still acts on behalf of the whole
  government per `doForcefulDebtCollection`'s existing entitlement logic.
  Compares the new `frozenset` to the old **by value** (`==`, not `is` —
  `voteExecutor` builds a fresh set every call, so identity would always
  read as changed even when the elected members are unchanged); if the set
  changed, writes it to every member, returns `True`. Returns `False` when
  the sitting executor(s) are still the highest-reach members — the
  maladministration cannot be fixed by replacement, and (per design) the
  government does **not** dissolve over it; the complaint stands. That
  inertness is itself the Sect. 126 finding: a magistracy with no power to
  reach the debtor is the very defect it was appointed to cure.
  *Locke, Sect. 152: the executive is "accountable to [the legislative], and may at pleasure be changed and displaced"; Sect. 153: the legislative resumes power "to punish for any maladministration against the laws." Executive selection being legislature-gated rather than form-independent was a resolved design choice for this phase — Locke's own separation of executive (§126) from legislative (§132) power is at least as compatible with the executor staying whole-membership-elected, but gating it too keeps "who holds power" answered once by `governmentForm` rather than piecemeal per law.*
- **`votePayFraction(self, members, executor)` (`1030-1034`) /
  `reviewExecutorPay(self, government)` (`1037-1050`)** — `members` here is
  `governmentLegislature`, same as every other now-legislature-scoped vote;
  `reviewExecutorPay` mirrors `reviewExecutor`'s structure
  exactly (same `len(members) < 2` guard on total government size, same
  re-vote-and-compare-and-write pattern) and is called at every occasion
  `reviewExecutor` is — a scheduled or legislature-grievance-forced
  reconvening (`doGovernanceReview`), a death (`doInheritance`), or
  post-withdrawal replacement — because executor identity is what
  `votePayFraction`'s preference depends on, so any event that can change
  the executor set (or the legislature's size relative to the executor
  set, which shifts whether executors are a majority *of the legislature*
  now rather than of the whole government) is also an occasion to
  re-vote pay. It runs unconditionally alongside `reviewExecutor` at each
  of those sites, not only when `reviewExecutor` itself reports a change
  — a government that shrinks from 4 to 3 members without an executor
  turnover still flips the executors from a tie to a majority, and the
  pay vote needs the chance to respond to that.
  *Design choice — pure call-sequencing, matching the existing `reviewRedistribution`/`reviewExecutor` pairing at every one of those sites; no distinct textual content beyond what `votePayFraction` and `attemptGovernmentFormation` already ground.*
- **`voteLevyFraction(self, legislature, allMembers)` (`1075-1078`) /
  `reviewLevyFraction(self, government)` (`1080-1091`)** — The seventh
  founding law: calls `voteByQuantileBracket(legislature, choices,
  allMembers)` — voters are the legislature, but the quantile breakpoints
  come from `allMembers` (the whole government), not the legislature.
  This is deliberate and necessary: a monarchy's legislature is always
  exactly one member, and a quantile computed from a single data point is
  meaningless (every breakpoint collapses to that one value, always
  producing the lowest choice regardless of how landed the monarch
  actually is — an inherent property of quantiles over one point, not an
  implementation gap). A government is never smaller than 2 (`len < 2`
  triggers dissolution everywhere already), so `allMembers` is always a
  well-formed reference population — the same fix already applied to
  `voteRedistribution`, judge a small voting body against the population
  it actually governs, not against itself. `reviewLevyFraction` mirrors
  `reviewExecutorPay`'s structure and call sites exactly, storing the
  result as `governmentLevyFraction`, which `runLevyPass` reads directly
  in place of a flat config constant.
  *Sect. 138/140 (see `runLevyPass` above) ground the substance of what's being voted; the quantile mechanism itself is `voteByQuantileBracket`'s, grounded there. That the reference population differs from `voteReparationRate`'s (whole government here, just the founders there) is a design choice forced by the structural difference between a law re-voted across a growing body and one decided once at founding with no larger population yet to reference.*
- **Removed: `territoryGovernmentFor(self, cell)`.** Returned the `set()`
  government of a cell's first governed living owner (else `None`). Its
  only caller was `findEthicalValueOfCell`'s toll/membership branch, which
  is gone (see that entry and `voteLandUse`'s removal above); the new
  expected-cost formula reads a representative owner's government status
  inline instead. Deleted rather than left as dead code.
- **`dissolveGovernmentIfUnviable(self, government)`** (`1226-1242`) — If fewer
  than two members remain, nulls every survivor's
  `government`/`governmentRate`/`governmentRedistribution`/`governmentExecutor`/`governmentExecutorPay`/`governmentForm`/`governmentLegislature`/`governmentLevyFraction`/`lastLegislativeReviewTimestep`,
  zeros their `grievance`, `executorGrievance`, and `legislatureGrievance`,
  clears the set. Trust scores persist. Called from `doInheritance` (death)
  and `doGovernanceReview` (withdrawal).
  *Locke, Sect. 211: a society dissolves when the body "can no longer act as one"; a single member is not a body. The survivor "returning to the state of nature" with its trust intact matches Sect. 211's sequel — dissolved members "are at liberty... by erecting a new legislative."*
- **`runLevyPass(self, government)`** (`1094-1145`) — Once per timestep per
  government (the `lastLevyTimestep` guard makes later members skip; the roster
  is snapshotted so shuffled run-order and any same-timestep withdrawal do not
  change the denominator). Levies a flat per-capita
  `governmentLevyFraction * mean(lastHarvest)` from every member (sugar
  first, then spice, capped at what it holds) into a pool — **every**
  member is taxed regardless of `governmentForm`; only the *payout* below
  differs by form. First, the government's voted `governmentExecutorPay`
  fraction of the pool is paid directly to its executor(s), split evenly
  among them, and removed from the pool. The remainder is redistributed
  the same timestep, and here **democracy and restricted forms diverge**:
  under `"democracy"` (`governmentLegislature == government`), behavior is
  exactly as before this phase — `"equal"` gives each member back its own
  levy scaled down by the same fraction the pool shrank by (net-zero on
  its own under a legitimate executor-pay deduction); `"proportional"`
  gives `remainingPool * (its claims / total claims)`. Under a
  **restricted** form, any member *not* in `governmentLegislature` gets
  `0.0` regardless of rule — the whole `remainingPool`, built from every
  member's contribution including excluded subjects', is split only among
  the legislature: evenly under `"equal"` (no longer "get your own money
  back" once a subject's contribution is never refunded to anyone in
  particular — the legislature splits the *whole* pool amongst itself),
  by claims share among the legislature under `"proportional"`. Then
  `grievance = max(0.0, grievance - (received - fairBaseline))` per
  member, where `fairBaseline` is what an `"equal"` split of the
  *post-pay* pool would have given that member under democracy's
  formula — an excluded subject's `received` of `0.0` against a positive
  `fairBaseline` makes this the same formula *increase* grievance sharply,
  the mechanism was already bidirectional, just never exercised toward
  total exclusion before this phase. Separately, an excluded member also
  accrues `environmentLandLegislatureGrievancePenalty` to
  `legislatureGrievance` every timestep it's excluded — a third,
  independent channel (see `doGovernanceReview`) that forces an early
  reconvening rather than feeding withdrawal. **Also separately**,
  whatever `governmentExecutorPay` exceeds
  `environmentLandExecutorMaintenanceFraction` is charged again as
  `excess`, and every member's `grievance` (executors included) increases
  by `excess * (its own contribution / pool)`; at or below the
  maintenance line, `excess` is `0` and nothing accrues.
  *Sect. 138 (the taking); Sect. 199 (the `"proportional"` concentration, and now the restricted-form exclusion itself — a legislature "having a distinct interest from the rest of the community" in its starkest form, keeping the whole pool while subjects are still taxed). The flat per-capita basis is chosen so `"proportional"` concentrates toward the land-rich by construction, independent of any harvest/claims correlation. The executor-pay cut itself is Sect. 140 up to the maintenance line: "it is fit every one who enjoys his share of the protection, should pay out of his estate his proportion for the maintenance of it" — a purpose (funding the Sect. 126 office) and majority consent (`votePayFraction`), unlike the ordinary levy which funds nothing and is Lockean only as the Sect. 222 wrong. Past that line the same payment stops being maintenance and becomes Sect. 138's "any part of his property without his own consent" again. `environmentLandExecutorMaintenanceFraction`, the excess formula's linearity, and the restricted-form payout split are design choices — Locke draws the relevant lines qualitatively, not numerically or mechanically.*
- **`doGovernanceReview(self)`** (`1160-1223`) — Called from
  `doGovernment`. First,
  the **executor-neglect channel**: a non-executor member counts its own
  debts whose debtor is alive and solvent — collectible starting the
  instant a debt exists, no grace period at all — and adds
  `environmentLandExecutorNeglectPenalty` per such debt to its
  `executorGrievance` (the earlier `doForcefulDebtCollection` already
  tried the member's own reach, so anything still outstanding is
  genuinely beyond it).
  Then the levy pass (which is also where `legislatureGrievance` accrues —
  see `runLevyPass`); if this member's `grievance` exceeds
  `environmentLandGrievanceThreshold` it **withdraws** (§240) — leaves the set,
  nulls its government fields (including `governmentForm`/
  `governmentLegislature`/`governmentLevyFraction`), zeros all three
  grievances, then `dissolveGovernmentIfUnviable`, then `reviewLegislature`,
  `reviewExecutor`, `reviewExecutorPay`, **and** `reviewLevyFraction` if the
  body survives (a withdrawing executor must be replaced, and a smaller body
  can flip both the legislature's membership and the pay/levy votes'
  majorities — legislature first, since the other three now read it),
  stamping `lastLegislativeReviewTimestep` and zeroing `legislatureGrievance`
  for every survivor since a full reconvening just happened.

  Otherwise, **a full reconvening — `reviewLegislature`,
  `reviewRedistribution`, `reviewExecutor`, `reviewExecutorPay`, and
  `reviewLevyFraction`, in that order — fires on either of two independent
  triggers**, checked in this order: (1) summed `legislatureGrievance`
  across the government exceeds `environmentLandLegislatureGrievanceThreshold`
  — the collective frustration of subjects excluded from payout under a
  restricted form forces the legislature to revisit itself ahead of
  schedule; or (2) `environmentLandLegislativeReviewInterval` timesteps
  have elapsed since `lastLegislativeReviewTimestep` — the routine,
  scheduled case (a value of `1` reconvenes every timestep). Either
  trigger runs the identical five reviews, then stamps
  `lastLegislativeReviewTimestep` and zeros `legislatureGrievance` for
  every member — a legislature-grievance-forced reconvening also resets
  the interval clock, so the two triggers don't compound. Within that
  block, `reviewRedistribution`'s decay and `reviewExecutor`'s
  `executorGrievance` reset still only fire when that specific review
  actually changed something. `governmentForm` itself is never touched by
  any branch here — only withdrawal-triggered dissolution ends it, per
  Sect. 149's "supreme power to... alter the legislative" being the sole
  exception to Sect. 134's "sacred and unalterable" placement.
  **Not the same as an ordinary join**: `addToGovernment` no longer
  triggers any of these reviews immediately (Phase 6) — a joiner just
  inherits the government's current values and waits for the next
  scheduled or grievance-forced reconvening like everyone else, per
  Sect. 153's "not necessary... that the legislative should be always in
  being."
  *Locke, Sect. 240 ("the people shall be judge" of whether the legislature has broken trust) — each member judging its own government; Sect. 225 ("a long train of abuses") — cumulative, not one bad law. Sect. 156/152 ground the executor-neglect channel: the executor holds "a fiduciary trust... for the safety of the people" and is displaced by the legislative for maladministration — but replacement, not dissolution, and only if there is a better candidate. Sect. 199's "distinct interest from the rest of the community" grounds the legislature-grievance channel specifically — excluded subjects registering that the body governing them is not answerable to them, distinct from `grievance`'s narrower "I personally received less than my fair share" and from `executorGrievance`'s narrower "my own debt specifically went unenforced." This is **not** Sect. 125's "known and indifferent judge": self-judgment is what Sect. 125 identifies as the problem. Sect. 125 stays unaddressed — the model has no contested facts, only transparent transfers. The interval itself, and the choice to let legislature-grievance override it rather than merely add to a shared counter, are design choices.*
  *Locke, Sect. 240 ("the people shall be judge" of whether the legislature has broken trust) — each member judging its own government; Sect. 225 ("a long train of abuses") — cumulative, not one bad law. Sect. 156/152 ground the second channel: the executor holds "a fiduciary trust... for the safety of the people" and is displaced by the legislative for maladministration — but replacement, not dissolution, and only if there is a better candidate. This is **not** Sect. 125's "known and indifferent judge": self-judgment is what Sect. 125 identifies as the problem. Sect. 125 stays unaddressed — the model has no contested facts, only transparent transfers.*
- **`resetTrustIn(self, violator)`** (`1054-1058`) — Zeroes
  `self.locke["trust"][violator.ID]` if nonzero. Called on the Locke agents
  who could actually *perceive* a trespass: those adjacent to the trespassed
  cell at that timestep (via the neighbours-only loop in
  `recordLandTrespassIfOwned`, above), plus each crediting
  owner when the violation is booked as a debt (in `convertViolationsToDebts`).
  Not the whole population.
  *Locke, Sect. 94: people act on what they perceive — "it hinders not men from feeling... when they perceive, that any man... is out of the bounds of the civil society which they are of". Instant grid-wide knowledge of a transgression is not perception. An earlier Phase 2 version reset every living Locke agent's trust at once, citing Sect. 8 ("a trespass against the whole species") — but Sect. 8 establishes only that the wrong concerns everyone, not that everyone learns of it. Sect. 11 grounds the owner carve-out: the injured party has a particular standing and finds out when the debt lands on the ledger, wherever they were standing. Zeroing the score rather than decaying it is a design choice.*
- **`doGovernment(self)`** (`570-574`) — Override of `agent.py`'s
  no-op hook, called from `agent.Agent.doTimestep` at the same point (and
  under the same gating — skipped exactly when the agent died to
  metabolism this timestep) that the ordinary base `doTrading()` call
  immediately precedes. Runs the land-specific per-timestep passes in
  order: forceful collection, trust accrual, and `doGovernanceReview` (executor
  neglect + levy + withdrawal + re-legislation + executor replacement).
  Locke no longer overrides `doTrading` itself — ordinary trading runs
  unmodified via the base class, and this hook carries only the
  land-specific behavior, since none of it is actually trading.
  *Design choice — pure call-sequencing wrapper; the hook itself
  (`doGovernment`/`doProperty` in `agent.py`) is
  likewise a design choice, not a Locke-specific citation, since it's
  scaffolding shared by every decision model, not a Second Treatise
  mechanic. Verified behavior-preserving against the prior
  `doTrading`-override design via a deterministic scratch test of call
  order and death-gating (single-seed population comparisons are not a
  valid check here — see `doGovernanceReview`'s neighboring entries and
  the note on `set()`-based nondeterminism in `agent.py`'s section
  below).*
- **`findBestEthicalCell(self, cells, greedyBestCell=None)`** (`578-586`) —
  Override of the base movement-decision hook; computes
  `findEnforcementTarget` once for the whole decision, scores every
  candidate cell via `findEthicalValueOfCell` (passing that target along),
  and picks the highest-scoring one. This is what actually decides where a
  `Locke` agent moves each timestep.
  *Design choice — generic movement-selection architecture shared by every decision model in the codebase, not Locke-specific content.*
- **`findEnforcementTarget(self)`** (`597-604`) — Returns `None` unless
  `self` is currently one of its government's executors. Otherwise,
  collects every debt receivable held by any government member
  (its own and every fellow member's — an executor may be entitled to
  collect any of them) that is collectible (debtor alive and solvent —
  no grace period, a debt qualifies the instant it exists), and returns
  the debtor on the single **oldest** such debt — the most overdue case,
  regardless of distance. Non-executors and executors with nothing
  collectible get `None` (no pursuit bias).
  *Design choice — which of possibly several outstanding debts to chase (oldest, not nearest) is invented; Sect. 126 establishes only that an executive power to reach transgressors must exist, not a prioritization rule among several. No grace period is a design choice too, though the more literal one: Locke never describes reparation as needing to wait.*
- **Removed: `isDesperate(self)`.** Used to return `True` if `self` would
  end the timestep with negative sugar or negative spice on its *current*
  holdings alone, and `findEthicalValueOfCell` (below) used it to override
  every exclusion/restraint branch — a starving agent would treat any
  cell, foreign or not, at full raw value. Grounded in Locke's First
  Treatise Sect. 42 (a charity right to another's plenty in extreme want)
  — flagged even when it existed as a citation that couldn't be checked
  against the locally available Second Treatise PDF (see `CLAUDE.md`).
  **Removed after an ablation showed it hurts aggregate survival, not
  helps it**: a 25-seed same-seed sample of `config.json`'s pure-`"locke"`
  population (reproduced identically across two independent reruns of
  each condition) found 8/25 extinct (32%) with desperation active vs.
  4/25 extinct (16%) with it ablated — removing the override roughly
  halved the extinction rate. Consent withdrawal (grievance-driven) also
  fired less often without it (~7.4/seed vs. ~5.6/seed); government
  dissolution (<2 members) was unaffected either way (~41.2 vs. ~40.2/seed).
  Plausible mechanism, not independently confirmed by further
  instrumentation: a desperate trespass still creates a violation debt
  and unconditionally resets
  every witnessing neighbor's trust in the trespasser
  (`recordLandTrespassIfOwned`'s trailing block) — a population where
  starving agents periodically incur debt and wreck their own trust
  standing this way seems to end up *less* resilient in aggregate than
  one where they simply starve without those liabilities, even though the
  override clearly helps the individual agent survive that one timestep.
- **`findExpectedViolationCost(self, cell, owners)`** (`~621-631`) — The
  cost half of the movement valuation: what a Locke agent expects
  harvesting this foreign-owned cell to cost it, as an additive sum of
  four weighted terms, each a factor the agent could plausibly know about
  the land without god's-eye access to another government's internal
  state:
  - `environmentLandOwnerCountCostWeight * len(owners)` — more co-owners,
    more people who could notice or pursue.
  - `environmentLandGovernmentCostWeight * (1 if the cell's representative
    owner belongs to a government else 0)` — organized/governed land vs. a
    lone individual's claim. Reads only the binary "is it governed," never
    the government's size or whether it has an executor.
  - `environmentLandReparationRateCostWeight * rate`, where `rate` is the
    representative owner's `governmentRate` (or `min(environmentLandReparationRateChoices)`
    if that owner has no government) — the posted, voted "standing law"
    severity of the debt if caught.
  - `environmentLandRestrainedCostWeight * (1 if self.locke["restrained"]
    else 0)` — the agent's own catch history.
  `representative` is `next(iter(owners))` for the government/rate terms —
  the same "first owner stands in for the cell's political status" idiom
  the deleted `territoryGovernmentFor` used. For a cell co-owned across
  *different* governments (rare, only via `doInheritance` splitting a
  claim among heirs who later join different bodies), the government/rate
  terms follow whichever owner happens to be first — a deliberate
  simplification, not a per-owner sum.
  *Design choice — the additive-four-term shape, the weights, and the choice of these four factors are this codebase's own construction; Locke gives no numeric theory weighing them. Per term: `howManyOwners` has no direct citation (design choice). `isItUnderAGovernment` builds on Sect. 87-89 (self-help in the state of nature gives way to a common, organized authority) — that grounds treating governed and ungoverned land as *different*, though not the specific penalty or its size. `whatIsTheReparationRate`: Sect. 12 ("sufficient to make it an ill bargain") grounds the debt; Sect. 136-137 (law must be "established, settled, known," not an arbitrary extemporary decree) grounds *why this term is legitimately knowable* to an agent ahead of time — a posted, voted rate is exactly the promulgated standing law Locke requires, unlike a government's moment-to-moment enforcement activity, which the formula deliberately never reads. `amIRestrained`: Sect. 12's restraint, a personal deterrent effect.*
- **`findEthicalValueOfCell(self, cell, pursuitTarget=None)`** (`615-639`) —
  Computes a cell's attractiveness for the movement decision as
  `sugar + spice`, minus `findExpectedViolationCost(cell, owners)` when
  the cell is owned by another living agent that `self` isn't one of —
  a real benefit-minus-cost tradeoff, not a hard block. A cell `self`
  owns, or an unowned cell, is scored at its raw `sugar + spice`
  unchanged. **Redesigned**: this used to be a set of hardcoded
  overrides — a flat `-(sugar + spice) - 1` for a `restrained` agent, a
  `(sugar + spice) * (1 - landUse)` toll discount for lawful paid entry
  into a government's territory, and a flat `0` for everything else
  (closed policy, no government, a member on a co-member's own claim).
  With the toll/`"closed"` concept gone (see `voteLandUse`'s removal) and
  `restrained` folded into `findExpectedViolationCost` as one weighted
  term rather than an override, all of that collapses to the single
  benefit-minus-cost line. The `restrained` field, its `__init__`
  default, and its setter in `doForcefulDebtCollection` are all
  untouched — only its *effect* on this method changed. A real
  consequence, deliberate: the old `restrained` branch guaranteed a
  restrained agent avoided all foreign land; the new formula does not —
  with enough food on the cell relative to the weights, a restrained
  agent can now rationally choose it. Then, if `findBestEthicalCell`
  passed a `pursuitTarget` (only ever non-`None` for an executor with
  something collectible), subtracts `environmentLandExecutorPursuitWeight *`
  Manhattan distance from the candidate cell to the target's *current*
  cell — biasing movement toward the debtor without overriding the
  expected-cost term above. The executor uses the debtor's exact current
  position, not a sensed/inferred one.
  *Locke, Sect. 27: a labour-made claim "excludes the common right of other men" grounds *why* a foreign-owned cell carries any cost at all. The magnitude of that cost, and the four factors it's built from, are `findExpectedViolationCost`'s (see its citation directly above). Modelling ownership as a graded expected cost rather than an absolute prohibition is a design choice — Sect. 27 establishes exclusion as property's effect, not that a self-interested outsider must treat every claim as infinitely costly to cross.*
- **`doInheritance(self)`** (`682-717`) — Runs the base wealth-inheritance
  mechanic first, then splits/forfeits the deceased's land shares (Locke
  children co-own; otherwise the share reverts). Discharges the deceased's
  debts/receivables, calls `government.discard(self)`, then
  `dissolveGovernmentIfUnviable`, and — if the body still has two or more
  members — `reviewLegislature`, `reviewRedistribution`, `reviewExecutor`,
  `reviewExecutorPay`, **and** `reviewLevyFraction` over the survivors, in
  that order (a death changes the roster — an occasion for the
  legislative, Sect. 153; the executor may have been the one who died,
  Sect. 152; the deceased may have been a legislator, changing who holds
  power under a restricted form; a smaller surviving body can shift the
  executor-pay vote's majority even without an executor turnover; and the
  levy fraction's reference population — the whole surviving government —
  has shrunk by one, which can move its quantile breakpoints). Death is
  still an unconditional, immediate reconvening regardless of
  `environmentLandLegislativeReviewInterval` — the interval only bounds
  the *routine* case in `doGovernanceReview`. Every survivor's
  `lastLegislativeReviewTimestep` is reset to the current timestep and
  `legislatureGrievance` zeroed, exactly as any other reconvening would.
  `governmentForm` is not re-examined — a government's form outlives any
  one member's death; only who currently holds it can change. Trust
  scores are left intact.
  *Locke, Sect. 72 grounds the land-splitting half ("in certain proportions, according to the law and custom of each country" — the equal split is within that space). Sect. 211 grounds the dissolution (see `dissolveGovernmentIfUnviable`). The debt-discharge half is a plain design choice — Chapter V does not say whether a reparation debt survives a party's death.*
- **`doProperty(self)`** (`576-578`) — Override of `agent.py`'s
  other no-op hook, called from `agent.Agent.doTimestep` immediately after
  the base `updateValues()` call, under the same gating (skipped exactly
  when the agent died to aging this timestep). Triggers
  `processLandAbandonment` and `settleDebtsVoluntarily`. Locke no longer
  overrides `updateValues` itself; the base implementation runs
  unmodified and this hook carries only the land-specific end-of-timestep
  cleanup.
  *Design choice — per-timestep orchestration hook. See
  `doGovernment`'s entry above for the equivalence argument and
  verification method against the prior `updateValues`-override design.*
- **`recordLandTrespassIfOwned(self, sugarCollected, spiceCollected)`**
  (`~580`) — Called directly from `Locke`'s own `collectResourcesAtCell`
  override; `agent.py` doesn't reference it at all. If the cell has a
  living owner and `self` isn't one of them, appends a violation record
  to `cell.pendingViolations` (with a snapshot of the `owners` dict, so
  the eventual debt is credited to whoever was wronged then — see
  `convertViolationsToDebts`), prints a debug line, and calls
  `other.resetTrustIn(self)` on every cell-adjacent neighbour that has
  the method (the `Locke` agents who witnessed it; a non-`Locke` neighbour
  has no `resetTrustIn`). **That's the whole method now.** It used to have
  a toll/territory interception branch first — a non-member could pay
  `harvest * governmentLandUse` up front for a lawful harvest with no
  violation. With `governmentLandUse` and the whole toll/`"closed"`
  concept gone (see `voteLandUse`'s removal), *every* non-owner harvest
  on owned land is unconditionally a violation; compensated access now
  happens only after the fact, as reparation-debt settlement. Deliberately
  does **not** touch `lastHarvestedTimestep` — only the owner's own
  harvest resets the abandonment clock (in `processReturnToOwnedLand`), so
  a claim under continuous theft still decays per Locke's spoilage
  proviso, keyed to the possessor's own use, not mere third-party contact.
  Only ever reachable when `self` is `Locke` (only `Locke` overrides
  `collectResourcesAtCell` to call it); a non-`Locke` harvester on
  Locke-claimed land is never checked at all — an explicit tradeoff
  against the universal Sect. 6 grounding this method carried while it
  lived on `Agent`, documented in the `agent.py` section's
  `collectResourcesAtCell` entry.
  *Sect. 6: "no one ought to harm another... in his... possessions" — any harvest of another's claimed land without their consent is a wrong; with no toll path, there is no consented-access carve-out left in this method. Sect. 94 grounds the notification loop's neighbours-only scope: trust is lost by those who perceive the trespass. Sect. 10/12 ground the reparation right the recorded violation triggers (in `convertViolationsToDebts`). The lost Sect. 119/124 toll-access citation is gone with the mechanic it grounded.*
- **`spawnChild(self, childID, birthday, cell, configuration)`**
  (`1143-1144`) — Returns a new `Locke` instance for reproduction, so a
  `Locke` agent's children are also `Locke` agents by default. This is what
  makes every `isinstance(c, Locke)` heir-eligibility check meaningful. A
  child starts with its own independently-rolled `trustThreshold` and an
  empty trust dict/government — nothing about the parent's political life
  is inherited (see `__init__` above).
  *Design choice — technical mechanism ensuring heirs are typed correctly for the `isinstance(c, Locke)` checks elsewhere; not itself a textual claim.*

## `agent.py` — `class Agent` (base class, only the touched methods)

- **`doTimestep(self, timestep, predeterminedMove=None)`** — Two calls
  added to the existing sequence: `self.doGovernment()`
  immediately after `self.doTrading()` (same position, same gating — the
  post-metabolism `if self.alive == False: return` above it — that
  `doTrading()` itself sits behind), and `self.doProperty()`
  immediately after `self.updateValues()` at the very end (same gating —
  the post-aging `return` above it — that `updateValues()` sits behind).
  Added so a decision model with its own per-timestep or end-of-timestep
  behavior that *isn't* trading or the base value-update logic (`Locke`'s
  land/government/debt machinery being the only current example) doesn't
  have to piggyback on an override of `doTrading`/`updateValues` whose
  name no longer describes what it does.
  *Design choice — pure call-sequencing scaffolding shared by every
  decision model, not a Locke-specific or Second-Treatise mechanic.*
- **`doGovernment(self)`** / **`doProperty(self)`**
  — No-op hooks (`pass`) called from the two new sites above. Every
  non-`Locke` decision model (`Asimov`, `Bentham`, `Leader`, `Temperance`,
  `"none"`) inherits the no-op and is behavior-unchanged; only `Locke`
  overrides them (see `ethics.py`'s entries for `doGovernment`/
  `doProperty`, which replaced its prior `doTrading`/
  `updateValues` overrides one-for-one).
  *Design choice — scaffolding. Verified behavior-preserving for `Locke`
  via a deterministic scratch test (fake-agent trace confirming the full
  `doTimestep` call order and both death-gating branches — metabolism
  death skips both hooks, aging death runs the timestep hook but skips
  the cleanup hook — exactly match the prior override-based design) plus
  a 25-seed extinction-rate comparison. Note on the seed comparison: a
  **single-seed population-count comparison is not a valid check on this
  codebase** — rerunning byte-identical code (same seed, same config, no
  code change at all) in a fresh process was found to already produce
  different final populations and even different survive/extinct
  outcomes for the same seed (e.g. one seed extinct in one run, `pop=887`
  in an immediate rerun of identical code). Root cause: a government is a
  bare `set()` of member agents (see this file's header), and Python's
  default object hash is identity/address-based, so a `set`'s iteration
  order is not reproducible across process runs even under a fixed
  `random.seed()` — `PYTHONHASHSEED` does not fix this, since it only
  affects `str`/`bytes` hashing, not the id-based hash of arbitrary
  objects. This is a pre-existing property of the simulation, not
  something this refactor introduced, and means aggregate statistics
  across a seed sample (extinction rate, not per-seed exact match) are
  the only sound way to compare two versions of the code going forward.
- **`collectResourcesAtCell(self)`** (`249-260`) — **No longer touched at
  all.** This used to have one line added (`self.recordLandTrespassIfOwned
  (sugarCollected, spiceCollected)`, called unconditionally for every
  agent type) — first as a universal trespass check living directly here,
  then, briefly, as a call to a `Locke`-only no-op stub of the same name
  (so every decision model still paid the cost of a pointless call). Both
  are gone now: `Locke` overrides `collectResourcesAtCell` itself (it
  already did, for claim creation — see `ethics.py`'s entry) and calls
  `recordLandTrespassIfOwned` from there directly, so the base method
  needs no knowledge of trespass at all, and non-`Locke` decision models
  pay zero cost for a mechanic that was never theirs.
  *No longer a design-choice entry — nothing here to justify, since nothing was added.*
- **`recordLandTrespassIfOwned`** — **No longer exists on `Agent` in any
  form**, not even a no-op stub. Fully removed after two intermediate
  designs: first a universal method living directly on `Agent` (fired for
  every decision model, grounded in Sect. 6's "no one ought to harm
  another... in his... possessions" binding everyone), then briefly a
  no-op stub here with the real logic moved to a `Locke`-only override
  (fired only when `self` happened to be `Locke`, called through the
  `collectResourcesAtCell` hook above). Both were consequences of trying
  to keep this class-agnostic; the final design abandons that entirely —
  the method now lives solely under `class Locke`, called from `Locke`'s
  own `collectResourcesAtCell` (see `ethics.py`'s entry for the exact
  mechanics and its own citation). **Same consequence as both prior
  designs, restated once more for the final version**: a non-`Locke`
  agent can harvest `Locke`-claimed land completely freely — no toll, no
  debt, no trust reset. This is a real, standing regression against the
  Sect. 6 universality the original design satisfied; it is not a
  citation-honesty improvement, it is an explicit design choice, made
  because the caller reasoned the check belongs entirely inside `class
  Locke` rather than anywhere on the base class, no matter how thin.
  Verified via a 16-seed `["locke", "none"]` multiagent run (from when
  this was still a `Locke`-only override, not yet fully moved into
  `collectResourcesAtCell` — the finding is unaffected by that later
  move, since it only changed the calling mechanism, not who gets
  checked), instrumented to count harvests by non-`Locke` agents on
  `Locke`-claimed land: tens of thousands of such harvests per seed go
  completely unrecorded (e.g. seed `494485441`: 27,596 harvests totaling
  86,747 sugar+spice) that would have hit the toll/violation pipeline
  under the original universal version. The population-level effect
  across that sample was mixed, not one-directional (7/16 vs. 6/16 seeds
  with any `Locke` survivors) — consistent with this simulation's
  established sensitivity to any code change (see `doTimestep`'s entry
  above on `set()`-based nondeterminism), so no clean causal population
  effect could be isolated, only the mechanical fact that the check no
  longer fires cross-model.
  *Design choice, explicitly weaker than the original universal version's Sect. 6 grounding — see the consequence note above. The logic itself lives entirely under `class Locke` (see `recordLandTrespassIfOwned`'s `ethics.py` entry for its current citations).*
- **`doCombat(self, cell)`** — Unmodified base-engine method (ordinary
  aggressive-agent combat: unconditionally kills `cell.agent`, loots up to
  the flat `maxCombatLoot` environment constant, relocates the attacker
  onto the victim's now-empty cell). Briefly reused by
  `Locke.doForcefulDebtCollection` as its enforcement mechanism (see that
  method's `ethics.py` entry) before being superseded by the
  purpose-built `doSteal` below; no longer called from anywhere in
  `ethics.py`. Untouched by any of this — still used exactly as before by
  ordinary movement-triggered aggression (`moveToBestCell`, gated on
  `findAggression() > 0`), for any decision model.
  *Not a Locke-specific entry — pre-existing base-engine mechanic, listed here only because `ethics.py` briefly called it.*
- **`doSteal(self, cell, amount)`** (`300-311`) — New, minimal, generic
  method, added specifically so `Locke`'s debt enforcement (see
  `doForcefulDebtCollection`'s `ethics.py` entry) could be a real, modeled
  event like `doCombat` without either killing the target or being capped
  by an amount unrelated to what's actually owed. Mirrors `doCombat`'s
  structure closely: `prey = cell.agent`; loots sugar first then spice, up
  to `amount` and capped at what `prey` actually holds; transfers the
  loot to `self`; returns `(sugarLoot, spiceLoot)` so a caller can track
  exactly how much was recovered. Deliberately **does not** call
  `prey.doDeath(...)` (the whole point — the target survives) and
  **does not** call `self.gotoCell(cell)` (unlike `doCombat`, the victim
  is still occupying that cell, so relocating the attacker onto it would
  corrupt cell/agent bookkeeping). Takes `amount` as a parameter rather
  than reading a flat environment-wide constant like `maxCombatLoot`,
  specifically so a caller can request exactly what it's owed (or any
  other amount) rather than an unrelated global severity dial — no new
  config key was needed. Written with no `Locke`- or debt-specific
  knowledge at all (no import, no `getattr(x, "locke", ...)`, nothing),
  so any decision model could call it for a non-lethal forced transfer,
  exactly as `doCombat` is available to any decision model for a lethal
  one — it just happens that only `Locke` has a use for it today.
  *Design choice — new but minimal engine-level scaffolding, not a Locke-specific or Second-Treatise mechanic in itself; see `doForcefulDebtCollection`'s entry for how its citation supports being called this way.*

## `sugarscape.py` (single-line/single-block changes, no new methods)

- **Agent factory** (`235-236`, inside the agent-creation method) — Adds
  `elif "locke" in agentConfiguration["decisionModel"]: a = ethics.Locke(...)`.
  This is the only place in the whole codebase a `Locke` agent object is
  actually instantiated during simulation setup or dead-agent replacement.
  *Design choice — Python object-instantiation plumbing.*
- **Default configuration dict** (`~1845-1928`) — Adds, as hardcoded defaults:
  `"environmentLandDecayTimesteps": 50`,
  `"environmentLandExecutorCount": 1`,
  `"environmentLandExecutorMaintenanceFraction": 0.2`,
  `"environmentLandExecutorNeglectPenalty": 0.5`,
  `"environmentLandExecutorPartialityPenalty": 0.5`,
  `"environmentLandExecutorPayChoices": [0.0, 0.1, 0.2, 0.4, 0.7]`,
  `"environmentLandExecutorPursuitWeight": 0.5`,
  `"environmentLandGovernmentCostWeight": 2.0`,
  `"environmentLandGrievanceDecay": 0.5`,
  `"environmentLandGrievanceThreshold": 6.0`,
  `"environmentLandLegislativeReviewInterval": 10`,
  `"environmentLandLegislatureGrievancePenalty": 0.5`,
  `"environmentLandLegislatureGrievanceThreshold": 6.0`,
  `"environmentLandLegislatureSize": 1`,
  `"environmentLandLevyFractionChoices": [0.1, 0.3, 0.5, 0.7, 0.9]`,
  `"environmentLandMaxClaimsPerAgent": 1`,
  `"environmentLandOwnerCountCostWeight": 1.0`,
  `"environmentLandReparationRateChoices": [1.25, 1.5, 2.0, 3.0]`,
  `"environmentLandReparationRateCostWeight": 1.0`,
  `"environmentLandReparationStakeReference": 8`,
  `"environmentLandRestrainedCostWeight": 3.0`, and
  `"environmentLandTrustThresholdRange": [4, 8]`.
  The four `*CostWeight` keys are the additive terms of
  `findEthicalValueOfCell`'s expected-cost formula (see that entry).
  `environmentLandUseChoices` was removed here entirely when the
  toll/`"closed"` land-use vote was deleted — following the precedent
  below for `environmentLandLevyFraction` and the two grace-period keys.
  Phase 6 removed three now-dead keys entirely rather than leaving them
  orphaned: `environmentLandLevyFraction` (superseded by the voted
  `environmentLandLevyFractionChoices`), `environmentLandGovernmentReviewThreshold`,
  and `environmentLandExecutorReviewThreshold` (both threshold gates
  removed from `doGovernanceReview`, which now reviews every legislative
  reconvening unconditionally — see that method's entry above). A later
  change removed two more: `environmentLandForcefulCollectionGraceTimesteps`
  and `environmentLandExecutorNeglectGraceTimesteps` — debt collection has
  no grace period at all now, a debt is collectible the instant it's
  created (see `doForcefulDebtCollection`/`findEnforcementTarget`/
  `doGovernanceReview` above), so there was nothing left for either key to
  size.
  This is load-bearing: the config-file-override loop
  (`for opt in configuration: if opt in options: ...`) only applies a
  `config.json` value for a key that *already exists* in this dict — a key
  present only in the JSON file and not here is silently ignored. (This is
  exactly the bug that made the grace-period config fix fail the first time
  it was tried, before this dict entry was added — the trust-threshold key
  was added here from the start to avoid repeating it.)
  *Design choice — Python config-plumbing; see the note on why all three dict entries are load-bearing.*
- **`verifyConfiguration(configuration)`** (`~1534-1552`) — **Reverted**: a
  brief `orderSignificant = ["environmentLandUseChoices"]` exemption from
  this function's generic `configValue.sort()` was added when
  `environmentLandUseChoices` (a mixed `str`/`float` list whose order was
  meaningful) existed. With that key gone, the exemption and the whole
  `orderSignificant` list are removed — the function's list-sorting loop
  is back to its original upstream form.
  *Design choice — Python config-validation plumbing, no textual content.*

## `config.json` (`sugarscapeOptions`, value/key changes only)

- **`agentDecisionModels`** (line `17`) — Value changed from `["bentham"]`
  to `["locke", "bentham", "egoist", "asimov"]`, so the scenario's default
  run is a mixed population: Locke agents alongside `bentham`/`egoist`
  (both `ethics.Bentham` with selfishness `0.5` / `1`) and `asimov`
  (`ethics.Asimov`). The non-Locke agents are what keep the trespass →
  reparation machinery exercised even at hard exclusion (see
  `findEthicalValueOfCell`).
  *Design choice — scenario configuration value for mixed-population testing.*
- **`environmentLandDecayTimesteps: 3`** (line `83`, new key) — Overrides
  the code default of `50` down to `3` for this scenario.
  *Design choice (numeric value); the underlying concept is grounded in Sect. 38 — see `forfeitCellClaim` above.*
- **`environmentLandExecutorCount: 2`** (new key) — Overrides the code
  default of `1` up to `2`, so this scenario's governments elect two
  executors instead of one; with `environmentLandTrustThresholdRange: [1, 1]`
  already growing governments past 2 members quickly here, this exercises
  "top-2 of a larger roster" rather than just "both founders."
  *Design choice (the count); the appointment itself is Sect. 126 — see `voteExecutor` above.*
- **`environmentLandReparationRateChoices: [1.25, 1.5, 2.0, 3.0]`** /
  **`environmentLandReparationStakeReference: 8`** (new keys) — Match the
  code defaults; the reparation-rate menu, and the claim count that maps
  to its harshest choice (also the stake reference `voteGovernmentForm`
  uses). `environmentLandUseChoices` was previously set here too; it was
  removed with the toll/`"closed"` land-use vote. The four
  `environmentLand*CostWeight` keys are also set here, matching the code
  defaults (`findEthicalValueOfCell`'s expected-cost weights).
  *Design choice (the menus, the reference constant, and the cost weights); the reparation floor is Sect. 12 and the vote is Sect. 95-96 — see `voteReparationRate` above; the cost weights are `findEthicalValueOfCell`'s.*
- **`environmentLandLegislatureSize: 1`** (new key) — Matches the code
  default; kept at the one value where the founding form vote is a real,
  present-tense choice for the founders (see `voteGovernmentForm` above) —
  a deliberately unremarked K≥2 override is a distinct, separate
  experiment, not something to fold into this shared scenario config
  pre-emptively.
  *Design choice (the size); the underlying Sect. 132 taxonomy — see `voteGovernmentForm` / `findLegislature` above.*
- **`environmentLandMaxClaimsPerAgent: 1`** (new key) — Matches the code
  default; kept at the tightest possible value for this scenario, so
  claim-holding maps one-to-one onto agents rather than letting a few
  long-lived agents accumulate several scattered cells each.
  *Design choice (the number); the underlying bound on how much one person's labour/consumption can justly appropriate is Sect. 36 — see `collectResourcesAtCell` above.*
- **The governance tuning keys** —
  `environmentLandLevyFractionChoices` (`[0.1, 0.3, 0.5, 0.7, 0.9]`,
  matching the code default — the levy fraction is now voted rather than
  a flat config constant, see `voteLevyFraction` above),
  `environmentLandGrievanceThreshold` (`10.0`),
  `environmentLandGrievanceDecay` (`0.5`),
  `environmentLandLegislativeReviewInterval` (`10`, matching the code
  default — the timestep interval between mandatory legislative
  reconvenings), `environmentLandLegislatureGrievancePenalty` (`0.5`) and
  `environmentLandLegislatureGrievanceThreshold` (`6.0`, both matching
  code defaults — the third grievance channel that can force an early
  reconvening ahead of the interval), and the six executor keys
  `environmentLandExecutorMaintenanceFraction` (`0.2`),
  `environmentLandExecutorNeglectPenalty` (`0.5`),
  `environmentLandExecutorPartialityPenalty` (`0.5`),
  `environmentLandExecutorPayChoices` (`[0.0, 0.1, 0.2, 0.4, 0.7]`),
  `environmentLandExecutorPursuitWeight` (`0.5`); tuned against 250-step
  debug runs so that withdrawal (levy grievance) is a recurring minority event
  and executor replacement fires on roster churn — Sect. 225/230.
  `environmentLandGovernmentReviewThreshold`,
  `environmentLandExecutorReviewThreshold`,
  `environmentLandForcefulCollectionGraceTimesteps`, and
  `environmentLandExecutorNeglectGraceTimesteps`, all previously listed
  here, are gone along with the code defaults they overrode — see the
  `sugarscape.py` entry above.
  *Design choices (all the numbers); the mechanisms are Sect. 138/199/140 (levy and executor pay), Sect. 240/199 (withdrawal and partiality), Sect. 126/152/156 (executor), Sect. 153 (the legislative-reconvening interval) — see `voteRedistribution` / `voteExecutor` / `doGovernanceReview` / `runLevyPass` / `doForcefulDebtCollection` / `voteLevyFraction` above.*
- **`environmentLandTrustThresholdRange: [1, 1]`** (new key) — Overrides the
  code default `[4, 8]` down for this scenario, so trust accrues fast and
  governments grow to many members — which the redistribution/rebellion
  machinery needs to have bodies to act on.
  *Design choice — Locke never specifies how much trust-building precedes political society forming; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `gui.py` — `class GUI` (only the touched lines)

- **`self.colors`/`self.governmentColors`** (constructor, `~line 26-28`) —
  Adds `"noGovernment": "#888888"` (neutral gray for any agent not
  currently in a government), `"executor": "#FFB000"`,
  `"legislature": "#98FB98"`, and
  `"governmentMember": "#00A0A0"` (the three flat tones for the Branches
  agent mode), and an empty `self.governmentColors = {}`
  cache dict, populated lazily the first time a given government is
  rendered (see `findGovernmentColor` below) — unlike tribes/races/
  decision models, the number of governments isn't known ahead of time,
  so their palette assignment can't be precomputed at GUI construction.
  The original `"claimed": "#C87850"` fixed-tint color is kept (a
  per-owner-color variant was tried and then reverted by request — see
  `lookupFillColor` below — so this flat tint is back to being the actual
  Property color, not dead code), alongside a new `"unclaimed": "#FFFFFF"`
  — plain white for any cell without an owner, matching the existing
  convention `lookupNetworkColor` already uses for "nothing here" (a
  literal `"white"` for an unoccupied cell in network view) rather than
  inventing a new earth tone. Property
  mode originally left unclaimed cells showing the ordinary sugar/spice
  gradient; a follow-up correction removed that too, so neither branch of
  Property mode reads from `"sugarAndSpice"` at all — claimed and
  unclaimed are now two flat tones, with no resource-level color ("the
  mountains") visible anywhere in this mode.
  *Design choice — visualization only.*
- **`configureAgentColorNames(self)`** (`80-81`) — Adds `"Government"` (Phase 2)
  and `"Branches"` (Phase 4, originally named `"Executor"` before it grew a
  legislature tone — see `lookupFillColor` below) to the selectable agent
  coloring modes.
  *Design choice — visualization only.*
- **`configureEnvironmentColorNames(self)`** (`218`) — Adds `"Property"`
  to the selectable environment coloring modes (previously only
  `"Pollution"`). A `"Territory"` mode (colored by owning government, via
  `findGovernmentColor`) was added alongside it and then removed by
  request — `findGovernmentColor` itself is kept, since the `"Government"`
  agent mode still uses it.
  *Design choice — visualization only.*
- **`findGovernmentColor(self, government)`** (new, Phase 2) — A
  government is a plain `set()`, which is unhashable, so this keys the
  color cache on `id(government)` instead (stable for the government's
  lifetime, since membership changes mutate the set in place rather than
  replacing it — see `addToGovernment` in `ethics.py`). Assigns the next
  unused color from `self.palette`, cycling by modulo once every palette
  slot has been claimed by some other government.
  *Design choice — visualization only; the one place in this codebase that colors a dynamically-unbounded, run-time-discovered category rather than a fixed, config-known one (tribes/races/decision models all precompute their palette slice from a config-known count at GUI construction).*
- **`lookupFillColor(self, cell)`** (`661-717`, one method, several added
  branches) — Has an `elif` branch for
  `activeColorOptions["environment"] == "Property"`: any claimed cell
  (`len(cell.owners) > 0`) renders as the flat `"claimed"` tint, any
  unclaimed cell as the flat `"unclaimed"` tint — a binary claimed/
  unclaimed signal, not proportional to share or distinguishable by
  owner, and with no sugar/spice-derived color on either side of that
  branch. A per-owner-color version of this branch (distinct color per
  owner, blended 50% with the sugar/spice level) was built, then
  explicitly reverted by request: it made owned land visually noisy —
  blending with the sugar/spice gradient ("mountains") muddied the
  claimed/unclaimed signal the flat tint is meant to give at a glance.
  The first attempt at removing that blend only fixed claimed cells and
  left unclaimed ones still showing the gradient; a follow-up correction
  gave unclaimed cells their own flat tint too, so the mountains are gone
  from this mode entirely, not just from owned land. A separate follow-up
  attempt
  to show both Property and Government information on the same occupied
  cell (first via a colored outline generalized to *every* agent-coloring
  mode by mistake, then via a small marker dot layered on top) was also
  built and then reverted by request, in favor of keeping this method
  and every coloring mode's behavior exactly as simple as it looks here.
  The **`"Government"` agent branch** duck-types via `getattr(agent, "locke",
  None)` (this file doesn't import `ethics.py`) to find the agent's government
  and colors it via `findGovernmentColor`; any agent without one — every
  non-Locke agent included — gets the neutral `"noGovernment"` gray.
  The **`"Branches"` agent branch** (Phase 4, renamed from `"Executor"` when
  a legislature tone was added) is the same duck-typed lookup, four flat
  tones checked in priority order: `"executor"` gold when `agent` is a
  member of `locke["governmentExecutor"]` (a `frozenset`, possibly holding
  more than one agent per `environmentLandExecutorCount`) — checked first,
  since under `"democracy"` (or the `"all"` legislature-size sentinel) the
  executor is also always a legislature member, and the more specific
  executive role should win; else `"legislature"` pale green when `agent`
  is a member of `locke["governmentLegislature"]`; else `"governmentMember"`
  teal for any other member; `"noGovernment"` gray otherwise. **Removed**:
  a `"Territory"` environment branch (Phase 4) once sat alongside
  `"Property"` here — a claimed cell colored by its owning government via
  `findGovernmentColor` instead of the flat `"claimed"` tint, so a
  government's whole territory and (under `"Government"`/`"Branches"`)
  its members read in the same palette color. Removed by request; the
  `"Property"`/`"Government"`/`"Branches"` modes and `findGovernmentColor`
  itself are all unaffected, since `"Government"` still calls it directly
  on an agent's own government. Selecting an environment *and* an agent
  mode still shows only the agent colour on an occupied cell (agent
  branches take priority — unchanged, original behaviour).
  *Design choice — visualization only. `"Branches"` is a peer mode, not an overlay on `"Property"` / `"Government"`; the two reverted elaborations above were about blending signals on one cell, which this does not do.*

## `README` (documentation only, no behavior)

- **`agentDecisionModels` entry** — Adds `"locke"` to the `Options:` list and
  a new `Note:` line documenting that trespass detection fires regardless of
  the trespasser's own decision model.
  *Design choice — documentation, not a textual claim.*
- **`environmentLandDecayTimesteps` entry** (new) — Documents the decay
  config key, its Locke-only relevance, and its code default of `50`.
  *Design choice — documentation; concept grounded in Sect. 38, see `forfeitCellClaim` above.*
- **`environmentLandExecutorCount` entry** (new) — Documents the executor
  count, its clamping to `[1, len(members)]`, and that it generalizes the
  same vision+movement/lowest-ID selection the single-executor case
  already used; Locke-only.
  *Design choice — documentation; see `voteExecutor` above.*
- **`environmentLandExecutorNeglectPenalty` entry** (new, rewritten) —
  Documents the per-debt-per-timestep grievance accrued to
  `executorGrievance` for a debt still unenforced, and that a debt is
  collectible/countable-as-neglected starting the very timestep it's
  created — no grace period at all; Locke-only. The
  `environmentLandForcefulCollectionGraceTimesteps`,
  `environmentLandExecutorNeglectGraceTimesteps`, and
  `environmentLandExecutorReviewThreshold` entries that previously sat
  alongside this are all gone — there is no grace window or threshold
  left to size: `reviewExecutor` runs at every legislative reconvening
  unconditionally regardless (see `doGovernanceReview` above).
  *Design choice — documentation; see `voteExecutor` / `reviewExecutor` above; the no-grace-period choice is Sect. 12/19 — Locke gives reparation no waiting period.*
- **`environmentLandExecutorPartialityPenalty` / `environmentLandExecutorPursuitWeight`
  entries** (new) — Document the partiality grievance (fed into ordinary
  `grievance`, distinct from `executorGrievance`) and the movement-scoring
  pursuit weight; both Locke-only.
  *Design choice — documentation; see `doForcefulDebtCollection` / `findEthicalValueOfCell` above.*
- **`environmentLandExecutorPayChoices` / `environmentLandExecutorMaintenanceFraction`
  entries** (new) — Document the executor-pay menu now voted via
  `votePayFraction`/`governmentExecutorPay`, and the maintenance ceiling
  above which the excess accrues grievance in `runLevyPass`; both Locke-only.
  *Design choice — documentation; see `votePayFraction` / `runLevyPass` above.*
- **`environmentLandReparationRateChoices` entry** (new, rewritten for
  Phase 6) — Documents the reparation-rate menu and that it's now voted
  via the shared quantile-bracket mechanism (`findQuantileChoice`/
  `voteByQuantileBracket`), each founder's own claims ranked against the
  founding pair itself; notes the documented equal-claims finding (two
  founders with identical claims, however large, always land on the
  mildest choice — no variance to rank against); Locke-only.
  **`environmentLandReparationStakeReference` entry** — Documents the
  stake reference, now grounding **only** `voteGovernmentForm`'s
  founding-form preference — no longer `voteReparationRate` (moved off it
  in Phase 6) or `voteLandUse` (deleted).
  *Design choice — documentation; see `voteReparationRate` / `voteGovernmentForm` above.*
- **`environmentLandLegislatureSize` entry** (new, extended for Phase 6) —
  Documents the oligarchy/monarchy ruling-body size, that `1` behaves as
  monarchy and `>1` as oligarchy through one shared selection mechanism,
  that it has no effect under `"democracy"`, and the new literal string
  `"all"` sentinel that forces every government to `"democracy"`
  unconditionally regardless of `voteGovernmentForm`'s outcome — a total
  kill-switch for the concentration mechanism, useful as a pure-
  direct-democracy control condition; Locke-only.
  *Design choice — documentation; see `voteGovernmentForm` / `findLegislature` above.*
- **`environmentLandLevyFractionChoices` entry** (new, replacing the old
  `environmentLandLevyFraction` entry) — Documents the levy-fraction
  menu and that the levy fraction is now the sixth founding law, voted
  via the same shared quantile-bracket mechanism as reparation rate but
  with the *whole government* (never smaller than 2) as the reference
  population rather than the legislature, specifically to avoid the
  single-point-reference degeneracy a monarchy's size-1 legislature would
  otherwise produce; Locke-only.
  *Design choice — documentation; see `voteLevyFraction` above.*
- **`environmentLandMaxClaimsPerAgent` entry** (new) — Documents the
  per-agent claim cap, that it gates *new* acquisition only (an agent
  already over the limit when it's lowered isn't forced to forfeit
  anything), and that it's checked alongside — not instead of — the
  "enough, and as good" proviso; Locke-only.
  *Design choice — documentation; see `collectResourcesAtCell` above.*
- **`environmentLandGrievanceThreshold` /
  `environmentLandGrievanceDecay` entries** (new) — Document the
  withdrawal-grievance threshold/decay; both Locke-only. The old
  `environmentLandGovernmentReviewThreshold` entry is gone — Phase 6
  removed the key it documented (see the `sugarscape.py` entry above).
  The `environmentLandUseChoices` entry is also gone — its land-use vote
  was deleted along with the toll/`"closed"` concept.
  *Design choice — documentation; see `voteRedistribution` / `doGovernanceReview` above.*
- **`environmentLandGovernmentCostWeight` / `environmentLandOwnerCountCostWeight`
  / `environmentLandReparationRateCostWeight` /
  `environmentLandRestrainedCostWeight` entries** (new) — Document the
  four additive weighted terms of `findEthicalValueOfCell`'s expected-cost
  formula; all Locke-only.
  *Design choice — documentation; see `findExpectedViolationCost` above.*
- **`environmentLandLegislativeReviewInterval` entry** (new) — Documents
  the timestep interval between mandatory full legislative reconvenings
  (`reviewLegislature`/`reviewRedistribution`/`reviewExecutor`/
  `reviewExecutorPay`/`reviewLevyFraction`, all run together), that a
  value of `1` reproduces "every timestep," and that death and consent
  withdrawal still trigger an *immediate* reconvening regardless of the
  interval; Locke-only.
  *Design choice — documentation; Sect. 153's "not necessary... always in being" grounds having an occasion at all, not any particular interval length — see `doGovernanceReview` above.*
- **`environmentLandLegislatureGrievancePenalty` / `environmentLandLegislatureGrievanceThreshold`
  entries** (new) — Document the third grievance channel: the per-timestep
  penalty accrued by a member excluded from the legislature under a
  restricted form and taxed but never paid (see `runLevyPass` above), and
  the summed-across-the-government threshold that, once crossed, forces
  an early reconvening ahead of the interval; distinct from both
  `grievance` (withdrawal) and `executorGrievance` (executor replacement
  only); Locke-only.
  *Design choice — documentation; Sect. 199 grounds the underlying grievance (rebellion begins with those excluded from power feeling the pinch), the threshold value and mechanism are a design choice — see `runLevyPass` / `doGovernanceReview` above.*
- **`environmentLandTrustThresholdRange` entry** (new) —
  Documents the trust-threshold-range config key, that it's independently
  drawn per agent at birth and not inherited from a parent, its Locke-only
  relevance, its default of `[4, 8]`, and that founding is bilateral while
  joining an existing government is unilateral.
  *Design choice — documentation; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `examples/locke_basic.json` (new file, not a class)

A standalone, runnable example scenario for the `locke` decision model, with
its own `__README__` summary field. Notable settings distinct from the main
`config.json`: `agentInheritancePolicy: "children"`,
`environmentLandDecayTimesteps: 10`, `environmentLandTrustThresholdRange: [1, 2]`,
and the reparation / levy-fraction-choices / grievance / executor /
legislature-review-interval / legislature-grievance / expected-cost-weight
keys set to the same values as the main config
(`environmentLandLegislativeReviewInterval: 10`,
`environmentLandLegislatureGrievancePenalty: 0.5`,
`environmentLandLegislatureGrievanceThreshold: 6.0`,
`environmentLandLevyFractionChoices: [0.1, 0.3, 0.5, 0.7, 0.9]`) so the full
governance machinery, including the levy-fraction founding vote and the third
grievance channel, is exercised when the example is run.

*Design choice — a runnable scenario file, not a textual claim.*
