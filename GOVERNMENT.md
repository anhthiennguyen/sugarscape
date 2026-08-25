# Government (Locke Phase 2, commit `9a70cff`)

A complete, source-order reference to every file, class, and method — or,
for single-line changes, the line itself — touched by exactly one commit:
`9a70cff98cc9ff70b5697e08cf5f5637cc7f235e`, "Adds Locke Phase 2: trust
points, social contract formation, and government." This is the trust →
social-contract → government layer on top of the Phase 1 property system
already documented in `PROPERTY.md`.

**Scope note**: this file describes only what that one commit changed, not
the current state of the repository. `gui.py` and `config.json` have both
been modified again since (per `git log`), so line numbers here are taken
from the commit itself (`git show 9a70cff:<file>`), not from `HEAD` — for
those two files, the line numbers below will not match what's on disk today.
`ethics.py`, `agent.py`, `sugarscape.py`, and `README` have not changed
since this commit, so their line numbers below do match current `HEAD`.
`PROPERTY.md` is the up-to-date reference for the codebase's current state;
this file is a historical record of one specific commit.

## `ethics.py` — `class Locke(agent.Agent)` (only the touched/new methods)

- **`__init__(self, agentID, birthday, cell, configuration)`** — Modified.
  Previously `self.locke = {"claims": [], "debtsReceivable": []}`. This
  commit reads `environmentLandTrustThresholdRange` off
  `cell.environment.sugarscape.configuration` (not the `configuration`
  parameter — traced end-to-end through `randomizeAgentEndowments` and
  `findChildEndowment`; neither ever copies `environment*`-prefixed keys
  into the per-agent endowment dict passed to `__init__`, so the threshold
  literally cannot be read any other way, nor inherited from a parent
  without deeper surgery) and adds three new keys: `"trust": {}`
  (`{otherAgentID: intScore}`, keyed by ID — matching the existing
  `Agent.socialNetwork[agentID]` convention already used elsewhere in
  `agent.py`), `"trustThreshold": random.randint(thresholdRange[0],
  thresholdRange[1])`, and `"government": None`.
  *Two sections together: Locke, Sect. 116: "a child is born a subject of no country or government" — political disposition is never inherited, each person must individually reach their own consent. Sect. 118 confirms this isn't just a claim about infancy but persists past majority: "governments themselves understand it otherwise; they claim no power over the son, because of that they had over the father; nor look on children as being their subjects, by their fathers being so" — an adult child's political standing owes nothing to the parent's. Together these ground why `trustThreshold` is independently rolled per agent rather than inherited from a parent. `random.randint` (not the seeded-hash-per-config convention `randomizeAgentEndowments` uses elsewhere) matches the existing `depressionFactor` reroll-at-birth precedent (`agent.py:909-915`) — the established pattern in this codebase for a trait that's independently rolled rather than inherited.*
- **`doForcefulDebtCollection(self)`** (`757-791`) — Modified (pre-existing
  Phase 1 method). One new block inserted immediately after the existing
  creditor-liveness check, before any seizure math: if `self.locke["government"]`
  is not `None` and the debt's creditor is not a member of it, the
  collection attempt is skipped (with a debug print) and the loop
  continues to the next debt. A non-member (`self.locke["government"] is
  None`, the common case for any agent that hasn't joined a government)
  skips this block entirely — unrestricted collection, unchanged from
  before this commit. The gate checks only the collector's and creditor's
  membership; the debtor's own membership is irrelevant.
  *Two sections together: Locke, Sect. 87 grounds the gate's very existence — political society is defined as the state where "every one of the members hath quitted this natural power, resigned it up into the hands of the community in all cases that exclude him not from appealing for protection to the law established by it," meaning membership itself is what transforms private, universal enforcement into something bounded by the community. Sect. 130 grounds specifically what a member is left able to do with that resigned power: "The power of punishing he wholly gives up... to assist the executive power of the **society**" — restricted to fellow members, not exercised freely for outsiders as before joining (that free-agent right, exercised on behalf of any creditor, is already correctly Locke-accurate pre-government per Sect. 10, see `PROPERTY.md`). Still a looser analogy than most of this codebase's citations — noted plainly rather than overstated.*
- **`doTrustAccrual(self)`** (`793-806`) — New. Runs every timestep for
  every cell the agent owns; every living neighbor of that cell who is not
  a co-owner and didn't trespass on it *this specific timestep* (checked
  via `cellPendingViolations`, filtered to `v["timestep"] == self.timestep`)
  earns one trust point from the owner, via `increaseTrust`. This is the
  literal complement of the trespass check `agent.recordLandTrespassIfOwned`
  already performs, reusing the same `cellPendingViolations`/
  `findNeighborAgents` primitives rather than re-scanning adjacency
  separately.
  *Design choice — no textual analog for a quantified trust-building period; Locke never describes trust or reputation being built up numerically before political society forms.*
- **`increaseTrust(self, candidate, cell)`** (`807-815`) — New. Increments
  `self.locke["trust"][candidate.ID]` by 1, logs it, and — only if
  `candidate` is itself a `Locke` instance — calls
  `attemptGovernmentFormation`. The `isinstance(candidate, Locke)` check is
  the *only* gate here, and it's what satisfies "exclusion follows from
  incapacity to consent, not discrimination": a non-`Locke` agent simply
  has no `.locke` dict to reciprocate through, so it's structurally never
  reachable past this point — no characteristic-based check (race, sex,
  tribe, tag) appears anywhere in this path.
  *Design choice for the trust-point mechanic itself; the exclusion principle is Locke, Sect. 60's logic (exclusion from full agency grounded in incapacity — "lunatics and ideots are never set free... but continued under the tuition... of others, all the time their own understanding is uncapable") applied here to consent rather than reason.*
- **`attemptGovernmentFormation(self, other)`** (`816-822`) — New. Returns
  early unless *both* directions of trust — `self`'s trust in `other`, and
  `other`'s trust in `self` — have each independently reached that
  tracking agent's own `trustThreshold`. Only then calls
  `formOrJoinGovernmentWith`.
  *Design choice — the bilateral-threshold mechanic has no textual analog; Locke describes political society forming by mutual consent (Sect. 95-99, see below) but never a quantified precondition for it.*
- **`formOrJoinGovernmentWith(self, other)`** (`823-842`) — New. Three
  cases: (1) both agents already belong to governments — does nothing,
  logging explicitly when those are two *different* governments (no
  merge); (2) exactly one already belongs to a government — the other
  joins it via `addToGovernment`; (3) neither does — founds a new
  government: a plain `set()` containing both agents, assigned by shared
  object reference to both agents' `self.locke["government"]`.
  *Locke, Sect. 95-99 grounds forming political society by mutual consent — "when any number of men have so consented to make one community or government, they are thereby presently incorporated" — and is why this is implemented as a bare `set()` rather than a dedicated class: a government here is nothing more than its members' collected consent, not a thing that exists apart from them (this was an explicit design correction mid-implementation — an earlier draft proposed a standalone `Government` class, rejected in favor of keeping everything under `class Locke`). The different-governments-no-merge branch is grounded in Sect. 121: "he that has once... given his consent to be of any common-wealth, is perpetually and indispensably obliged to be, and remain unalterably a subject to it... and can never be again in the liberty of the state of nature" — membership is exclusive and binding, so an already-committed agent can't also found or join a second body. This citation reversed what would have been the "obvious" game-design default (letting governments merge) once the text was actually checked.*
- **`addToGovernment(self, government, newMember)`** (`843-849`) — New.
  Adds `newMember` to the existing shared `set()` and points their own
  `self.locke["government"]` at that same set object. The set already
  referenced by every other current member is mutated in place, so no
  existing member's reference needs updating and the government object
  itself is never recreated.
  *Locke, Sect. 122 grounds the specific mechanic ("the existing body doesn't re-found itself"): an individual joining an established commonwealth becomes a member "by his actually entering into it by positive engagement, and express promise and compact" — the commonwealth itself doesn't need to re-form or re-consent for each new member, only the joiner needs to consent.*
- **`resetTrustIn(self, violator)`** (`850-854`) — New. Zeroes
  `self.locke["trust"][violator.ID]` if it's currently nonzero, with a
  debug print. Called on every living `Locke` agent — via three duck-typed
  lines appended to `agent.recordLandTrespassIfOwned`, see `agent.py`
  below — any time any agent, Locke or not, is recorded as a trespasser.
  A single violation therefore resets *every* tracking agent's trust in
  the violator at once, not just the immediate victim's. Notably, this
  reset never touches `self.locke["government"]` on either side — a
  violator who already belongs to a government keeps full membership and
  every collection privilege that comes with it, even the instant after
  every fellow member's trust in them has dropped to 0. Nothing in the
  spec or in `formOrJoinGovernmentWith`/`addToGovernment` checks trust
  again once membership is established.
  *Locke, Sect. 8: a transgression is "a trespass against the **whole species**, and the peace and safety of it" — grounding the global (not victim-only) scope of the reset; the specific choice to zero the score outright rather than, say, decay it gradually is a design choice Locke doesn't address. The membership-survives-a-trust-collapse behavior above is not a gap glossed over — it is the textually correct outcome per Sect. 121 (already cited under `formOrJoinGovernmentWith`): membership, once formed by consent, is "perpetually and indispensably obliged" and ends only "by any calamity, the government he was under comes to be dissolved," not by an internal trust score fluctuating. Locke's own theory argues against building an expulsion mechanic here, not merely toward omitting one.*
- **`doTrading(self)`** (`856-861`) — Modified. One line added at the end:
  `self.doTrustAccrual()`, after the three pre-existing Phase 1 calls
  (`doLandConsentGrants`, `doLandBuyoutOffers`, `doForcefulDebtCollection`).
  *Design choice — pure call-sequencing wrapper.*

## `agent.py` — `class Agent` (only the touched method)

- **`recordLandTrespassIfOwned(self, sugarCollected, spiceCollected)`** —
  Modified (pre-existing Phase 1 method; this file's only change in this
  commit). Three lines appended at the end, right after the existing
  trespass debug print:
  ```python
  for other in self.cell.environment.sugarscape.agents:
      if other is not self and hasattr(other, "resetTrustIn"):
          other.resetTrustIn(self)
  ```
  This is a bare notification loop over the living-agent population
  (`sugarscape.agents`, already the set dead agents are pruned from each
  timestep), not a new method — it's deliberately *not* a method on
  `Agent`, because all the actual trust-reset logic (what "reset" means,
  the debug message, the trust dict itself) belongs to `Locke.resetTrustIn`,
  which this loop calls. Duck-typed via `hasattr` (matching this method's
  existing style — see `PROPERTY.md`), not `isinstance(other, Locke)`,
  because `agent.py` cannot import `ethics.py` (circular; `ethics.py`
  already imports `agent`), and because this must work regardless of the
  *violator's* own decision model too — only a `Locke` instance actually
  has a `resetTrustIn` method, so `hasattr` already means "every `Locke`
  agent" without ever naming `Locke`. This is the *only* new code outside
  `class Locke` introduced by this entire commit.
  *Locke, Sect. 6: "The state of nature has a law of nature to govern it, which obliges every one... no one ought to harm another in his life, health, liberty, or possessions." The law of nature binds everyone, not just fellow property-owners — the same grounding this pre-existing method already had for living on the base `Agent` class, now extended to the notification loop appended to it.*

## `sugarscape.py` (one line)

- **Hardcoded config defaults dict** (`1916`, between
  `environmentLandForcefulCollectionGraceTimesteps` and
  `environmentMaxCombatLoot`) — Adds
  `"environmentLandTrustThresholdRange": [4, 8]`. Load-bearing exactly
  like the two pre-existing Phase 1 Locke config keys: the config-file-
  override loop (`for opt in configuration: if opt in options: ...`) only
  applies a `config.json` value for a key that *already exists* in this
  dict — a key present only in the JSON file and not here is silently
  ignored (this is the same bug class that broke the Phase 1 grace-period
  fix the first time it was tried).
  *Design choice — Python config-plumbing.*

## `config.json` (one new key, as of this commit)

- **`environmentLandTrustThresholdRange: [4, 8]`** (line `85`, new key) —
  Matches the code default introduced in the same commit. (A later,
  separate commit changed this scenario's value to `[1, 1]`; that change
  is out of scope for this file, which documents `9a70cff` only.)
  *Design choice — Locke never specifies how much trust-building precedes political society forming; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `README` (one new entry)

- **`environmentLandTrustThresholdRange` entry** (new, after the
  pre-existing `environmentLandForcefulCollectionGraceTimesteps` entry) —
  Documents the config key, that it's independently drawn per agent at
  birth and not inherited from a parent, its Locke-only relevance, and its
  default of `[4, 8]`.
  *Design choice — documentation; see `doTrustAccrual`/`attemptGovernmentFormation` above.*

## `gui.py` — `class GUI` (line numbers as of this commit; see scope note above)

- **`self.colors` dict** (constructor, line `26`) — Adds
  `"noGovernment": "#888888"`, the neutral gray for any agent not
  currently in a government (or with no `.locke` dict at all). At this
  commit, the pre-existing Phase 1 `"claimed": "#C87850"` entry is still
  present and still used — a later, separate commit removed it when land
  claims switched from a flat tint to per-owner coloring; that change is
  out of scope here.
  *Design choice — visualization only.*
- **`self.governmentColors = {}`** (constructor, line `28`) — New. An
  empty cache dict, populated lazily the first time each government is
  rendered (see `findGovernmentColor` below) — unlike tribes/races/
  decision models, the number of governments isn't known ahead of time, so
  their palette assignment can't be precomputed at GUI construction the
  way those are.
  *Design choice — visualization only.*
- **`configureAgentColorNames(self)`** (line `80`) — Modified. Adds
  `"Government"` to the list of selectable agent coloring modes, which
  previously offered `"Decision Models", "Depression", "Disease",
  "Metabolism", "Movement", "Races", "Sex", "Tribes", "Vision"`.
  *Design choice — visualization only.*
- **`findGovernmentColor(self, government)`** (new, inserted between
  `findColorRange` and `findSugarAndSpiceColors` — this file's methods are
  strictly alphabetically ordered) — A government is a plain `set()`,
  which is unhashable, so this keys the color cache on `id(government)`
  instead (stable for the government's lifetime, since membership changes
  mutate the set in place rather than replacing it — see
  `addToGovernment` in `ethics.py` above). Assigns the next unused color
  from `self.palette`, cycling by modulo once every palette slot has been
  claimed by some other government.
  *Design choice — visualization only; also the one place in this codebase (as of this commit) that colors a dynamically-unbounded, run-time-discovered category rather than a fixed, config-known one (tribes/races/decision models all precompute their palette slice from a config-known count at GUI construction).*
- **`lookupFillColor(self, cell)`** (`661-702`, one pre-existing Phase 1
  method with a new branch added) — Adds an `elif` branch at `683-688`
  for `activeColorOptions["agent"] == "Government"`: duck-types via
  `getattr(agent, "locke", None)` (this file doesn't import `ethics.py`
  either, same reasoning as `agent.py` above) to find the agent's
  government, if any, and colors it via `findGovernmentColor`; any agent
  without one — including every non-Locke agent, which has no `.locke` at
  all — gets the neutral `"noGovernment"` gray. (This commit does not
  touch the pre-existing `"Land Claims"` environment-coloring branch
  higher up in the same method; a later, separate commit changed that one
  from a flat claimed/unclaimed tint to per-owner coloring — out of scope
  here.)
  *Design choice — visualization only.*
