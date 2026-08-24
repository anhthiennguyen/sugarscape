# Property (the `locke` decision model)

A complete, source-order reference to every file the `locke` branch has ever
touched (per `git diff a46ec6f..HEAD --stat`, the commit before the `Locke`
class existed), every class in those files that changed, and every method in
those classes — or, for single-line/config changes, the line itself.

## `ethics.py` — `class Locke(agent.Agent)` (`ethics.py:552-920`)

- **`__init__(self, agentID, birthday, cell, configuration)`** (`552-556`) —
  Calls `super().__init__` for standard agent setup, then adds
  `self.locke = {"claims": [], "debtsReceivable": []}`: the agent's own
  bookkeeping of which cells it holds a share in, and which debts are owed
  *to* it as creditor.
  *Design choice — bookkeeping structure, no textual analog.*
- **`cellOwners(self, cell)`** (`557-560`) — Lazily creates and returns
  `cell.owners` (a `{agent: share}` dict) the first time it's touched. The
  central accessor for reading ownership anywhere in the class.
  *Design choice — lazy accessor plumbing for the ownership concept grounded in Locke, Sect. 27: "every man has a property in his own person... the labour of his body, and the work of his hands, we may say, are properly his."*
- **`cellConsentedAgents(self, cell)`** (`562-565`) — Lazily creates and
  returns `cell.consentedAgents`, the set of agents with standing harvest
  permission on that cell.
  *Design choice — accessor plumbing for the consent concept grounded in Sect. 35/120 (see `doLandConsentGrants` below).*
- **`cellConsentApprovals(self, cell)`** (`567-570`) — Lazily creates and
  returns `cell.consentApprovals`, a `{candidate: {owners who have approved}}`
  dict tracking in-progress unanimous-consent votes to admit a new consented
  harvester.
  *Design choice — accessor plumbing; the unanimity rule itself is grounded in Sect. 35 (see `doLandConsentGrants` below).*
- **`cellPendingViolations(self, cell)`** (`572-575`) — Lazily creates and
  returns `cell.pendingViolations`, the list of thefts not yet converted
  into debt.
  *Design choice — accessor plumbing.*
- **`agentLandDebtsOwed(self, agent)`** (`577-580`) — Lazily creates and
  returns `agent.landDebtsOwed` on **any** agent object passed in, not just
  `Locke` instances. This single line is what lets a non-`Locke` agent carry
  land debt at all.
  *Design choice — accessor plumbing; the underlying reparation debt it stores is grounded in Locke, Sect. 10 (see `convertViolationsToDebts` below).*
- **`claimCellFor(self, cell, owner)`** (`582-586`) — Sets
  `cell.owners = {owner: 1.0}` (100% single ownership), stamps
  `lastHarvestedTimestep` to the current timestep, and resets
  `consentedAgents`/`consentApprovals` to empty. The ownership-establishing
  primitive, used when a cell is first claimed.
  *Locke, Sect. 32: "As much land as a man tills, plants, improves, cultivates, and can use the product of, so much is his property. He by his labour does, as it were, inclose it from the common."*
- **`forfeitCellClaim(self, cell)`** (`588-592`) — The inverse of
  `claimCellFor`: wipes `cell.owners` back to `{}`, resets
  `lastHarvestedTimestep` to `-1`, and clears consent state. This is what
  "reverts to the commons" means mechanically.
  *Locke, Sect. 38: "if either the grass of his enclosure rotted on the ground, or the fruit of his planting perished without gathering, and laying up, this part of the earth, notwithstanding his enclosure, was still to be looked on as waste, and might be the possession of any other."*
- **`convertViolationsToDebts(self, cell, timestep)`** (`594-608`) — For
  every pending violation on the cell, splits the stolen `amount` across all
  current owners proportional to share, creates one debt record per
  (owner, trespasser) pair, files it on both the creditor's
  `debtsReceivable` and the debtor's `landDebtsOwed`, then clears
  `pendingViolations`. This is the "owner returns → theft becomes debt"
  step.
  *Locke, Sect. 10: "he who hath received any damage, has... a particular right to seek reparation from him that has done it."*
- **`removeSettledDebt(self, debt)`** (`610-617`) — Removes one fully-paid
  or otherwise-discharged debt from both the creditor's `debtsReceivable`
  and the debtor's `landDebtsOwed` lists.
  *Design choice — ledger cleanup once reparation (Sect. 10) has already been satisfied; no distinct textual basis of its own.*
- **`transferShare(self, cell, previousOwner, newOwner)`** (`619-629`) —
  Moves one owner's entire share of a cell to a new owner: settles any
  pending violations into debts first (so nothing is lost in the handoff),
  then pops the share off the old owner and adds it to the new owner,
  updating both agents' `locke["claims"]` lists. Used by buyouts.
  *Design choice — internal share-moving primitive; the substantive "purchase" concept it serves is grounded in Sect. 120 (see `doLandBuyoutOffers` below).*
- **`acquireLandClaim(self, cell)`** (`631-635`) — Thin wrapper calling
  `claimCellFor(cell, self)` and appending the cell to
  `self.locke["claims"]` — the actual "claim this cell" action taken when
  harvesting unclaimed land.
  *Locke, Sect. 28: "That labour put a distinction between them and common: that added something to them more than nature, the common mother of all, had done; and so they became his private right."*
- **`collectResourcesAtCell(self)`** (`637-648`) — Override of the base
  harvesting method. Calls `super().collectResourcesAtCell()` first (which
  now also runs the generic trespass check — see `agent.py` below). Then:
  if the cell is unclaimed and unclaimed land still exists nearby, claims
  it; if `self` is already an owner, calls `processReturnToOwnedLand`.
  *Design choice — dispatch/routing logic; the substantive rules it dispatches to (`acquireLandClaim`, `processReturnToOwnedLand`) each carry their own citation.*
- **`processReturnToOwnedLand(self, cell)`** (`650-654`) — Re-stamps
  `lastHarvestedTimestep` and calls `convertViolationsToDebts` — the "owner
  comes back to land that was stolen from" moment from the design.
  *Design choice — the specific "wait until the owner returns" timing is invented; the reparation right it triggers is grounded in Sect. 10 (see `convertViolationsToDebts` above).*
- **`processLandAbandonment(self)`** (`656-670`) — Runs every timestep for
  every claim the agent holds; forfeits any cell the *owner* hasn't
  harvested in `environmentLandDecayTimesteps` steps, otherwise keeps it in
  the agent's claims list. A trespasser or consented licensee harvesting the
  cell does not reset this clock (see `recordLandTrespassIfOwned` in
  `agent.py` below) — a claim under continuous theft still decays.
  *Locke, Sect. 38 (see `forfeitCellClaim` above) grounds losing land through non-use; the specific numeric timestep threshold (`environmentLandDecayTimesteps`) is a design choice — Locke never puts a number on it.*
- **`settleDebtsVoluntarily(self)`** (`672-693`) — Runs every timestep; for
  every debt the agent owes, pays down as much as it can from sugar/spice
  above its own metabolic need (sugar first, then spice), removing the debt
  once fully paid. No proximity requirement.
  *Locke, Sect. 37: "the intrinsic value of things... depends only on their usefulness to the life of man," combined with Sect. 47: "And thus came in the use of money, some lasting thing that men might keep without spoiling, and that by mutual consent men would take in exchange for the truly useful, but perishable supports of life." Together these ground value as commensurable across different useful goods, but it's a stretched analogy: Locke's money is valuable specifically because it is NOT one of the perishable staples, whereas sugar and spice here are the staples themselves — the "same nominal value regardless of resource" rule has no tight single-passage match.*
- **`doLandConsentGrants(self)`** (`695-727`) — Runs every timestep for
  every cell the agent co-owns; for each agent adjacent to that cell not
  yet consented, co-signs — there is no dissent path; an owner
  unconditionally adds itself to the approval set every timestep it
  processes the claim, with no cost-benefit check of any kind — and once
  **every** current owner has signed on (unanimous, not share-weighted),
  charges the
  candidate the cell's current `sugar + spice` value (with a
  50-metabolism-timestep reserve buffer) split pro rata across all owners,
  then marks the candidate consented.
  *Locke, Sect. 35: "no one can inclose or appropriate any part [of commonly-held land], without the consent of all his fellow-commoners; because this is left common by compact." Sect. 120 separately grounds owner-granted "permission" as a valid means of land enjoyment in general. The fee formula and the 50-timestep reserve buffer are still design choices with no textual basis; the approval rule itself now matches Sect. 35's unanimity requirement rather than diverging from it.*
- **`doLandBuyoutOffers(self)`** (`729-752`) — Runs every timestep; for
  every cell adjacent to the agent's current position that it doesn't
  itself own, if that cell lies outside the current owner's own foraging
  range, offers to buy that owner's share outright at
  `(maxSugar + maxSpice) * share` (again with the 50-metabolism-timestep
  reserve buffer), paying directly and calling `transferShare`.
  *Locke, Sect. 120: "Whoever therefore, from thenceforth, by inheritance, purchase, permission, or otherways, enjoys any part of the land... must take it with the condition it is under." The buyout price formula itself is a design choice.*
- **`doForcefulDebtCollection(self)`** (`757-791`) — Runs every timestep;
  for every neighboring agent, for every debt that neighbor owes (to
  anyone, since debts can be owed by any agent type), once the debt is
  older than `environmentLandForcefulCollectionGraceTimesteps`, and — new
  in Phase 2 — provided the collector isn't in a government whose
  membership excludes the creditor, seizes whatever sugar/spice the debtor
  currently has (not limited to an above-metabolism reserve), but capped at
  the outstanding debt amount, and pays it to the creditor.
  *Two sections together for the base method, not one: Locke, Sect. 19 grounds why self-help force is legitimate at all here — "the want of such an appeal gives a man the right of war" — and there is no common judge/government in this simulation to appeal to instead. Sect. 12 grounds why the seizure is capped rather than punitive: "each transgression may be punished to that degree, and with so much severity, as will suffice to make it an ill bargain to the offender, give him cause to repent." (An earlier version of this citation used only Sect. 19's thief-killing scenario, which is tonally mismatched with a calm, capped seizure after a grace period — Sect. 12 is the better fit for what the code actually does.) The Phase 2 membership gate's best fit is Sect. 130: "The power of punishing he wholly gives up... to assist the executive power of the **society**" — a member's free-agent collection right is resigned once they join a government, restricted to fellow members — but this is a looser analogy than most of this file's citations; noted plainly rather than overstated.*
- **`doTrustAccrual(self)`** (`793-806`) — Runs every timestep for every
  cell the agent owns; every neighbor of that cell who is alive, not a
  co-owner, and didn't trespass on it *this* timestep earns one trust point
  from the owner (via `increaseTrust`) — the literal complement of the
  trespass check `agent.recordLandTrespassIfOwned` already performs,
  reusing the same `cellPendingViolations`/`findNeighborAgents` primitives
  rather than re-scanning adjacency separately.
  *Design choice — no textual analog for a quantified trust-building period; Locke never describes trust or reputation being built up numerically before political society forms.*
- **`increaseTrust(self, candidate, cell)`** (`807-815`) — Increments
  `self.locke["trust"][candidate.ID]` by 1, logs it, and — only if
  `candidate` is itself a `Locke` instance — checks whether this increment
  just completed mutual threshold-crossing (`attemptGovernmentFormation`).
  The `isinstance(candidate, Locke)` check here is also what satisfies
  "exclusion follows from incapacity to consent, not discrimination": a
  non-`Locke` agent simply has no `.locke` dict to reciprocate through, so
  it's structurally never reachable past this point — no
  characteristic-based check (race/sex/tribe/tag) exists anywhere in this
  path.
  *Design choice for the mechanic itself; the exclusion principle above is Locke, Sect. 60's logic (exclusion from full agency grounded in incapacity — "lunatics and ideots are never set free... but continued under the tuition... of others, all the time their own understanding is uncapable") applied here to consent rather than reason.*
- **`attemptGovernmentFormation(self, other)`** (`816-822`) — Returns
  early unless *both* directions of trust (`self`'s trust in `other`, and
  `other`'s trust in `self`) have each reached that tracking agent's own
  `trustThreshold`; only then calls `formOrJoinGovernmentWith`.
  *Design choice — the bilateral-threshold mechanic has no textual analog; Locke describes political society forming by mutual consent (see Sect. 95-99 below) but never a quantified precondition for it.*
- **`formOrJoinGovernmentWith(self, other)`** (`823-842`) — If both agents
  already belong to (the same or different) governments, does nothing —
  logging the cross-government case explicitly. If exactly one already
  belongs to a government, the other joins it via `addToGovernment`. If
  neither does, founds a new government: a plain `set()` containing both
  agents, assigned by shared object reference to both agents'
  `self.locke["government"]`.
  *Locke, Sect. 95-99 grounds forming political society by mutual consent — "when any number of men have so consented to make one community or government, they are thereby presently incorporated" — and is why this is implemented as a bare `set()` rather than a dedicated class: a government here is nothing more than its members' collected consent, not a thing that exists apart from them. The different-governments-no-merge branch is grounded in Sect. 121: "he that has once... given his consent to be of any common-wealth, is perpetually and indispensably obliged to be, and remain unalterably a subject to it... and can never be again in the liberty of the state of nature" — membership is exclusive and binding, so an already-committed agent can't also found or join a second body.*
- **`addToGovernment(self, government, newMember)`** (`843-849`) — Adds
  `newMember` to the existing shared `set()` and points their own
  `self.locke["government"]` at that same set object; the set already
  referenced by every other current member is mutated in place, so no
  member's reference needs updating and the government never gets
  recreated.
  *Locke, Sect. 122 grounds the specific mechanic ("the existing body doesn't re-found itself"): an individual joining an established commonwealth becomes a member "by his actually entering into it by positive engagement, and express promise and compact" — the commonwealth itself doesn't need to re-form or re-consent for each new member, only the joiner needs to consent.*
- **`resetTrustIn(self, violator)`** (`850-854`) — Zeroes
  `self.locke["trust"][violator.ID]` if nonzero. Called on every living
  `Locke` agent (via three duck-typed lines appended to
  `agent.recordLandTrespassIfOwned`, see `agent.py` below) any time any
  agent — Locke or not — is recorded as a trespasser, so a single
  violation resets *every* tracking agent's trust in the violator at once,
  not just the immediate victim's.
  *Locke, Sect. 8: a transgression is "a trespass against the **whole species**, and the peace and safety of it" — grounding the global (not victim-only) scope of the reset; the specific choice to zero the score rather than, say, decay it is a design choice Locke doesn't address.*
- **`doTrading(self)`** (`856-861`) — Override that runs the base agent's
  ordinary sugar/spice trading first (`super().doTrading()`), then the
  four land-specific behaviors above in order: consent grants, buyouts,
  forceful collection, and (Phase 2) trust accrual.
  *Design choice — pure call-sequencing wrapper.*
- **`findBestEthicalCell(self, cells, greedyBestCell=None)`** (`863-876`) —
  Override of the base movement-decision hook; scores every candidate cell
  via `findEthicalValueOfCell` and picks the highest-scoring one. This is
  what actually decides where a `Locke` agent moves each timestep.
  *Design choice — generic movement-selection architecture shared by every decision model in the codebase, not Locke-specific content.*
- **`findEthicalValueOfCell(self, cell)`** (`877-883`) — Computes a cell's
  attractiveness as `sugar + spice`, with a conditional multiply by `1.0`
  when the cell is owned by someone else without consent — currently a
  no-op, so ownership has zero effect on movement choice.
  *Design choice — currently a no-op stub; there is no implemented concept here to cite.*
- **`doInheritance(self)`** (`884-913`) — Runs the base wealth-inheritance
  mechanic first (`super().doInheritance()`), then for every claimed cell,
  either splits the deceased's share evenly across all living `Locke`
  children (co-ownership) or, if none exist, removes the deceased's share
  outright; forfeits the cell entirely if no owners remain afterward. Also
  discharges all of the deceased's outstanding debts/receivables. **Does
  not** touch trust scores or government membership at all: a dead agent
  is simply skipped by `resetTrustIn`'s and `doTrustAccrual`'s loops (both
  iterate `sugarscape.agents`/`findNeighborAgents()`, which only return
  living agents) — functionally harmless — but a dead agent's object stays
  forever in every government `set()` it belonged to and in every other
  agent's `trust` dict, an unbounded stale-reference leak this Phase 2 pass
  introduced and doesn't clean up. Flagging this as a real gap, not a
  design choice with a rationale behind it.
  *Locke, Sect. 72: "the possession of the father being the expectation and inheritance of the children, ordinarily in certain proportions, according to the law and custom of each country." This grounds the land-splitting half of this method — Locke explicitly leaves the split mechanism to "law and custom," so the specific choice of an equal split among every living child is a design choice within a space Locke deliberately left open. The debt-discharge half has no citation of its own: nothing in Chapter V says whether a reparation debt survives the debtor's or creditor's death, so wiping the ledger clean at death rather than transferring it to heirs is a plain design choice, not something Sect. 72 (or anything else read so far) actually covers.*
- **`updateValues(self)`** (`914-918`) — Per-timestep hook (calls base
  `super().updateValues()`) that triggers `processLandAbandonment` and
  `settleDebtsVoluntarily` — the two behaviors that happen automatically
  every timestep regardless of the agent's location.
  *Design choice — per-timestep orchestration hook, architecture not content.*
- **`spawnChild(self, childID, birthday, cell, configuration)`**
  (`919-920`) — Returns a new `Locke` instance for reproduction, so a
  `Locke` agent's children are also `Locke` agents by default. This is what
  makes every `isinstance(c, Locke)` heir-eligibility check meaningful. A
  child starts with its own independently-rolled `trustThreshold` and an
  empty trust dict/government — nothing about the parent's political life
  is inherited (see `__init__` above).
  *Design choice — technical mechanism ensuring heirs are typed correctly for the `isinstance(c, Locke)` checks elsewhere; not itself a textual claim.*

## `agent.py` — `class Agent` (base class, only the touched methods)

- **`collectResourcesAtCell(self)`** (`249-260`) — One line added:
  `self.recordLandTrespassIfOwned(sugarCollected, spiceCollected)`, inserted
  after pollution handling and before the cell's sugar/spice are reset. This
  ensures every harvest, by every agent type, checks for trespass before the
  cell's resources are cleared for the next timestep.
  *Design choice — the insertion point (where in the base harvesting flow the check runs) is architecture, not textual content.*
- **`recordLandTrespassIfOwned(self, sugarCollected, spiceCollected)`**
  (`262-283`) — New method (Phase 1), generic (not `Locke`-specific)
  trespass detector: if the cell has a living owner and `self` isn't one of
  them, and `self` isn't already a consented licensee, appends a violation
  record to `cell.pendingViolations`. Deliberately does **not** touch
  `lastHarvestedTimestep` — only the owner's own harvest resets the
  abandonment clock (in `processReturnToOwnedLand`), so a claim under
  continuous theft still decays per Locke's spoilage proviso, which is keyed
  to the possessor's own use, not mere third-party contact with the land.
  Because this lives on the base `Agent` class rather than inside `Locke`,
  it fires for any decision model, satisfying "any agent regardless of
  decision model" from the design. **Phase 2 addition**: three lines at the
  end, after the trespass debug print, loop over every living agent in the
  simulation and call `other.resetTrustIn(self)` if `other` has that
  method — i.e. every `Locke` agent, found via `hasattr` duck-typing rather
  than `isinstance(other, Locke)` (this file can't import `ethics.py`;
  `ethics.py` already imports `agent`). This is the *only* new code outside
  `class Locke` in the whole Phase 2 change — all the actual trust-reset
  logic (what "reset" means, the debug message, the trust dict itself) is
  the `Locke.resetTrustIn` method it calls; this is a bare notification
  loop, not a new method of its own.
  *Locke, Sect. 6: "The state of nature has a law of nature to govern it, which obliges every one: and reason, which is that law, teaches all mankind, who will but consult it... no one ought to harm another in his life, health, liberty, or possessions." The law of nature binds everyone, not just fellow property-owners — grounding why this check (and the notification loop appended to it) has to live on the base `Agent` class rather than inside `Locke`.*

## `sugarscape.py` (single-line/single-block changes, no new methods)

- **Agent factory** (`235-236`, inside the agent-creation method) — Adds
  `elif "locke" in agentConfiguration["decisionModel"]: a = ethics.Locke(...)`.
  This is the only place in the whole codebase a `Locke` agent object is
  actually instantiated during simulation setup or dead-agent replacement.
  *Design choice — Python object-instantiation plumbing.*
- **Default configuration dict** (`1914-1916`) — Adds
  `"environmentLandDecayTimesteps": 50`,
  `"environmentLandForcefulCollectionGraceTimesteps": 1`, and (Phase 2)
  `"environmentLandTrustThresholdRange": [4, 8]` as hardcoded defaults.
  This is load-bearing: the config-file-override loop
  (`for opt in configuration: if opt in options: ...`) only applies a
  `config.json` value for a key that *already exists* in this dict — a key
  present only in the JSON file and not here is silently ignored. (This is
  exactly the bug that made the grace-period config fix fail the first time
  it was tried, before this dict entry was added — the trust-threshold key
  was added here from the start to avoid repeating it.)
  *Design choice — Python config-plumbing; see the note on why all three dict entries are load-bearing.*

## `config.json` (`sugarscapeOptions`, value/key changes only)

- **`agentDecisionModels`** (line `17`) — Value changed from `["bentham"]`
  to `["locke"]`, making `locke` the active decision model for this
  scenario's default run.
  *Design choice — scenario configuration value.*
- **`environmentLandDecayTimesteps: 3`** (line `83`, new key) — Overrides
  the code default of `50` down to `3` for this scenario.
  *Design choice (numeric value); the underlying concept is grounded in Sect. 38 — see `forfeitCellClaim` above.*
- **`environmentLandForcefulCollectionGraceTimesteps: 1`** (line `84`, new
  key) — Matches the code default of `1`.
  *Design choice — Locke specifies no time period at all before force becomes legitimate; see Sect. 12/19 under `doForcefulDebtCollection` above.*
- **`environmentLandTrustThresholdRange: [4, 8]`** (line `85`, new key,
  Phase 2) — Matches the code default; the inclusive range each Locke
  agent's own `trustThreshold` is independently drawn from at birth.
  *Design choice — Locke never specifies how much trust-building precedes political society forming; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `gui.py` — `class GUI` (only the touched lines)

- **`self.colors`/`self.governmentColors`/`self.landOwnerColors`**
  (constructor, `~line 26-29`) — Adds, Phase 2, `"noGovernment": "#888888"`
  (neutral gray for any agent not currently in a government) plus two empty
  cache dicts, `self.governmentColors = {}` and `self.landOwnerColors =
  {}`, each populated lazily the first time a given government/land owner
  is rendered (see `findGovernmentColor`/`findOwnerColor` below) — unlike
  tribes/races/decision models, neither the number of governments nor the
  number of distinct land owners is known ahead of time, so their palette
  assignments can't be precomputed at GUI construction. The original,
  now-superseded `"claimed": "#C87850"` fixed-tint color (a single flat
  color for any claimed cell, added when land claims were first
  visualized) is removed — no longer referenced now that claimed cells are
  colored per owner instead.
  *Design choice — visualization only.*
- **`configureAgentColorNames(self)`** (`80-81`, Phase 2) — Adds
  `"Government"` to the list of selectable agent coloring modes.
  *Design choice — visualization only.*
- **`configureEnvironmentColorNames(self)`** (`218`) — Adds `"Land Claims"`
  to the list of selectable environment coloring modes, which previously
  only offered `"Pollution"`.
  *Design choice — visualization only.*
- **`findGovernmentColor(self, government)`** (new, Phase 2) — A
  government is a plain `set()`, which is unhashable, so this keys the
  color cache on `id(government)` instead (stable for the government's
  lifetime, since membership changes mutate the set in place rather than
  replacing it — see `addToGovernment` in `ethics.py`). Assigns the next
  unused color from `self.palette`, cycling by modulo once every palette
  slot has been claimed by some other government.
  *Design choice — visualization only; also one of two places in this codebase (the other being `findOwnerColor` below) that colors a dynamically-unbounded, run-time-discovered category rather than a fixed, config-known one (tribes/races/decision models all precompute their palette slice from a config-known count at GUI construction).*
- **`findLandOwnerColor(self, owners)`** (new) — Takes a cell's `owners`
  dict (`{agent: share}`) and returns a share-weighted average RGB across
  every co-owner's own individual color (from `findOwnerColor`) — a
  single-owner cell renders in exactly that owner's color; a co-owned cell
  blends proportionally to each owner's share, generalizing the existing
  two-color `interpolateColor` blend used elsewhere in this file (e.g.
  sugar/spice coloring) to an arbitrary number of owners.
  *Design choice — visualization only.*
- **`findOwnerColor(self, owner)`** (new) — Assigns and caches one stable
  color per land-owning agent, keyed directly on the agent object (agents
  are already used as dict keys elsewhere in this codebase, e.g.
  `cell.owners` itself, so no `id()`/`.ID` indirection is needed here
  unlike `findGovernmentColor`), cycling through `self.palette` by modulo.
  *Design choice — visualization only.*
- **`lookupFillColor(self, cell)`** (`661-702`, one method with two added
  branches) — Adds an `elif` branch at `669-673` for when
  `activeColorOptions["environment"] == "Land Claims"`: colors an
  unoccupied cell by its normal sugar/spice color, blended 50% toward the
  cell's owner-derived color from `findLandOwnerColor` if `len(cell.owners)
  > 0` — different owners are now visually distinguishable from each other
  (not just claimed vs. unclaimed, which is what this branch did before
  this pass). Also adds (Phase 2) a branch at `683-688` for
  `activeColorOptions["agent"] == "Government"`: duck-types via
  `getattr(agent, "locke", None)` (this file doesn't import `ethics.py`
  either) to find the agent's government, if any, and colors it via
  `findGovernmentColor`; any agent without one — including every non-Locke
  agent, which has no `.locke` at all — gets the neutral `"noGovernment"`
  gray.
  *Design choice — visualization only.*

## `README` (documentation only, no behavior)

- **`agentDecisionModels` entry** — Adds `"locke"` to the `Options:` list and
  a new `Note:` line documenting that trespass detection fires regardless of
  the trespasser's own decision model.
  *Design choice — documentation, not a textual claim.*
- **`environmentLandDecayTimesteps` entry** (new) — Documents the decay
  config key, its Locke-only relevance, and its code default of `50`.
  *Design choice — documentation; concept grounded in Sect. 38, see `forfeitCellClaim` above.*
- **`environmentLandForcefulCollectionGraceTimesteps` entry** (new) —
  Documents the grace-period config key, its Locke-only relevance, and its
  default of `1`.
  *Design choice — documentation; see Sect. 12/19 under `doForcefulDebtCollection` above.*
- **`environmentLandTrustThresholdRange` entry** (new, Phase 2) —
  Documents the trust-threshold-range config key, that it's independently
  drawn per agent at birth and not inherited from a parent, its Locke-only
  relevance, and its default of `[4, 8]`.
  *Design choice — documentation; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `examples/locke_basic.json` (new file, not a class)

A standalone, runnable example scenario for the `locke` decision model, with
its own `__README__` summary field. Notable settings distinct from the main
`config.json`: `agentInheritancePolicy: "children"` (same value as the main
config, so the wealth/land inheritance asymmetry above applies here too),
and `environmentLandDecayTimesteps: 10` (different from both the main
config's `3` and the code default of `50`). It doesn't override
`environmentLandForcefulCollectionGraceTimesteps`, so that scenario runs on
the code default of `1`.

*Design choice — a runnable scenario file, not a textual claim.*
