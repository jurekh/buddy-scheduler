# Feature Specification: buddy-scheduler

**Feature Branch**: `001-buddy-scheduler`
**Created**: 2026-02-24
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Team Pairings (Priority: P1)

A team coordinator maintains a roster of team members and runs the tool periodically
(weekly or bi-weekly) to generate a new round of buddy pairings. Each active member
is assigned exactly one buddy. If the team has an odd number of active members, one
person sits out. The coordinator receives a structured result suitable for sharing
with the team or feeding into another system.

**Why this priority**: This is the core utility of the tool. All other stories build
on it. Without valid pairings, nothing else delivers value.

**Independent Test**: Provide a static team list with no history. Verify that every
active member appears in exactly one pair, no member is paired with themselves, and
the total pair count equals half the number of active members (rounded down).

**Acceptance Scenarios**:

1. **Given** a team list with an even number of active members, **When** pairings are
   generated, **Then** every active member appears in exactly one pair and the output
   contains N/2 pairs.

2. **Given** a team list with an odd number of active members, **When** pairings are
   generated, **Then** (N−1)/2 pairs are produced and the sit-out member is identified
   in the output.

3. **Given** a team list where no members are active, **When** pairings are requested,
   **Then** the tool exits with a clear error message and produces no pairing output.

---

### User Story 2 - History-Aware Pairing (Priority: P2)

Over multiple rounds, the coordinator wants the tool to avoid repeating buddy pairs.
The tool records who has been paired with whom and, in subsequent runs, prefers
pairings between members who have not been paired recently or at all. The coordinator
can choose whether to persist the new pairings back to the history store after each
run.

**Why this priority**: Without history awareness the same pairs recur, defeating the
purpose of a rotation program. History tracking is the primary quality signal for the
optimiser.

**Independent Test**: Run the tool twice on the same team with history update enabled
between runs. The second run should produce different pairings from the first wherever
team size allows alternatives.

**Acceptance Scenarios**:

1. **Given** a history where members A and B have been paired many times and A and C
   have never been paired, **When** pairings are generated, **Then** A is paired with
   C rather than B (assuming no other constraints prevent it).

2. **Given** a run completes successfully with history update enabled, **When** the
   tool exits, **Then** the history store is updated to include the new pairings and
   all prior entries are preserved.

3. **Given** no history store exists and history update is enabled, **When** the tool
   runs, **Then** a new history store is created automatically and the run proceeds
   normally.

4. **Given** a team with an odd number of active members where member A has sat out
   more times than member B in recorded history, **When** pairings are generated,
   **Then** member B is chosen as the sit-out member rather than member A.

---

### User Story 3 - Timezone-Compatible Pairing (Priority: P2)

Members of the team are spread across multiple timezones. The coordinator wants
pairings to favour members with compatible or overlapping working hours, improving
the chance that buddies can schedule a meeting without extreme scheduling conflict.
The weight given to timezone compatibility relative to history is configurable.

**Why this priority**: Alongside history avoidance, timezone compatibility is the
second quality signal for pairings. Without it, technically valid pairings may be
operationally useless for geographically distributed teams.

**Independent Test**: Provide a team split into two clearly distinct timezone groups
with no history. Verify that pairings fall predominantly within the same timezone
group.

**Acceptance Scenarios**:

1. **Given** a team where half the members are in one timezone region and half in
   another, **When** pairings are generated with timezone weighting enabled, **Then**
   pairings predominantly match members within the same region.

2. **Given** a high timezone-weight and a low history-weight configuration, **When**
   pairings are generated, **Then** timezone compatibility takes priority over history
   avoidance in the output.

3. **Given** a situation where ideal timezone grouping is not achievable without
   violating other constraints, **When** pairings are generated, **Then** the tool
   still produces a valid result and does not abort.

---

### User Story 4 - Avoidance Constraints and Inactive Members (Priority: P3)

Certain members must never be paired together (e.g., a manager with their direct
report, or members with a known working-relationship conflict). Additionally, members
who are temporarily away must be excluded from pairings without being removed from
the roster. Both constraints are enforced absolutely — they are not preferences that
can be traded off against quality scores.

**Why this priority**: These are hard correctness requirements. Violating them makes
output unusable regardless of optimisation quality. They are P3 only because the tool
delivers partial value without them, but they are non-negotiable once present.

**Independent Test**: Configure an avoidance pair and an inactive member. Run the
tool multiple times. Verify the avoidance pair never appears in any output and the
inactive member never appears in any pair.

**Acceptance Scenarios**:

1. **Given** member A lists member B as an avoidance, **When** pairings are generated,
   **Then** A and B are never assigned as a pair, regardless of history or timezone
   scores.

2. **Given** member A is marked inactive, **When** pairings are generated, **Then**
   member A does not appear in any pair and the remaining active members are paired
   normally.

3. **Given** avoidance constraints make it impossible to pair all members validly,
   **When** pairings are requested, **Then** the tool reports the conflict with
   sufficient detail for the coordinator to resolve it, exits without producing
   partial output, and does not attempt any fallback strategy.

4. **Given** a MIP solver failure that is not caused by infeasible constraints,
   **When** pairings are requested, **Then** the tool reports the failure with an
   actionable error message (including the solver status and a suggestion to try a
   different profile) and exits with a non-zero status code.

---

### Edge Cases

- What happens when only one member is active?
- What happens when two members each list the other as an avoidance and no other
  valid partners exist for either?
- What happens when a member named in an avoidance list is not present in the team
  roster?
- What happens when the history store references members no longer in the team? → Stale entries are silently ignored during pairing. With --update-history and --prune-history, stale entries are removed from the store.
- What happens when the team file is missing, empty, or structurally malformed?
- What happens when the history store exists but was partially written (e.g., due to
  an interrupted previous run)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST generate pairings such that each active member appears in
  exactly one pair per run.
- **FR-002**: When the number of active members is odd, the tool MUST produce (N−1)/2
  pairs and identify the one member who sits out. The sit-out member MUST be chosen
  by preferring the member who has sat out least frequently (or least recently) in
  recorded history, consistent with the rotation objective.
- **FR-003**: The tool MUST prefer pairings between members who have been paired less
  frequently in recorded history, penalising repetition in proportion to a
  configurable weight.
- **FR-004**: The tool MUST prefer pairings between members with compatible timezones,
  penalising incompatibility in proportion to a configurable weight.
- **FR-005**: The tool MUST never produce a pair that violates an avoidance constraint,
  regardless of history or timezone scores.
- **FR-006**: The tool MUST exclude inactive members from pairing consideration without
  requiring their removal from the team roster.
- **FR-007**: The tool MUST accept the relative weights of history and timezone
  penalties as parameters at invocation time.
- **FR-008**: The tool MUST accept a solver profile parameter that adjusts the MIP
  solver's optimality gap tolerance and branching aggressiveness. Available profiles
  MUST include at minimum: a fast profile (wider gap tolerance, less aggressive
  branching), an optimal profile (tight gap tolerance, aggressive branching), and an
  adaptive profile that automatically selects settings based on team size. The default
  profile MUST be adaptive.
- **FR-009**: When history update is requested, the tool MUST persist the new pairings
  to the history store after a successful run.
- **FR-017**: History store entries for members absent from the current team roster
  MUST be silently ignored during pairing and never cause an error. When both history
  update and history pruning are requested, the tool MUST remove all stale entries
  (identifiers not present in the current roster) from the history store as part of
  the same write.
- **FR-010**: When no history store exists and history update is requested, the tool
  MUST create a new history store automatically.
- **FR-011**: When avoidance constraints make a valid complete pairing impossible, the
  tool MUST report the conflict explicitly and exit without producing output.
- **FR-012**: When the MIP solver returns a non-optimal status that is not attributable
  to infeasible hard constraints, the tool MUST report the failure immediately with an
  actionable error message that includes the solver status and a suggestion to try a
  different solver profile. No fallback strategies are attempted. Infeasibility caused
  by avoidance constraints MUST be reported with conflict details and no fallback.
- **FR-016**: The primary optimisation strategy MUST use Mixed Integer Programming
  (MIP) to produce solutions that are provably optimal (or within a defined gap
  tolerance) with respect to the combined history and timezone penalty objectives,
  subject to all hard constraints.
- **FR-013**: The tool MUST emit all structured results as JSON to standard output.
- **FR-014**: The tool MUST emit all diagnostic output and error messages to standard
  error, keeping standard output clean for programmatic consumption.
- **FR-018**: The tool MUST emit operational log messages to standard error at a
  configurable level (DEBUG, INFO, WARNING, ERROR). The default level MUST be INFO.
  Log output MUST cover all significant operations: input loading, validation,
  optimisation start and completion, history reads and writes,
  and errors. Duration and peak memory usage MUST be logged at INFO level at the end
  of each run.
- **FR-015**: The tool MUST validate all inputs before beginning optimisation and
  report validation failures with actionable descriptions. Team roster files MUST be
  validated as well-formed YAML containing a non-empty list of members. History store
  files, when present, MUST be validated as well-formed JSON with a consistent
  internal structure before use.

### Key Entities

- **TeamMember**: A person on the team. Defined in the YAML team roster file. Has a
  unique identifier, a timezone designation, an active flag (defaults to active), and
  an optional list of member identifiers who must never be paired with this person.
- **PairingHistory**: A symmetric matrix of match counts, persisted as a JSON file
  managed exclusively by the tool. Each cell [A][B] holds the number of times member
  A and member B have been paired; [A][B] always equals [B][A]. Diagonal cells [A][A]
  are unused. Also records a per-member sit-out count used to drive fair sit-out
  rotation.
- **PairingResult**: The output of a single run. Contains: the list of pairs; the
  sit-out member (if any); a success flag; an optimisation score; solve duration;
  a solver_profile string identifying the MIP profile used (e.g., "optimal",
  "balanced", "fast"); a solver_gap value present only for MIP solutions indicating
  the achieved gap from theoretical optimum; peak memory usage; inactive member names;
  and an avoidance_conflicts list present only when the run failed due to infeasible
  hard constraints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every run with two or more active members produces output where each
  active member appears in exactly one pair or is identified as the sit-out member.
- **SC-002**: Avoidance constraints are honoured in 100% of runs — a constrained pair
  never appears in output under any configuration.
- **SC-003**: Across a sequence of runs on the same team, no pair repeats until each
  member has exhausted all other eligible partners (where team size permits).
- **SC-004**: The tool completes a run for a team of up to 100 active members within
  5 seconds under the default performance profile.
- **SC-005**: Every defined error condition (empty team, malformed input, impossible
  constraints, corrupted history) produces a clear, human-readable message and a
  non-zero exit status.
- **SC-006**: JSON output is well-formed and machine-parseable in every execution
  path, including failure cases.

## Clarifications

### Session 2026-02-24

- Q: What is the precise performance target for teams of up to 100 active members? → A: Under 5 seconds on the default performance profile.
- Q: When the team has an odd number of active members, how is the sit-out member chosen? → A: History-driven — prefer the member who has sat out least recently (or fewest times).
- Q: Does pairing history accumulate indefinitely or decay/expire over time? → A: Accumulates indefinitely — all historical pairings count equally regardless of age.
- Q: What format must the tool use for structured output? → A: JSON — all structured output (pairs, quality score, metadata, and error payloads) is emitted as JSON to standard output.
- Q: What algorithm must the primary optimisation strategy use? → A: Mixed Integer Programming (MIP) is required as the primary optimisation method.
- Q: How is pairing history structured internally? → A: A symmetric matrix of match counts — each cell [A][B] = [B][A] holds the number of times member A and member B have been paired.
- Q: What does the performance profile control, and what is the default? → A: Profiles adjust MIP solver settings (optimality gap tolerance and branching aggressiveness); they do not switch algorithms. The default profile is adaptive — it automatically selects solver settings based on team size. There are no fallback strategies; solver failure is reported as an error.
- Q: How does the JSON output signal which solver profile was used? → A: The solver_profile field carries the resolved profile name (e.g., "optimal", "balanced", "fast"). The solver_gap field is present only for successful MIP solutions indicating the achieved gap from theoretical optimum.
- Q: What file formats are used for the team roster and history store? → A: Team roster in YAML (human-authored); history store in JSON (machine-managed).
- Q: What happens when the history store references members no longer in the current team roster? → A: Stale entries are silently ignored during pairing (never cause an error). When --update-history is used, an additional --prune-history flag MAY be provided to remove entries for absent members from the store.
- Q: What level of operational logging must the tool provide? → A: Configurable log level (DEBUG / INFO / WARNING / ERROR) via a parameter; default INFO; all log output goes to stderr.

## Assumptions

- Member identifiers are unique within a team roster; duplicate identifiers are a
  configuration error.
- Timezone designations are free-form strings provided by the operator; compatibility
  is assessed by string similarity, not strict UTC-offset arithmetic.
- The history store is managed exclusively by this tool; external modifications are
  not supported.
- Pairing history accumulates indefinitely; all historical entries count equally
  regardless of age. No pruning, decay, or retention window is applied.
- The tool is invoked by a human operator or a scheduled automation job; no
  long-running daemon or server mode is required.
- Supported team size is 2–100 active members; behaviour outside this range is not
  guaranteed.
- Avoidance constraints are treated as symmetric: if A lists B, the pair is forbidden
  regardless of whether B also lists A.
