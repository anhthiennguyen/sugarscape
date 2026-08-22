# Property (the `locke` decision model)

A complete, source-order reference to every file the `locke` branch has ever
touched (per `git diff a46ec6f..HEAD --stat`, the commit before the `Locke`
class existed), every class in those files that changed, and every method in
those classes — or, for single-line/config changes, the line itself.

## `ethics.py` — `class Locke(agent.Agent)` (`ethics.py:552-849`)

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
  *Design choice — the co-owner voting data structure has no textual basis; Locke never describes joint ownership or how joint owners must agree.*
- **`cellConsentApprovals(self, cell)`** (`567-570`) — Lazily creates and
  returns `cell.consentApprovals`, a `{candidate: {owners who voted yes}}`
  dict tracking in-progress majority votes to admit a new consented
  harvester.
  *Design choice — accessor plumbing.*
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
  *Locke, Sect. 47: "And thus came in the use of money, some lasting thing that men might keep without spoiling, and that by mutual consent men would take in exchange for the truly useful, but perishable supports of life."*
- **`doLandConsentGrants(self)`** (`695-727`) — Runs every timestep for
  every cell the agent co-owns; for each agent adjacent to that cell not
  yet consented, records this owner's approval vote, and once accumulated
  approvals exceed 50% of ownership share, charges the candidate the cell's
  current `sugar + spice` value (with a 50-metabolism-timestep reserve
  buffer) split pro rata across all owners, then marks the candidate
  consented.
  *Locke, Sect. 120 lists "permission" alongside inheritance and purchase as a valid means by which another may come to enjoy land — grounding owner-granted consent in general; the majority-by-share voting mechanism and the fee formula are both design choices with no textual basis.*
- **`doLandBuyoutOffers(self)`** (`729-752`) — Runs every timestep; for
  every cell adjacent to the agent's current position that it doesn't
  itself own, if that cell lies outside the current owner's own foraging
  range, offers to buy that owner's share outright at
  `(maxSugar + maxSpice) * share` (again with the 50-metabolism-timestep
  reserve buffer), paying directly and calling `transferShare`.
  *Locke, Sect. 120: "Whoever therefore, from thenceforth, by inheritance, purchase, permission, or otherways, enjoys any part of the land... must take it with the condition it is under." The buyout price formula itself is a design choice.*
- **`doForcefulDebtCollection(self)`** (`754-782`) — Runs every timestep;
  for every neighboring agent, for every debt that neighbor owes (to
  anyone, since debts can be owed by any agent type), once the debt is
  older than `environmentLandForcefulCollectionGraceTimesteps`, seizes
  whatever sugar/spice the debtor currently has (not limited to an
  above-metabolism reserve) and pays it to the creditor.
  *Locke, Sect. 19: "Thus a thief, whom I cannot harm, but by appeal to the law, for having stolen all that I am worth, I may kill, when he sets on me to rob me... because the law... permits me my own defence, and the right of war."*
- **`doTrading(self)`** (`784-788`) — Override that runs the base agent's
  ordinary sugar/spice trading first (`super().doTrading()`), then the
  three land-specific behaviors above in order: consent grants, buyouts,
  forceful collection.
  *Design choice — pure call-sequencing wrapper.*
- **`findBestEthicalCell(self, cells, greedyBestCell=None)`** (`790-802`) —
  Override of the base movement-decision hook; scores every candidate cell
  via `findEthicalValueOfCell` and picks the highest-scoring one. This is
  what actually decides where a `Locke` agent moves each timestep.
  *Design choice — generic movement-selection architecture shared by every decision model in the codebase, not Locke-specific content.*
- **`findEthicalValueOfCell(self, cell)`** (`804-809`) — Computes a cell's
  attractiveness as `sugar + spice`, with a conditional multiply by `1.0`
  when the cell is owned by someone else without consent — currently a
  no-op, so ownership has zero effect on movement choice.
  *Design choice — currently a no-op stub; there is no implemented concept here to cite.*
- **`doInheritance(self)`** (`811-839`) — Runs the base wealth-inheritance
  mechanic first (`super().doInheritance()`), then for every claimed cell,
  either splits the deceased's share evenly across all living `Locke`
  children (co-ownership) or, if none exist, removes the deceased's share
  outright; forfeits the cell entirely if no owners remain afterward. Also
  discharges all of the deceased's outstanding debts/receivables.
  *Locke, Sect. 72: "the possession of the father being the expectation and inheritance of the children, ordinarily in certain proportions, according to the law and custom of each country." Locke explicitly leaves the split mechanism to "law and custom," so the specific choice of an equal split among every living child is a design choice within a space Locke deliberately left open.*
- **`updateValues(self)`** (`841-844`) — Per-timestep hook (calls base
  `super().updateValues()`) that triggers `processLandAbandonment` and
  `settleDebtsVoluntarily` — the two behaviors that happen automatically
  every timestep regardless of the agent's location.
  *Design choice — per-timestep orchestration hook, architecture not content.*
- **`spawnChild(self, childID, birthday, cell, configuration)`**
  (`846-847`) — Returns a new `Locke` instance for reproduction, so a
  `Locke` agent's children are also `Locke` agents by default. This is what
  makes every `isinstance(c, Locke)` heir-eligibility check meaningful.
  *Design choice — technical mechanism ensuring heirs are typed correctly for the `isinstance(c, Locke)` checks elsewhere; not itself a textual claim.*

## `agent.py` — `class Agent` (base class, only the touched methods)

- **`collectResourcesAtCell(self)`** (`249-260`) — One line added:
  `self.recordLandTrespassIfOwned(sugarCollected, spiceCollected)`, inserted
  after pollution handling and before the cell's sugar/spice are reset. This
  ensures every harvest, by every agent type, checks for trespass before the
  cell's resources are cleared for the next timestep.
  *Design choice — the insertion point (where in the base harvesting flow the check runs) is architecture, not textual content.*
- **`recordLandTrespassIfOwned(self, sugarCollected, spiceCollected)`**
  (`262-278`) — New method, generic (not `Locke`-specific) trespass
  detector: if the cell has a living owner and `self` isn't one of them,
  and `self` isn't already a consented licensee, appends a violation record
  to `cell.pendingViolations`. Deliberately does **not** touch
  `lastHarvestedTimestep` — only the owner's own harvest resets the
  abandonment clock (in `processReturnToOwnedLand`), so a claim under
  continuous theft still decays per Locke's spoilage proviso, which is keyed
  to the possessor's own use, not mere third-party contact with the land.
  Because this lives on the base `Agent` class rather than inside `Locke`,
  it fires for any decision model, satisfying "any agent regardless of
  decision model" from the design.
  *Locke, Sect. 6: "The state of nature has a law of nature to govern it, which obliges every one: and reason, which is that law, teaches all mankind, who will but consult it... no one ought to harm another in his life, health, liberty, or possessions." The law of nature binds everyone, not just fellow property-owners — grounding why this check has to live on the base `Agent` class rather than inside `Locke`.*

## `sugarscape.py` (single-line/single-block changes, no new methods)

- **Agent factory** (`235-236`, inside the agent-creation method) — Adds
  `elif "locke" in agentConfiguration["decisionModel"]: a = ethics.Locke(...)`.
  This is the only place in the whole codebase a `Locke` agent object is
  actually instantiated during simulation setup or dead-agent replacement.
  *Design choice — Python object-instantiation plumbing.*
- **Default configuration dict** (`1914-1915`) — Adds
  `"environmentLandDecayTimesteps": 50` and
  `"environmentLandForcefulCollectionGraceTimesteps": 1` as hardcoded
  defaults. This is load-bearing: the config-file-override loop
  (`for opt in configuration: if opt in options: ...`) only applies a
  `config.json` value for a key that *already exists* in this dict — a key
  present only in the JSON file and not here is silently ignored. (This is
  exactly the bug that made the grace-period config fix fail the first time
  it was tried, before this dict entry was added.)
  *Design choice — Python config-plumbing; see the note on why both dict entries are load-bearing.*

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
  *Design choice — Locke specifies no time period at all before force becomes legitimate; see Sect. 19 under `doForcefulDebtCollection` above.*

## `gui.py` — `class GUI` (only the touched lines)

- **`self.colors` dict** (constructor, `~line 26`) — Adds
  `"claimed": "#C87850"`, the tint color blended into a claimed cell's
  normal color.
  *Design choice — visualization only.*
- **`configureEnvironmentColorNames(self)`** (`218`) — Adds `"Land Claims"`
  to the list of selectable environment coloring modes, which previously
  only offered `"Pollution"`.
  *Design choice — visualization only.*
- **`lookupFillColor(self, cell)`** (`661-665`) — Adds an `elif` branch for
  when `activeColorOptions["environment"] == "Land Claims"`: colors an
  unoccupied cell by its normal sugar/spice color, blended 50% toward the
  `"claimed"` tint if `len(cell.owners) > 0` — a binary claimed/unclaimed
  check, not proportional to share count.
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
  *Design choice — documentation; see Sect. 19 under `doForcefulDebtCollection` above.*

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
