# Property (the `locke` decision model)

This document describes the `locke` agent decision model as implemented on the
`locke` branch: a Lockean theory of property (land is claimed by labor, lost
through non-use, defended through reparation and force, licensed through
consent, and passed down through inheritance) expressed as Sugarscape agent
rules. It covers what is built (Phase 1: property) and calls out what is
explicitly deferred (Phase 2: trust and government).

Implementation lives in `ethics.Locke` (`ethics.py:552-849`), with one piece of
shared infrastructure in the base `agent.Agent` class
(`agent.py:249-278`) so that land claims are enforceable against agents of
*any* decision model, not just other `locke` agents.

## Design source

The rules below were specified as a set of design paragraphs (not derived
from the code), cross-checked against Locke's *Second Treatise of Government*,
Chapter V ("Of Property") and Chapter VIII ("Of the Beginning of Political
Societies"). Where the implementation diverges from those paragraphs, or adds
behavior the paragraphs don't specify, it's called out explicitly in
[Implementation details not covered by the design](#implementation-details-not-covered-by-the-design)
below.

## Data model

Land ownership and its consequences are stored as plain attributes bolted
onto `Cell` and `Agent` objects on first use, via `hasattr`-guarded accessor
methods on `Locke` (`ethics.py:557-580`):

| Attribute | Lives on | Meaning |
|---|---|---|
| `cell.owners` | `Cell` | `{agent: share}` — fractional ownership of the cell. A cell with no entry, or an empty dict, is unclaimed. |
| `cell.lastHarvestedTimestep` | `Cell` | Timestep this cell was last harvested by *anyone* (owner, licensee, or trespasser). Drives abandonment. |
| `cell.consentedAgents` | `Cell` | Set of agents who have paid for and received standing permission to harvest this cell. |
| `cell.consentApprovals` | `Cell` | `{candidate_agent: {owners who have voted to admit them}}` — in-progress consent votes. |
| `cell.pendingViolations` | `Cell` | List of `{trespasser, cell, amount, timestep}` — thefts not yet converted to debt. |
| `agent.landDebtsOwed` | any `Agent` | List of debts this agent owes as a debtor (works for non-`Locke` agents too). |
| `agent.locke["claims"]` | `Locke` agent | List of cells this agent currently holds any ownership share in. |
| `agent.locke["debtsReceivable"]` | `Locke` agent | List of debts owed *to* this agent as creditor. |

Because `owners`, `consentedAgents`, `pendingViolations`, etc. live on the
`Cell` and generic `Agent` objects rather than exclusively inside `Locke`,
land claims are visible to and enforceable against every decision model in
the simulation, not only other `locke` agents.

## Land claiming

An agent claims a cell by harvesting it, but only if the claim wouldn't be
the last unclaimed land around — i.e. Locke's "enough, and as good left in
common for others" proviso, read here as *spatial* sufficiency rather than
global sufficiency:

```
collectResourcesAtCell()                      ethics.py:637
  owners = cellOwners(cell)
  if len(owners) == 0:
      unclaimedNearbyCellExists = any cell in findCellsInRange() is also unclaimed
      if unclaimedNearbyCellExists:
          acquireLandClaim(cell)               ethics.py:631
```

`acquireLandClaim` sets `cell.owners = {self: 1.0}` (100% share to the
claimant) and stamps `lastHarvestedTimestep` (`claimCellFor`, `ethics.py:582`).

## Land abandonment

Each timestep, every `Locke` agent checks its own claims
(`processLandAbandonment`, `ethics.py:656`) and forfeits any cell that hasn't
been harvested in `environmentLandDecayTimesteps` steps:

```python
if self.timestep - claimedCell.lastHarvestedTimestep >= decayThreshold:
    forfeitCellClaim(claimedCell)   # cell.owners = {}, reverts to unclaimed
```

**Note:** `lastHarvestedTimestep` is updated by *any* harvest of the cell —
owner, consented licensee, or trespasser (see
[Implementation details](#implementation-details-not-covered-by-the-design)) —
not specifically the owner's own harvest. A cell being actively stolen from
every timestep will never decay, even if the owner never returns to it.

Config: `environmentLandDecayTimesteps` (default `50` in code, `3` in
`config.json`'s example scenario).

## Trespass, violations, and debt

Trespass detection lives in the base `Agent` class
(`agent.py:262-278`, called from `collectResourcesAtCell` at
`agent.py:249-260`), so it fires for **any** agent that harvests a claimed
cell without consent — `locke`, `bentham`, `egoist`, etc. — not only other
`locke` agents:

```
recordLandTrespassIfOwned(sugarCollected, spiceCollected)   agent.py:262
  owners = cell.owners  (if any, and self is not one of them, and some owner is alive)
      cell.lastHarvestedTimestep = self.timestep
      if self not in cell.consentedAgents:
          cell.pendingViolations.append({trespasser: self, cell, amount, timestep})
```

The theft is *not* immediately turned into a debt — it sits as a pending
violation until the owner actually returns to the cell:

```
collectResourcesAtCell()  (Locke override)     ethics.py:637
  elif self in owners:
      processReturnToOwnedLand(cell)            ethics.py:650
        -> convertViolationsToDebts(cell, timestep)   ethics.py:594
```

`convertViolationsToDebts` splits each pending violation's `amount` across
all co-owners proportional to their `share`, creating one debt record per
(owner, trespasser) pair, then clears `cell.pendingViolations`.

### Settling debt

Two independent, complementary paths exist, matching the "agents pay ...
despite physical constraint, although forceful collection does[require
proximity]" rule:

**Voluntary** (`settleDebtsVoluntarily`, `ethics.py:672`) — runs every
timestep for every debtor, with no proximity requirement. A debtor pays down
its debts out of whatever sugar/spice it has *above* its own metabolic need,
sugar first, then spice, for the same nominal value regardless of which
resource is used.

**Forceful** (`doForcefulDebtCollection`, `ethics.py:754`, called from
`doTrading` at `ethics.py:784`) — requires the collecting agent to be
adjacent to the debtor (`self.cell.findNeighborAgents()`), and only fires
once the debt has aged past a grace period:

```python
graceTimesteps = configuration["environmentLandForcefulCollectionGraceTimesteps"]
if self.timestep - debt["createdTimestep"] < graceTimesteps:
    continue
```

Config: `environmentLandForcefulCollectionGraceTimesteps` (default `1`).
Forceful collection seizes whatever sugar/spice the debtor currently has —
unlike voluntary settlement, it is *not* limited to the amount above the
debtor's metabolic need.

**What "adjacent"/"physically constrained" actually means spatially** is not
a Locke-specific concept — every mechanic below that requires proximity
(forceful collection above, plus consent grants and buyouts further down)
is built on `Cell.neighbors`, which is generic environment topology:
radius-1 only, either 4-connected (`neighborhoodMode: "vonNeumann"`, the
default — north/south/east/west) or 8-connected (`"moore"`, adds the four
diagonals), and wraps around the grid edges by default
(`environmentWraparound: true`), so two agents on opposite edges of the map
can be "adjacent" for the purposes of every Locke mechanic below.

## Consent-based licensing

An owner (or majority of co-owners, by share) can grant standing permission
to harvest a claimed cell in exchange for a fee, evaluated every timestep in
`doLandConsentGrants` (`ethics.py:695`), owner-initiated and
physically-constrained to agents adjacent to **the claimed cell itself**
(`claimedCell.findNeighborAgents()`) — not to the owner's current position,
since an owner processes every cell it holds a share in each timestep,
regardless of where it's currently standing:

```python
fee = claimedCell.sugar + claimedCell.spice        # current yield, not potential
for candidate in claimedCell.findNeighborAgents():
    candidateApprovals.add(self)                    # this owner votes yes
    approvingShare = sum(shares of all owners who have voted yes)
    if approvingShare <= 0.5:
        continue                                      # needs a majority of shares
    if candidate can afford fee (with a 50-metabolism-timestep reserve buffer):
        candidate pays fee, split pro rata across owners by share
        candidate added to cell.consentedAgents
```

Consent, once granted, is permanent (the candidate stays in
`consentedAgents` and is never removed short of the cell being forfeited or
re-claimed).

## Out-of-range buyouts

If a claimed cell falls outside its owner's own foraging range
(`cellsInRange`), a *different* `locke` agent may buy that share outright and
permanently — but only if the buyer is currently standing adjacent to that
cell (`self.cell.neighbors.values()`, i.e. relative to **the buyer's own
position**, the opposite reference frame from consent grants above),
evaluated in `doLandBuyoutOffers` (`ethics.py:729`):

```python
if neighborCell == targetOwner.cell or neighborCell in targetOwner.cellsInRange:
    continue                                          # still in owner's range: not buyable
price = (neighborCell.maxSugar + neighborCell.maxSpice) * share   # potential yield, not current
if buyer can afford price (with a 50-metabolism-timestep reserve buffer):
    pay targetOwner, transferShare(cell, targetOwner, self)
```

`transferShare` (`ethics.py:619`) moves the target owner's share to the
buyer, converting any pending violations to debts first so nothing is lost
in the handoff.

## Inheritance

On death, `doInheritance` (`ethics.py:811`) splits each claimed cell
fractionally, in equal shares, across every currently-living `locke` child;
if none exist, the cell reverts toward the commons:

```python
livingLockeChildren = [c for c in socialNetwork["children"] if c.isAlive() and isinstance(c, Locke)]
for claimedCell in self.locke["claims"]:
    convertViolationsToDebts(claimedCell, timestep)     # settle the ledger before transferring
    if livingLockeChildren:
        perChildShare = myShare / len(livingLockeChildren)
        # each living Locke child's ownership share increases by perChildShare
    else:
        del owners[self]                                 # this owner's share is simply removed
    if len(owners) == 0:
        forfeitCellClaim(claimedCell)                    # only reverts to commons if NO owners remain
```

Note that "reverts to the commons" is a consequence of the owners dict
becoming empty, not a direct rule — on a co-owned cell, a childless owner's
share is just removed while surviving co-owners (or their heirs) keep theirs.

Outstanding debts and receivables belonging to the deceased are discharged
(not transferred) at death — `removeSettledDebt` is called on all of them at
the end of `doInheritance`.

### Land inheritance vs. wealth inheritance

`Locke.doInheritance` opens with `super().doInheritance()` (`ethics.py:812`),
which runs the **generic, decision-model-agnostic** inheritance mechanic
already present in `agent.Agent.doInheritance` (`agent.py:391`) before any
Locke-specific land splitting happens. That base mechanic splits the
deceased's *sugar and spice* evenly across recipients chosen by the
`agentInheritancePolicy` config value (`"none"`, `"children"`, `"sons"`,
`"daughters"`, or `"friends"`) — entirely independent of the land logic
below it.

This produces an asymmetry worth knowing about: wealth inheritance under
`agentInheritancePolicy: "children"` splits across **every** living child,
Locke or not, while land inheritance splits only across living children that
are themselves `isinstance(c, Locke)`. A Locke parent with one Locke child
and one Bentham child will have both children inherit sugar/spice, but only
the Locke child inherits any land share.



## Configuration reference

| Key | Default (code / `config.json`) | Meaning |
|---|---|---|
| `agentDecisionModels` | `["none"]` / `["locke"]` | Include `"locke"` to enable this decision model. |
| `environmentLandDecayTimesteps` | `50` / `3` | Timesteps a claimed cell can go unharvested (by anyone) before the claim is forfeited. |
| `environmentLandForcefulCollectionGraceTimesteps` | `1` / `1` | Timesteps a land debt must age before it can be forcefully collected. |
| `agentInheritancePolicy` | `"none"` / `"children"` in `config.json` (also `"children"` in `examples/locke_basic.json`) | Generic, non-Locke-specific wealth (sugar/spice) inheritance policy — see [Land inheritance vs. wealth inheritance](#land-inheritance-vs-wealth-inheritance). **Active by default in this repo's `config.json`**, so the child-filter asymmetry described there is live, not hypothetical. |

## Cross-decision-model interactions

- **Any** agent, regardless of its own decision model, can trigger a
  trespass violation by harvesting a `locke` agent's claimed cell without
  consent (`agent.py:262`).
- **Any** agent that owes a land debt can have it forcefully collected by an
  adjacent `locke` creditor or co-owner (`doForcefulDebtCollection` no longer
  restricts collection targets to other `locke` agents).
- Only `locke` agents can *own* land, *grant* consent, *offer* buyouts, or
  *inherit* claims — those actions live entirely inside the `Locke` class and
  require `isinstance(x, Locke)` (e.g. `doInheritance`'s
  `livingLockeChildren` filter).

## Observability

There is currently no aggregate instrumentation for any part of this system.
`updateRuntimeStatsPerGroup` (`sugarscape.py:1007`) — the function that
builds every per-timestep stat written to `log.json` and every series
available to `dataCollectionOptions.plots` (`deaths`, `giniCoefficient`,
`happiness`, `lifeExpectancy`, `population`, `sickness`, `tradeVolume`,
`ttl`, `wealth`) — has no land/claim/violation/debt counters at all. The
only ways to observe this system while it runs are:

- Per-event debug print statements, gated behind `debugMode` containing
  `"all"` or `"agent"`, on essentially every state-changing method above
  (claims, trespasses, debt conversion, voluntary/forceful settlement,
  consent grants, buyouts, bequests, abandonment).
- The GUI's binary "Land Claims" color mode (see item 7 below).

There is no way to plot, e.g., total land under claim, outstanding debt, or
violation rate over time without parsing debug output by hand.

## Implementation details not covered by the design

These are real, verified behaviors in the current code that the design
paragraphs don't specify one way or the other. They're not necessarily bugs
— several are reasonable implementation choices — but they're worth knowing
about:

1. **Abandonment resets on any harvest, not the owner's harvest specifically.**
   `lastHarvestedTimestep` is stamped by trespassers and consented licensees
   too, so a claim under continuous theft never decays even if the true
   owner never returns.
2. **Consent grants require majority-by-share approval**, not a single
   owner's decision — a voting mechanic that only matters because land can
   be fractionally co-owned (via inheritance or partial buyouts).
3. **Two distinct, unstated pricing formulas**: consent fee uses the cell's
   *current* `sugar + spice`; buyout price uses the cell's *potential*
   `maxSugar + maxSpice`.
4. **A hardcoded 50-metabolism-timestep reserve buffer** gates both consent
   payments and buyouts — an agent won't spend itself below that buffer to
   pay for either.
5. **`findEthicalValueOfCell` (`ethics.py:804`) multiplies cell value by
   `1.0`** when the cell is owned by someone else without consent — a no-op
   stub. It reads as an unfinished attempt to make unconsented land look
   less attractive to the agent's own movement/foraging choice, but
   currently does nothing. Practical consequence: `findBestEthicalCell`
   (`ethics.py:790`), which is what actually picks where a `Locke` agent
   moves each timestep, scores an unconsented, owned cell exactly the same
   as free land. Locke agents show no movement-level aversion to someone
   else's claimed cell — they walk onto and harvest it the same as they
   would unclaimed land, and only feel a consequence afterward, through the
   violation/debt pipeline.
6. **Voluntary debt settlement runs unconditionally every timestep** for
   every debtor with any land debt, independent of and prior to any forceful
   collection attempt.
7. **The GUI's "Land Claims" coloring is binary, not proportional**
   (`gui.py:661-665`): it blends a fixed "claimed" tint onto any cell with
   `len(cell.owners) > 0`, regardless of how many owners there are or what
   share each holds. Fractional co-ownership from inheritance/buyouts isn't
   visually distinguishable from single ownership.

## Not yet implemented: trust and social contract (Phase 2)

The following is specified in the design but has **no corresponding code**
anywhere in `ethics.py`, `agent.py`, `sugarscape.py`, or `config.json` as of
this writing:

- Trust-point accrual: an agent gains a trust point with a neighbor's cell
  owner for being adjacent to that cell without stealing from it.
- A per-agent-pair randomized threshold (drawn from a `config.json` array
  such as `[4, 8]`) at which trust converts into a social contract.
- Social contract formation requiring *both* agents to have independently
  reached their threshold with each other.
- A "government" body: a shared debt/violation list across all contracted
  members, with any member able to collect violations or debts on behalf of
  any other member.
- Frictionless joining: a new agent can join an existing government by
  itself consenting, without the existing body needing to re-form or
  re-vote.
- Trust tracked for *all* agents, regardless of their own decision model —
  not just other `locke` agents.
- Exclusion from the social contract grounded strictly in incapacity to
  consent (e.g. agents that can't reason/consent at all), never in
  arbitrary discrimination.
- Trust resetting to zero for an agent upon any violation.

None of this exists yet. Everything documented above this section is Phase 1
(property) only.
