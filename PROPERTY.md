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
  `restrained` (the Sect. 12 restraint flag), `governmentLandUse`
  (`"closed"`/`"toll"` — the Sect. 124 rule binding non-members in the
  territory), `governmentRedistribution` (`"equal"`/`"proportional"` — how the
  Sect. 138 levy is paid back out), `grievance` (`0.0`; cumulative net loss
  under `proportional`, the fuel for Sect. 240 withdrawal), `lastHarvest` (this
  timestep's gross harvest, for the levy), `lastLevyTimestep` (idempotence
  guard for the once-per-timestep levy pass), `governmentExecutor` (the member
  appointed to collect on the society's behalf — Sect. 126/130), and
  `executorGrievance` (`0.0`; a separate accumulator for the Sect. 156
  complaint, drives executor replacement only, never withdrawal).
  *Design choice — bookkeeping structure, no textual analog. `trustThreshold`, `restrained`, `grievance`, `executorGrievance` are all per-agent and never inherited (Sect. 116/118 for political disposition; Sect. 12 restraint and one's own grievance are personal). The government-law fields (rate, land-use, redistribution, executor) are copied from existing members on join (Sect. 97), not from a parent.*
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
- **`claimCellFor(self, cell, owner)`** (`586-590`) — Sets
  `cell.owners = {owner: 1.0}` (100% single ownership), stamps
  `lastHarvestedTimestep` to the current timestep, and resets
  `consentedAgents`/`consentApprovals` to empty. The ownership-establishing
  primitive, used when a cell is first claimed. Does **not** touch
  `pendingViolations` — a trespass against a *prior* epoch's owner is still
  owed to that owner (see `convertViolationsToDebts`, which credits the
  snapshotted owner, not the current one), so wiping the list here would
  erase a legitimate outstanding claim whenever a decayed cell is re-taken.
  *Locke, Sect. 32: "As much land as a man tills, plants, improves, cultivates, and can use the product of, so much is his property. He by his labour does, as it were, inclose it from the common."*
- **`forfeitCellClaim(self, cell)`** (`592-596`) — The inverse of
  `claimCellFor`: wipes `cell.owners` back to `{}`, resets
  `lastHarvestedTimestep` to `-1`, and clears consent state. Leaves
  `pendingViolations` in place for the same reason as `claimCellFor` — the
  wronged prior owner may still recover the debt if they (or anyone) re-touch
  the cell.
  *Locke, Sect. 38: "if either the grass of his enclosure rotted on the ground, or the fruit of his planting perished without gathering... this part of the earth, notwithstanding his enclosure, was still to be looked on as waste, and might be the possession of any other."*
- **`convertViolationsToDebts(self, cell, timestep)`** (`598-631`) — For
  every pending violation on the cell, splits the stolen `amount` across the
  owners **snapshotted at trespass time** (`violation["owners"]`, falling back
  to current owners for pre-snapshot records) proportional to share, **scaled
  by a reparation rate above parity** — the crediting owner's `governmentRate`,
  or `min(choices)` from `environmentLandReparationRateChoices` for an owner
  not in a government. Skips any snapshotted owner who is the trespasser or is
  no longer alive. Creates one debt record per (owner, trespasser) pair, files
  it on both the creditor's `debtsReceivable` and the debtor's `landDebtsOwed`,
  resets that owner's trust in the trespasser (moment of discovery), then
  clears `pendingViolations`.
  *Locke, Sect. 10: "he who hath received any damage, has... a particular right to seek reparation from him that has done it." Sect. 11 grounds crediting the owner *at the time of the wrong*, not the current claimant — reparation runs offender → injured party, so a decayed-and-re-taken cell must not book a debt against (or, if the re-claimant is the original trespasser, to) the wrong agent. Sect. 12 grounds sizing the debt above parity: the penalty must be "sufficient to make it an ill bargain to the offender" — a net-zero return costs the trespasser nothing. Sect. 11 also grounds the owner trust reset here: the injured party learns of the trespass when it lands on the ledger, wherever they stood when it happened (see `resetTrustIn`).*
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
- **`acquireLandClaim(self, cell)`** (`654-658`) — Thin wrapper calling
  `claimCellFor(cell, self)` and appending the cell to
  `self.locke["claims"]` — the actual "claim this cell" action, reached from
  `collectResourcesAtCell` only after a non-zero harvest.
  *Locke, Sect. 27/28: property is made from what a man "removes out of the state that nature hath provided" — "that labour... added something to them more than nature... and so they became his private right." No removal, no claim; the harvest gate in `collectResourcesAtCell` is what enforces this.*
- **`collectResourcesAtCell(self)`** (`662-680`) — Override of the base
  harvesting method. Captures `cell.sugar + cell.spice` **before**
  `super().collectResourcesAtCell()` (the parent zeroes the cell at the end,
  so the amount can't be read afterwards), records it as
  `self.locke["lastHarvest"]` every timestep — before the gate, so a
  no-harvest timestep records `0.0` and is not levied on a stale value — then
  **returns immediately if nothing was harvested**. Only on a non-zero harvest
  does it dispatch: claim an unclaimed cell if unclaimed land still exists
  nearby, or, if `self` is already an owner, call `processReturnToOwnedLand`.
  *Locke, Sect. 27 (claim creation) and Sect. 38 (claim retention) both key on gathering, not presence — "if... the fruit of his planting perished without gathering... this part of the earth, notwithstanding his enclosure, was still to be looked on as waste." Standing on a depleted cell is not gathering, so it neither creates nor refreshes a claim. The dispatch targets each carry their own citation.*
- **`processReturnToOwnedLand(self, cell)`** (`679-683`) — Re-stamps
  `lastHarvestedTimestep` and calls `convertViolationsToDebts` — the "owner
  comes back and gathers from land that was stolen from" moment. Only reached
  after a non-zero harvest (see `collectResourcesAtCell`), so an owner parked
  on an exhausted cell no longer holds the claim against `processLandAbandonment`.
  *Design choice — the specific "wait until the owner returns" timing is invented; the reparation right it triggers is grounded in Sect. 10, and the harvest gate in Sect. 38 (see `collectResourcesAtCell`). Consequence: pending violations on a claim the owner only ever revisits without gathering are not booked until someone next harvests the cell (still credited to the snapshotted victim via `convertViolationsToDebts`), or are lost if the claim decays first — consistent with an abandoning owner forfeiting the claim going forward.*
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
- **`doForcefulDebtCollection(self)`** (`782-843`) — Runs every timestep; for
  every neighboring agent, for every debt that neighbor owes older than
  `environmentLandForcefulCollectionGraceTimesteps`, seizes whatever
  sugar/spice the debtor holds (capped at the debt) and pays it to the
  creditor — **but only if `self` is the creditor, or `self` is its
  government's `governmentExecutor` and the creditor is a fellow member**.
  A non-executor member does not collect for others; a governmentless agent
  collects only its own. When a seizure lands on a `Locke` debtor its
  `restrained` flag is set (Sect. 12). If the executor collects its *own* debt
  in a step where a fellow member's enforceable one goes unreached, a
  `Sect. 156` line is logged.
  *Sect. 19 grounds why self-help force is legitimate at all — there is no common judge/magistracy to appeal to. Sect. 12 grounds the cap: "sufficient to make it an ill bargain to the offender." Sect. 11 grounds the ungated **self**-collection: the injured party's right to reparation is gated by nothing. Sect. 126 grounds the appointment itself — the state of nature "wants power... to give [the sentence] due execution", so the society names an executor. Sect. 130 grounds routing collection through that one office: members "engage their natural force... to assist the executive power of the society", not to freelance for one another. Sect. 156 grounds the neglect line — the executor's power is "a fiduciary trust... for the safety of the people", and self-collection while a fellow member's debt goes unreached is that trust visibly unfulfilled (not Sect. 222 — no property is taken). An earlier "member-visible ledger" version let every member collect for every fellow member; the executor supersedes it (Sect. 126's step Locke actually describes).*
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
- **`attemptGovernmentFormation(self, other)`** (`859-890`) — Called from
  `increaseTrust` with `self` = the agent whose trust toward `other` just
  crossed its own `trustThreshold`. Returns early if that threshold isn't met.
  Then: if `self` is already in a government, does nothing (one at a time). If
  `other` is in a government, `self` joins it (`addToGovernment`) on its own
  consent alone. Otherwise, only if `other`'s trust toward `self` has also
  crossed `other`'s threshold, founds a new government — a bare `set()` — and
  votes **four** laws over the founders: `voteReparationRate` (the reparation
  multiplier), `voteLandUse` (closed/toll), `voteRedistribution` (equal/
  proportional), `voteExecutor` (who collects on the society's behalf). Zeros
  both founders' `grievance` and `executorGrievance`.
  *Locke, Sect. 95-99 grounds forming political society by mutual consent — "when any number of men have so consented to make one community or government, they are thereby presently incorporated" — and is why a government is a bare `set()`, not a class: nothing more than its members' collected consent. Sect. 99 grounds the bilateral requirement for **founding** (each founder consents); Sect. 89 grounds **joining** an existing body on the joiner's consent alone ("men being... by nature all free, equal, and independent, no one can be... subjected to the political power of another, without his own consent"). The one-government-at-a-time rule is a design choice — Sect. 121 is about a tacit consenter's freedom to leave versus an express consenter's binding, not about exclusivity.*
- **`voteReparationRate(self, founders)`** (`892-906`) — Each founder's
  preferred rate is one entry from `sorted(environmentLandReparationRateChoices)`,
  picked by `round(min(1.0, claims / environmentLandReparationStakeReference) *
  (len(choices) - 1))` — its claimed-cell count against a fixed reference. The
  government adopts the median of the founders' preferred rates (lower of the
  two middle values for an even count). Stored as `governmentRate`.
  *Locke, Sect. 12 gives only a floor ("an ill bargain"), not a number, so the rate is set by collective decision. Sect. 95-96: one equal vote each, the body moving "whither the greater force carries it, which is the consent of the majority" — hence the median. Sect. 138 grounds keying the preference to holdings. The stake-reference constant and the choice menu are design choices.*
- **`voteLandUse(self, members)`** (`908-918`) — The Sect. 124 standard binding
  non-members in the territory. A member holding at least the government's mean
  claim count votes `"toll"` (it has toll income to gain), the rest vote
  `"closed"`; majority, tie → `"toll"`. Voted once at formation, never
  re-legislated — Sect. 153's "legislated once" story holds for it.
  *Locke, Sect. 119: one who enjoys "any part of the dominions of any government... is thereby bound to obey the laws of that government." The territory (union of members' claims) is the dominion, so a government can bind a non-member standing in it; under `"toll"` there is a lawful path (a per-harvest fee), under `"closed"` a non-member's harvest is categorically a trespass. Sect. 124 (government exists to protect property under "a standing rule") grounds this being a rule, not just a penalty. The mean-relative vote and the fee formula are design choices.*
- **`voteRedistribution(self, members)`** (`919-931`) — The contested law: how
  the per-timestep levy is paid back out. A member holding **strictly more**
  than the government's mean claim count votes `"proportional"`, the rest vote
  `"equal"`; majority, tie → `"equal"`. Re-voted whenever the roster changes
  (`addToGovernment`, `doInheritance`) or grievance forces a review — the one
  law that reconvenes the legislative (Sect. 153).
  *Locke, Sect. 138/139: "the supreme power cannot take from any man any part of his property without his own consent" — the levy is exactly that, a taking the aggrieved minority did not consent to. `"equal"` returns each member its own levy (the power held, not abused); `"proportional"` moves value from the land-poor to the land-rich — Sect. 199, power "to his own private separate advantage." So this is Lockean not as legitimate legislation (Sect. 140 taxation funds operations; this funds nothing) but as the wrong of Sect. 222 ("they endeavour to take away, and destroy the property of the people"), which forfeits trust and licenses withdrawal (Sect. 240). The mean-relative vote and the whole levy amount are design choices.*
- **`voteExecutor(self, members)`** (`936-946`) — The fourth founding law
  (Sect. 126). Preference does **not** track landholding — §126's defect is
  inability to *reach* the transgressor, so the pick is the member with the
  greatest reach = `findVision() + findMovement()`, ties broken by lowest ID.
  Because reach is an objective shared fact the ballot is degenerate (every
  member names the same agent) and it reduces to an argmax — kept in vote form
  for parity with the other three, noted here.
  *Locke, Sect. 126 grounds the appointment (the state of nature "wants power... to give [the sentence] due execution"). Sect. 152 grounds its being an office, replaceable "at pleasure", not a right — hence the deterministic tie-break rather than a natural entitlement. The vision+movement metric is a design choice standing in for "capacity to execute a judgment on a distant party."*
- **`addToGovernment(self, government, newMember)`** (`947-971`) — Adds
  `newMember` to the shared `set()`, points their `locke["government"]` at it,
  copies the standing `governmentRate` / `governmentLandUse` /
  `governmentRedistribution` / `governmentExecutor` onto them, zeros their
  `grievance` and `executorGrievance`, then calls `reviewRedistribution` **and**
  `reviewExecutor` — a changed roster is an occasion for the legislative to
  re-vote both of those (Sect. 153). Rate and land-use are not re-legislated.
  *Locke, Sect. 97 grounds binding the joiner to the standing laws without a re-founding: consenting to incorporate "puts himself under an obligation... to submit to the determination of the majority." (Not Sect. 122 — that is about tacit compliance not conferring membership.)*
- **`reviewRedistribution(self, government)`** (`973-988`) — Re-runs only
  `voteRedistribution` over the current roster; if the rule changed, writes it
  to every member and returns `True`. A no-op if the land-rich/land-poor
  balance is unchanged — so under a stable roster and holdings, `"proportional"`
  persists and grievance climbs to withdrawal (Sect. 222–243: dissolution, not
  reform, is the remedy for a legislature turned to faction advantage).
  *Sect. 153: "it is not necessary... that the legislative should be always in being" — it meets on occasion, and a roster change or a failing law is an occasion.*
- **`reviewExecutor(self, government)`** (`989-1006`) — Re-runs `voteExecutor`;
  if the appointment changed, writes it to every member, logs `(Sect. 152)`,
  returns `True`. Returns `False` when the sitting executor is still the
  highest-reach member — the maladministration cannot be fixed by replacement,
  and (per design) the government does **not** dissolve over it; the complaint
  stands. That inertness is itself the Sect. 126 finding: a magistracy with no
  power to reach the debtor is the very defect it was appointed to cure.
  *Locke, Sect. 152: the executive is "accountable to [the legislative], and may at pleasure be changed and displaced"; Sect. 153: the legislative resumes power "to punish for any maladministration against the laws."*
- **`territoryGovernmentFor(self, cell)`** (`965-975`) — Returns the `set()`
  government of the first living owner of `cell` that belongs to one, else
  `None`. Derived, not stored — territory moves as claims are made and decay.
  *Locke, Sect. 119: the dominion is the members' land.*
- **`dissolveGovernmentIfUnviable(self, government)`** (`1009-1026`) — If fewer
  than two members remain, nulls every survivor's
  `government`/`governmentRate`/`governmentLandUse`/`governmentRedistribution`/`governmentExecutor`,
  zeros their `grievance` and `executorGrievance`, clears the set. Trust scores
  persist. Called from `doInheritance` (death) and `doGovernanceReview`
  (withdrawal).
  *Locke, Sect. 211: a society dissolves when the body "can no longer act as one"; a single member is not a body. The survivor "returning to the state of nature" with its trust intact matches Sect. 211's sequel — dissolved members "are at liberty... by erecting a new legislative."*
- **`runLevyPass(self, government)`** (`992-1024`) — Once per timestep per
  government (the `lastLevyTimestep` guard makes later members skip; the roster
  is snapshotted so shuffled run-order and any same-timestep withdrawal do not
  change the denominator). Levies a flat per-capita
  `environmentLandLevyFraction * mean(lastHarvest)` from every member (sugar
  first, then spice, capped at what it holds); redistributes the pool the same
  timestep — `"equal"`: each gets its own levy back (net-zero); `"proportional"`:
  each gets `pool * (its claims / total claims)`. Then
  `grievance = max(0.0, grievance - net)` per member.
  *Sect. 138 (the taking); Sect. 199 (the `"proportional"` concentration). The flat per-capita basis is chosen so `"proportional"` concentrates toward the land-rich by construction, independent of any harvest/claims correlation. Net-zero at the body level; a persistent common fund is out of scope.*
- **`doGovernanceReview(self)`** (`1073-1131`) — Called from `doTrading`. First,
  the **executor-neglect channel**: a non-executor member counts its own debts
  that ripened (`createdTimestep + collectionGrace`) at least
  `environmentLandExecutorNeglectGraceTimesteps` ago and whose debtor is alive
  and solvent, and adds `environmentLandExecutorNeglectPenalty` per such debt to
  its `executorGrievance` (the earlier `doForcefulDebtCollection` already tried
  the member's own reach, so anything still outstanding is genuinely beyond it).
  Then the levy pass; if this member's `grievance` exceeds
  `environmentLandGrievanceThreshold` it **withdraws** (§240) — leaves the set,
  nulls its government fields, zeros both grievances, then
  `dissolveGovernmentIfUnviable`, then `reviewExecutor` if the body survives (a
  withdrawing executor must be replaced). Else: if summed `grievance` exceeds
  `environmentLandGovernmentReviewThreshold`, `reviewRedistribution` (decay on a
  change); and if summed `executorGrievance` exceeds
  `environmentLandExecutorReviewThreshold`, `reviewExecutor` (zero everyone's
  `executorGrievance` on a change).
  *Locke, Sect. 240 ("the people shall be judge" of whether the legislature has broken trust) — each member judging its own government; Sect. 225 ("a long train of abuses") — cumulative, not one bad law. Sect. 156/152 ground the second channel: the executor holds "a fiduciary trust... for the safety of the people" and is displaced by the legislative for maladministration — but replacement, not dissolution, and only if there is a better candidate. This is **not** Sect. 125's "known and indifferent judge": self-judgment is what Sect. 125 identifies as the problem. Sect. 125 stays unaddressed — the model has no contested facts, only transparent transfers.*
- **`resetTrustIn(self, violator)`** (`1054-1058`) — Zeroes
  `self.locke["trust"][violator.ID]` if nonzero. Called on the Locke agents
  who could actually *perceive* a trespass: those adjacent to the trespassed
  cell at that timestep (via the neighbours-only loop in
  `agent.recordLandTrespassIfOwned`, see `agent.py` below), plus each crediting
  owner when the violation is booked as a debt (in `convertViolationsToDebts`).
  Not the whole population.
  *Locke, Sect. 94: people act on what they perceive — "it hinders not men from feeling... when they perceive, that any man... is out of the bounds of the civil society which they are of". Instant grid-wide knowledge of a transgression is not perception. An earlier Phase 2 version reset every living Locke agent's trust at once, citing Sect. 8 ("a trespass against the whole species") — but Sect. 8 establishes only that the wrong concerns everyone, not that everyone learns of it. Sect. 11 grounds the owner carve-out: the injured party has a particular standing and finds out when the debt lands on the ledger, wherever they were standing. Zeroing the score rather than decaying it is a design choice.*
- **`doTrading(self)`** (`1060-1067`) — Override that runs the base agent's
  ordinary trading first (`super().doTrading()`), then the land-specific
  behaviours in order: consent grants, buyouts, forceful collection, trust
  accrual, and `doGovernanceReview` (executor neglect + levy + withdrawal +
  re-legislation + executor replacement).
  *Design choice — pure call-sequencing wrapper.*
- **`findBestEthicalCell(self, cells, greedyBestCell=None)`** (`863-876`) —
  Override of the base movement-decision hook; scores every candidate cell
  via `findEthicalValueOfCell` and picks the highest-scoring one. This is
  what actually decides where a `Locke` agent moves each timestep.
  *Design choice — generic movement-selection architecture shared by every decision model in the codebase, not Locke-specific content.*
- **`findEthicalValueOfCell(self, cell)`** (`937-953`) — Computes a cell's
  attractiveness for the movement decision as `sugar + spice`, forced to `0`
  when the cell is owned by another living agent and `self` has no standing
  consent on it — and, if `self.locke["restrained"]` is set, to
  `-(sugar + spice) - 1` (negative, richer claims avoided harder). A Locke
  agent places no value on entering foreign land; a restrained one scores it
  below its own worst legitimate option. A consented harvester
  (`cellConsentedAgents`) and an owner on their own cell are unaffected either
  way.
  *Locke, Sect. 27: a labour-made claim "excludes the common right of other men" — exclusion is the primary effect of property. Hard exclusion in the movement score, not a tunable discount; an unrestrained Locke agent still trespasses when every reachable cell scores 0 (boxed in by claims), and non-`Locke` agents (which never run this method) trespass freely — so the trespass → debt → reparation machinery stays exercised. Sect. 12: punishment serves "reparation and restraint" — the negative score is the restraint half, driving a previously-collected-from agent to enter claimed land only when literally every reachable cell belongs to someone else. Restricted to Locke agents (only they carry the flag); implemented for completeness — in practice Locke agents rarely trespass under hard exclusion, so it seldom fires. The exclusion is flat across agents — Sect. 27 excludes everyone's common right equally, not weighted by trust or shared government.*
- **`doInheritance(self)`** (`1140-1179`) — Runs the base wealth-inheritance
  mechanic first, then splits/forfeits the deceased's land shares (Locke
  children co-own; otherwise the share reverts). Discharges the deceased's
  debts/receivables, calls `government.discard(self)`, then
  `dissolveGovernmentIfUnviable`, and — if the body still has two or more
  members — `reviewRedistribution` **and** `reviewExecutor` over the survivors
  (a death changes the roster — an occasion for the legislative, Sect. 153; and
  the executor may have been the one who died, Sect. 152). Trust scores are left
  intact.
  *Locke, Sect. 72 grounds the land-splitting half ("in certain proportions, according to the law and custom of each country" — the equal split is within that space). Sect. 211 grounds the dissolution (see `dissolveGovernmentIfUnviable`). The debt-discharge half is a plain design choice — Chapter V does not say whether a reparation debt survives a party's death.*
- **`updateValues(self)`** (`1138-1142`) — Per-timestep hook that triggers
  `processLandAbandonment` and `settleDebtsVoluntarily`.
  *Design choice — per-timestep orchestration hook.*
- **`spawnChild(self, childID, birthday, cell, configuration)`**
  (`1143-1144`) — Returns a new `Locke` instance for reproduction, so a
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
  (`262-317`) — Generic (not `Locke`-specific) trespass detector: if the cell
  has a living owner and `self` isn't one of them and isn't a consented
  licensee, it would append a violation record to `cell.pendingViolations`
  (with a snapshot of the `owners` dict, so the eventual debt is credited to
  whoever was wronged then — see `convertViolationsToDebts`). **Territory
  interception first** (Sect. 119): a duck-typed loop over `owners`
  (`getattr(owner, "locke", None)["government"]`, no import of `ethics`) finds
  whether the cell is in a government's territory; if it is and `self` is not a
  member and the government's `governmentLandUse` is `"toll"`, `self` is charged
  `harvest * environmentLandUseTollFactor` (paid pro rata to the owners) — and
  if `self` can pay it in full, the harvest is lawful and the method `return`s
  with **no violation recorded**. `"closed"`, an unpayable toll, or a
  non-territory cell fall through to the ordinary violation path. Non-`Locke`
  agents pay tolls too (they hold sugar/spice) but the levy/grievance machinery
  never touches them. Deliberately does **not** touch
  `lastHarvestedTimestep` — only the owner's own harvest resets the
  abandonment clock (in `processReturnToOwnedLand`), so a claim under
  continuous theft still decays per Locke's spoilage proviso, which is keyed
  to the possessor's own use, not mere third-party contact with the land.
  Because this lives on the base `Agent` class rather than inside `Locke`,
  it fires for any decision model, satisfying "any agent regardless of
  decision model" from the design. **Trailing block**: after the trespass
  debug print, a loop over `self.cell.findNeighborAgents()` calls
  `other.resetTrustIn(self)` on any neighbour that has the method — i.e. the
  `Locke` agents adjacent to the trespassed cell, found via `hasattr`
  duck-typing (this file can't import `ethics.py`; `ethics.py` already imports
  `agent`). All the trust-reset logic lives in `Locke.resetTrustIn`; this is a
  bare notification loop. (An earlier version looped over the whole living
  population — see `resetTrustIn` for why that was scoped down to witnesses.)
  *Locke, Sect. 6: "The state of nature has a law of nature to govern it, which obliges every one... no one ought to harm another in his life, health, liberty, or possessions" — the law of nature binds everyone, so the trespass check itself lives on the base `Agent` class. Sect. 94 grounds the notification loop's neighbours-only scope: trust is lost by those who perceive the trespass.*

## `sugarscape.py` (single-line/single-block changes, no new methods)

- **Agent factory** (`235-236`, inside the agent-creation method) — Adds
  `elif "locke" in agentConfiguration["decisionModel"]: a = ethics.Locke(...)`.
  This is the only place in the whole codebase a `Locke` agent object is
  actually instantiated during simulation setup or dead-agent replacement.
  *Design choice — Python object-instantiation plumbing.*
- **Default configuration dict** (`~1914-1928`) — Adds, as hardcoded defaults:
  `"environmentLandDecayTimesteps": 50`,
  `"environmentLandExecutorNeglectGraceTimesteps": 5`,
  `"environmentLandExecutorNeglectPenalty": 0.5`,
  `"environmentLandExecutorReviewThreshold": 15.0`,
  `"environmentLandForcefulCollectionGraceTimesteps": 1`,
  `"environmentLandGovernmentReviewThreshold": 10.0`,
  `"environmentLandGrievanceDecay": 0.5`,
  `"environmentLandGrievanceThreshold": 6.0`,
  `"environmentLandLevyFraction": 0.3`,
  `"environmentLandReparationRateChoices": [1.25, 1.5, 2.0, 3.0]`,
  `"environmentLandReparationStakeReference": 8`,
  `"environmentLandTrustThresholdRange": [4, 8]`, and
  `"environmentLandUseTollFactor": 0.35`.
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
- **`environmentLandForcefulCollectionGraceTimesteps: 1`** (line `84`, new
  key) — Matches the code default of `1`.
  *Design choice — Locke specifies no time period at all before force becomes legitimate; see Sect. 12/19 under `doForcefulDebtCollection` above.*
- **`environmentLandReparationRateChoices: [1.25, 1.5, 2.0, 3.0]`** /
  **`environmentLandReparationStakeReference: 8`** (new keys) — Match the code
  defaults; the menu a government votes over and the claim count that maps to
  the harshest choice.
  *Design choice (the menu and the reference constant); the above-parity requirement is Sect. 12 and the vote is Sect. 95-96 — see `voteReparationRate` above.*
- **The governance tuning keys** — `environmentLandUseTollFactor` (`0.35`),
  `environmentLandLevyFraction` (`0.9`), `environmentLandGrievanceThreshold`
  (`10.0`), `environmentLandGovernmentReviewThreshold` (`10.0`),
  `environmentLandGrievanceDecay` (`0.5`), and the three executor keys
  `environmentLandExecutorNeglectGraceTimesteps` (`5`),
  `environmentLandExecutorNeglectPenalty` (`0.5`),
  `environmentLandExecutorReviewThreshold` (`15.0`). Toll well below `1.0` so
  `"toll"` and `"closed"` differ; the rest tuned against 250-step debug runs so
  that withdrawal (levy grievance) is a recurring minority event and executor
  replacement fires on roster churn — Sect. 225/230.
  *Design choices (all the numbers); the mechanisms are Sect. 119/124 (toll), Sect. 138/199 (levy), Sect. 240 (withdrawal), Sect. 126/152/156 (executor) — see `voteLandUse` / `voteRedistribution` / `voteExecutor` / `doGovernanceReview` above.*
- **`environmentLandTrustThresholdRange: [1, 1]`** (new key) — Overrides the
  code default `[4, 8]` down for this scenario, so trust accrues fast and
  governments grow to many members — which the redistribution/rebellion
  machinery needs to have bodies to act on.
  *Design choice — Locke never specifies how much trust-building precedes political society forming; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `gui.py` — `class GUI` (only the touched lines)

- **`self.colors`/`self.governmentColors`** (constructor, `~line 26-28`) —
  Adds `"noGovernment": "#888888"` (neutral gray for any agent not
  currently in a government), `"executor": "#FFB000"` and
  `"governmentMember": "#00A0A0"` (the two flat tones for the Executor agent
  mode), and an empty `self.governmentColors = {}`
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
  and `"Executor"` (Phase 4) to the selectable agent coloring modes.
  *Design choice — visualization only.*
- **`configureEnvironmentColorNames(self)`** (`218`) — Adds `"Property"` and
  `"Territory"` to the selectable environment coloring modes (previously only
  `"Pollution"`).
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
  The **`"Executor"` agent branch** (Phase 4) is the same duck-typed lookup,
  three flat tones: `"executor"` gold when `locke["governmentExecutor"] is
  agent`, `"governmentMember"` teal for any other member, `"noGovernment"`
  gray otherwise. The **`"Territory"` environment branch** (Phase 4) is the
  Property branch with one extra step: for a claimed cell it walks
  `cell.owners`, and if an owner has a government returns that government's
  `findGovernmentColor` (so the same government's land and — under the
  `"Government"` / `"Executor"` agent mode — its members read in the same
  palette colour); a claimed but governmentless cell falls back to the flat
  `"claimed"` tint, unclaimed to `"unclaimed"`. Selecting an environment
  *and* an agent mode still shows only the agent colour on an occupied cell
  (agent branches take priority — unchanged, original behaviour).
  *Design choice — visualization only. `"Territory"` and `"Executor"` are new peer modes, not overlays on `"Property"` / `"Government"`; the two reverted elaborations above were about blending signals on one cell, which these do not do.*

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
- **`environmentLandExecutorNeglectGraceTimesteps` /
  `environmentLandExecutorNeglectPenalty` / `environmentLandExecutorReviewThreshold`
  entries** (new) — Document the executor neglect window (measured from when a
  debt ripens), the per-debt-per-timestep grievance, and the summed threshold
  that reconvenes the government to re-vote its executor; all Locke-only.
  *Design choice — documentation; see `voteExecutor` / `reviewExecutor` above.*
- **`environmentLandReparationRateChoices` / `environmentLandReparationStakeReference`
  entries** (new) — Document the reparation-rate menu, the founding vote, the
  lone-owner floor, and the stake reference; both Locke-only.
  *Design choice — documentation; see `voteReparationRate` above.*
- **`environmentLandUseTollFactor` / `environmentLandLevyFraction` /
  `environmentLandGrievanceThreshold` / `environmentLandGovernmentReviewThreshold`
  / `environmentLandGrievanceDecay` entries** (new) — Document the toll fraction,
  the levy fraction, and the three grievance thresholds; all Locke-only.
  *Design choice — documentation; see `voteLandUse` / `voteRedistribution` / `doGovernanceReview` above.*
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
and the reparation / toll / levy / grievance / executor keys set to the same
values as the main config so the governance machinery is exercised when the
example is run.

*Design choice — a runnable scenario file, not a textual claim.*
