# PATHRIX — Team Workflow

**Team size: 2. Timeline: see `PLAN.md` §1.1 (26 days as of 18 Aug 2026).**

**Status:** 🚧 provisional — same standing as `ARCHITECTURE.md`. This is a process
we're starting with, not one either of us is locked into. Change it the moment
it's wrong.

---

## 0. The split, stated plainly

> **This is my read of "the rest," not something you confirmed.** Fix it in one
> line if it's wrong — that's cheaper than either of us working off a guess.

| | Owns |
|---|---|
| **You (Hitchgernn)** | AI/agent (`agent/`), backend implementation (`api/`, `routing/` code, `data/` code), UI/UX design (Claude Design canvas — mockups and design system, not frontend code), DevOps/deployment |
| **Your teammate** | Frontend implementation (`frontend/`, from your Claude Design handoff via MCP + `ARCHITECTURE.md`/`PLAN.md` as the structural reference), field survey + GIS digitization, dataset QC and metadata, routing *accuracy* validation (tuning against real Yogyakarta routes), project coordination with MAPID, QA/usability testing, competition deliverables and presentation |

This maps onto the proposal's original five roles (`proposal_pathrix.md` §12):
you absorb *AI/Agent Engineer*, *UI/UX Designer*, the implementation half of
*Backend & Spatial Analyst*, and DevOps; your teammate absorbs *WebGIS Developer
(Frontend)*, *Project Leader*, the domain half of *Backend & Spatial Analyst*,
and the survey work.

**Why DevOps moved to you.** Original split had it with your teammate. It moved
because you're setting up the Compose topology and CI alongside the backend you're
already building — splitting deploy config ownership from the code it deploys adds
a handoff for no benefit at this team size.

**Why the frontend moved.** Originally frontend sat with you because AI + backend
+ frontend is one person's flow when the codebase is small enough to hold in one
head. It moved because your teammate is IT-background and can implement directly
from a design handoff — freeing you to spend the AI + backend + design time on
the harder problem (the agent and routing engine), which is where the scored
metrics actually live (`PRD_AI_TOD_Navigator_Yogyakarta.md` §10). Design and its
implementation are now two different people, which means the handoff itself is a
dependency — see §4.

---

## 1. Where the shared truth lives

Do not re-derive scope in conversation. Point at the document.

| Question | Answer lives in |
|---|---|
| What are we building, for whom, by when | `PRD_AI_TOD_Navigator_Yogyakarta.md` |
| What did we promise the judges | `proposal_pathrix.md` — **binding**, deviations need a reason |
| What order do we build it in | `PLAN.md` §11 |
| How do the pieces fit, what's the contract between them | `ARCHITECTURE.md` |
| How do we work together | this file |

If a conversation resolves something not written down, **write it down before the
conversation ends.** A decision that lives only in a chat thread doesn't exist
for the other person tomorrow.

---

## 2. The one hard synchronization point

`PLAN.md` §11.1 already names it: **the API contract freezes by ~27 August.**

Before that date: talk daily, contracts are expected to move, don't build
downstream of anything not yet frozen.

After that date: `models/` (the Pydantic schemas) is the interface. Either
person can build against it without checking with the other first. **Changing a
frozen schema after this date is a conversation, not a solo edit** — the other
person has code depending on the old shape.

If the contract turns out wrong after freeze, say so immediately rather than
working around it silently — a workaround compounds; a schema fix on day 1 of
being wrong is cheap.

---

## 3. Daily rhythm

Two people, 26 days, no PM tooling overhead earns its cost. Keep this to the
minimum that prevents surprises:

- **Once a day, async is fine:** what you finished, what you're touching next,
  anything blocking you. A message is enough — this doesn't need a meeting.
- **Before touching something in the other person's lane**, say so first. Not
  for permission — so two people don't independently fix the same thing.
- **When you hit one of the open questions in `ARCHITECTURE.md` §15**, resolve
  it together and update the document in the same sitting. Don't let it sit as
  a verbal agreement.

No sprints, no story points, no board with columns neither of us will maintain
for 26 days. `PLAN.md` §11's table *is* the plan.

---

## 4. Handoffs

The two places work crosses the split, made explicit so neither side guesses:

| Handoff | From → To | What crosses |
|---|---|---|
| Survey + digitized routes | Teammate → You | CSV/GeoJSON into the ETL pipeline (`ARCHITECTURE.md` §6.3) — agree on the file shape *before* the survey finishes, not after |
| Routing accuracy | You → Teammate | A route you can already compute, for teammate to check against ground truth and hand back `W_TRANSFER`/`W_WALK` tuning (`ARCHITECTURE.md` §7.2) |
| Hosting requirements | Teammate → You | Once hosting is decided (`PLAN.md` §12.2), teammate relays MAPID's finalist-subdomain requirements from their coordination role; you own the Compose topology and deploy end to end, so this is the only cross-lane step — the Compose file (`ARCHITECTURE.md` §4.1) is written host-agnostic so it's a config change, not a rebuild |
| Design → frontend build | You → Teammate | Claude Design canvas (mockups + tokens) via the MCP you gave him, **plus** `ARCHITECTURE.md` §9–§10 for what the canvas can't show — state shape, the `ui_command` contract, why the map owns viewport truth and the store just mirrors it (§10.1). The MCP is visual truth; the docs are structural truth. Name canvas layers like component names (`AgentSheet`, `RouteCard`) since that's what carries through the handoff. |
| Implemented screens | Teammate → You (for review) | A look before merge, since presentation-readiness is a stated deliverable and both names are on the submission |

---

## 5. Decision authority

To avoid re-litigating: whoever owns the lane (§0) decides inside it. Cross-lane
or judge-facing decisions — anything that changes what's in `proposal_pathrix.md`
or the final PRD — get a two-line async confirmation before either person acts on
it, because both names are on the submission.

Genuinely stuck between two options with no clear owner: default to whichever
costs less to reverse (see `ARCHITECTURE.md` §2.5's degrade-don't-fail spirit —
same instinct applies to process, not just code).

---

## 6. What "done" means before submission

Pulled from `PLAN.md` §11.2 so it isn't re-typed twice:

1. Public WebGIS link — finalist subdomain, MAPID MAPS basemap, mobile-first
2. Final PRD (updated)
3. Metadata for all datasets + processing methodology
4. Survey activity documentation + budget usage
5. AI Agent explanation — input/process/output/validation per capability
6. Final presentation deck — 6 minutes + 4 minutes Q&A

Items 3, 4, and 6 are teammate-led; item 5 is yours to write since you own the
agent; item 1 is a joint output. Draft the split for who writes what by the time
the API contract freezes — writing deliverables in the last 4 days (`PLAN.md`
§11's final window) is the schedule's tightest spot.

---

## 7. If the schedule slips

`PLAN.md` §11.1 already sets the cut order: sustainability extras → Urban
Planning layer → multi-stop itineraries. That order is not renegotiated under
pressure — decide the priorities calmly now, not during the crunch when adrenaline
argues for keeping everything.

If a cut is needed, whichever person owns the piece being cut says so out loud
before quietly dropping it, so the other person's plans and the deliverables
list (§6) update too.
