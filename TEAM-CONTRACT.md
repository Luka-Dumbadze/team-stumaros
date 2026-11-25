# Team Contract · StumarOS

*Due with team lock, end of Week 3. Signed by everyone. Short beats ceremonial.*

> **Status: signed by Luka Dumbadze (2026-11-24); awaiting @UrjuHub and @ZONDROK.** Drafted on 2026-11-24 from the repo's commit history (see "Who built what"). It becomes the contract when every member has signed below. Until then, any member may change any line in their signing pull request.

## Members and roles
| Name | GitHub | Primary role | Backup role |
|---|---|---|---|
| Luka Dumbadze | [@Luka-Dumbadze](https://github.com/Luka-Dumbadze) | Repo keeper (owns the repo, CI, branch rules, tags) | Eval keeper (`evals/`, golden set, results) |
| Urju | [@UrjuHub](https://github.com/UrjuHub) | Spec keeper (`docs/spec.md`, `AGENTS.md` stay true) | Data & content keeper (`data/` guide and stays, privacy) |
| Mariami Tskhomelidze | [@ZONDROK](https://github.com/ZONDROK) | [to agree at the first sync] | [to agree] |

Roles stay fixed until the end of Week 7 (HW2), then we review them together. On Demo Day, anyone answers anything, so backup roles are how you learn each other's parts.

**Who built what (Weeks 1–4, from `git log`):**
- **Luka:** `AGENTS.md` and spec v0 (`531dd90`), the HW1 triage slice now in `src/` and `tests/` (`3eba1f6`), the Design Review (`e1a74bf`), the `lab1-spec` and `design-review` tags, and the Weeks 1–4 catch-up branch.
- **Urju:** the repo's first commit (`f56dfb6`), the team-docs commit "initial" (`3688283`), and the individual HW1 write-up in `hw1/UrjuHub/` (spec, golden questions, delegation log, journal). No commits to `src/` or `tests/` yet.
- **Mariami:** a collaborator with write access (checked 2026-11-24), added to the team on 2026-11-24. No commits in the repo yet.

The roles above move product work toward Urju (spec and data) so every member owns part of `main` from Week 5. With three members, we rebalance the four roles at the first sync after everyone has signed.

## How we decide
- **Small things:** whoever is doing the work decides.
- **Big things** (scope, stack, pivots): consensus of all members, written down as a decision record in `docs/decisions/`.
- **Tie-breaker** if we disagree for more than 48 hours: the Spec keeper decides scope questions, and the Repo keeper decides stack and infrastructure questions.

**Pull requests:** every change goes through a pull request (`docs/TEAM-REPO.md` §4). Another member reviews it, reading the tests first. The person who drove the agent never merges their own PR. Nobody pushes to `main`.

## When we work
Weekly sync: [day, time, where: to agree at the first sync after signing]. Core hours we can all be reached: [range: to agree].

## Contribution
Work is visible in commits and the journal. If someone carries or someone coasts, we say it in week terms, not in Week 15.

## When it breaks
Step 1: name it inside the team within 48 hours. Step 2: if unresolved in one week, we bring it to the instructor together. No-show rule: after 2 missed syncs without notice, Step 1 starts immediately, and the missed work is reassigned at that sync.

Signed (a commit from each member on this file counts as a signature). Each member ticks their own line and fills in the date, in their own commit:

- [x] Luka Dumbadze (@Luka-Dumbadze): date 2026-11-24 (entered by Claude Code on Luka's instruction, in a commit from Luka's account)
- [x] Urju (@UrjuHub): date 2026-11-24
- [ ] Mariami Tskhomelidze (@ZONDROK): date ______
