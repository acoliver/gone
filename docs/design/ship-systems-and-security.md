# Ship Systems and Security

> **Status:** Design companion covering ship power, environmental control, security credentials, SAINT-5, hazards, survival and difficulty. The Spanish [design bible](biblia.md) wins on story facts and reveal protections. Design proposals below are labeled as proposals; unresolved items belong in [the decisions ledger](decisions.md).

## Authority and use

Established story and gameplay direction is stated separately from design proposals and unresolved implementation choices. Any unimplemented system described here is not a claim about the current build. Sources are cited inline by file and section; section references avoid line numbers because the bible is being revised in parallel.

## SAINT-5

### Established behavior

The maintenance machine's designation is **SAINT-5**. Main power visibly reactivates it. Its first useful work is at the stasis bay: it extinguishes the electrical fire and repairs wiring, establishing its maintenance purpose before the player encounters its hostility. It is a large, durable industrial machine with manipulators, tools and a drill, without conventional military armament. It is not a combat boss the player can destroy. (Sources: `tmp/lore-intake/gone_story_summary.md` §§6, 36-37; `tmp/lore-intake/reconciliation.md` §§1.11, 2.17.)

SAINT-5 is hostile because the protagonist has been classified as a threat under its containment instructions. When it finds the protagonist conscious, lethal force is permitted if it cannot contain him safely; if it finds him unconscious, it may return him to stasis. The exact decision rules remain open. (Sources: story summary §§6, 8; reconciliation §1.11.)

SAINT-5 is **not hunting the player**. Its primary work is ship repair. It follows maintenance priorities and can attack when the protagonist is in its area or path. The player is generally faster. It usually gives repair work priority over pursuing the protagonist. The order of urgent repairs, containment and attack is not specified. (Sources: story summary §6; reconciliation §§1.11, 2.17.)

### Established cooperation and manipulation

SAINT-5 can repair faults, undo deliberate disconnections, and respond to maintenance faults the player creates. The player can manipulate its priorities and cooperate indirectly with it. (Sources: story summary §6; docs/design/biblia.md §§35-36.)

### Established recognition and avoidance

SAINT-5 recognizes a conscious person's body. A different badge changes ship authentication, but does not fool the robot's physical recognition. It avoids heavily irradiated areas until the hazard is reduced or resolved. Exact boundaries and avoidance behavior remain open. (Sources: story summary §§6, 10; puzzle handoff §§6-7; reconciliation §1.11.)

### Proposal: cooperation scheduling

Use a priority-based job model, with arbitration that prevents a repeated fault from freezing its behavior or creating an unlimited distraction. Scheduler details remain open. (Sources: puzzle handoff §§7, 10; reconciliation §1.11.)

### Ending ambiguity

The final image leaves SAINT-5's action unresolved. It approaches the protagonist's closed stasis pod and extends a tool. It may be repairing, inspecting, disconnecting or enforcing containment. The ending must not confirm which interpretation is correct. (Sources: story summary §§33, 38; reconciliation §§1.10, 4.8.)

## Badges, credentials and access

### Established facts

The protagonist's badge is found in or near his quarters. It provides his identity and useful access, and readers present the active carried credential automatically when the player uses them. Some security systems react aggressively to the protagonist's identity. (Sources: story summary §§10, 38; reconciliation §§1.12, 2.22.)

A dead crew member's badge grants less access, but does not provoke the same identity-specific response. Its location and discovery timing are open; an infirmary or isolated compartment is only a proposal. (Sources: story summary §10; puzzle handoff §6; reconciliation §§1.12, 3.11.)

The lover's badge is found in astrometrics. Picking it up triggers a brief memory of her body and the protagonist's cry of “No!” The badge grants higher access, including command and the captain's quarters. Her exact service post is not established. (Sources: story summary §§11-12; reconciliation §§1.12, 1.13, 2.19.)

### Established credential interaction

The player selects the active carried credential as equipment state. A contextual reader interaction presents it automatically, without a verb menu. SAINT-5 recognizes bodies, not cards. (Sources: decisions brief §9; story summary §§10-11.)

### Proposal: credential interface

Credential selection can be presented as an equipment-state control; exact interface presentation remains open. (Source: puzzle handoff §§5-6.)

### Established access distinctions

Identity and privilege are separate. The protagonist's badge can offer broad access while exposing his identity to hostile security. The corpse badge can avoid that particular response while lacking permissions. The lover's badge provides greater access. The complete access hierarchy, clearance levels, devices that first reveal hostility, and any device-specific exception remain open. Alternate credentials affect ship authentication, not SAINT-5's physical recognition. (Sources: story summary §§10-11; puzzle handoff §6; reconciliation §§1.12, 2.17.)

## Power generation and distribution

### Established design rules

The ship distinguishes generation from distribution. Restoring main generation does not repair broken buses, breakers, wiring, controllers, computers or local circuits, and does not make every compartment safe or operational. Emergency, secondary and main generation, storage, buses, local distribution and isolation are conceptual system elements; the detailed model is not complete. (Sources: `docs/design/biblia.md` Part IV §§29-30 and Part V §46; story summary §§4-5; reconciliation §1.14.)

The secondary generator supplies limited power before main power. Early power can support only selected systems or compartments. At the current playable opening, a console in the secondary-power room uses two presses: the first displays “Inactivo,” the second activates the generator. That implementation changes lighting in the hall and power room; it is not a general power or life-support simulation. (Sources: story summary §§4-5; repository baseline verified in `app/game.gd`, `app/power_room.gd`, `app/hallway.gd`, `tests/power_room_test.gd`.)

**Proposal:** Require a viable cooling solution and usable electrical output connection before restoring main generation. Restoring it activates more systems, including SAINT-5, but distribution repairs continue afterward. The startup dependency is proposed, while generation and distribution remain distinct. (Sources: story summary §§5-6; puzzle handoff §§3, 5, 9.)

**Handoff engineering direction:** Keep simulation deterministic and testable headless, with tests independent of visual rendering. Keep rendering separate from simulation state, following the repository's `sim/` and `app/` separation. Extend the existing headless simulation tests and harness lanes rather than building a parallel harness. This is the handoff's direction for proposed engineering work, not a claim about the current implementation. (Source: puzzle handoff §§9, 11-12.)

### Design proposal: loads and output alternatives

Model generation capacity, distribution connectivity and loads as distinct state. Candidate loads include ventilation, oxygen recycling, CO₂ scrubbing, lighting, doors, computers, cooling, sensors and security. The player can route limited output among them, with consequences for safety and access. Proposed engineering alternatives are repair of the primary cooling loop or isolation with reduced-capacity auxiliary cooling, and rebuilding the output connection or installing a lower-capacity bypass. These alternatives are design candidates, not approved implementations or a settled electrical budget. (Sources: puzzle handoff §§5, 9; reconciliation §§1.14-1.15, 4.7.)

## Atmosphere and environmental control

Atmosphere includes oxygen, carbon dioxide, pressure, circulation, temperature and smoke. Powering a service does not make an area safe instantly; conditions change over time. Turning off support can create a temporary route while air quality deteriorates. Oxygen alone does not guarantee safety if CO₂ or smoke remains hazardous. (Sources: bible Part V §45; story summary §§4-5; reconciliation §1.14.)

**Proposal:** Use compartment-level state for the environmental systems and a visible, understandable route cost when power is reallocated. Potential recovery routes include restoring power, repairing a scrubber or using temporary protective air. Whether the first power tradeoff uses mutually exclusive loads or inefficient simultaneous loads with brownouts remains open. (Sources: puzzle handoff §§5, 9, 13C; reconciliation §§1.14, 2.23.)

Numerical limits for atmosphere, exposure, load capacity, cooling and safe duration are open. Do not present thresholds as settled. (Sources: bible Part V §45; reconciliation §§2.23, 2.26.)

## Doors and access conditions

A door may have separate mechanical condition, electrical actuation, authorization and pressure constraints. Main power is not a universal unlock, and a temporary atmosphere route is not a permanent repair. Multiple solutions such as credentials, a service route, manual release or a repaired actuator are proposals for applicable obstacles, not a promise that each door has every option. (Sources: puzzle handoff §§5, 9; reconciliation §1.14.)

## Telemetry and the wrist map

The protagonist eventually acquires a wearable arm console. It can provide a structural schematic, connected system status and environmental, power or door information where functioning equipment supplies it. Initially, internal sensors do not provide reliable live damage data or the robot's position. Later telemetry remains limited: a robot marker may disappear in unmonitored areas, and fires, breaches and damage may remain unknown without working sensors. (Sources: story summary §7; bible Part IV §§34, 44; reconciliation §§1.11-1.12, 2.21.)

**Proposal:** Keep structural room names and intended connections distinct from live measurements. Do not give the map knowledge that the ship's functioning sensors do not have. (Sources: puzzle handoff §§2, 9; reconciliation §§1.14, 2.21.)

## Fire and smoke

The opening stasis bay contains an electrical fire, sparks and smoke. The intended opening asks the player to take a fallen metal structural piece, force the jammed hatch and leave before smoke incapacitates or kills him. SAINT-5 can extinguish a small electrical fire and repair wiring; major structural fires require further intervention. (Sources: story summary §§4, 6, 36; bible Part IV §36; reconciliation §§1.11, 1.14.)

At the inspected repository baseline, smoke symptoms are reversible exposure, audio and vision effects, not a completed death timer. The opening's intended lethal urgency must not be described as already implemented. (Sources: `tmp/lore-intake/reconciliation.md` §5; verified in `sim/smoke_symptoms.gd`.)

## Radiation

At least one ship section is dangerously irradiated, and the armory is in that section. The protagonist never obtains a conventional weapon; the historical gunshot does not establish present-day weapon gameplay. SAINT-5 avoids the hazardous area until conditions change. The radiation source, mechanism, boundary and remediation are open. (Sources: bible Part IV §35 and Part V §48; story summary §6; reconciliation §§1.11, 2.26.)

## Death, stasis rescues and difficulty

If the protagonist loses consciousness from unsafe air, SAINT-5 may return him to stasis. A later fault may wake him years or decades later. Between awakenings, the ship may change in visible ways: systems SAINT-5 repaired can fail again, SAINT-5 may have repaired other systems while the protagonist was in stasis, other areas can deteriorate, new sections can become depressurized or damaged, and wear can increase. (Source: story summary §8.) On the first rescue, the player initially reads these changes as ship deterioration rather than elapsed decades. Exact changes and timing remain open. Roughly three rescues are a hidden, unreliable design concept, not a visible lives counter or ordinary respawn rule. (Sources: bible Part IV §37; story summary §8; reconciliation §1.9.)

Easy mode allows conventional save and load. Hard mode removes conventional save/load as a way to reverse consequences and relies on conditional stasis rescue where available. Death can still be permanent. Exact persistence and rescue implementation are open. (Sources: bible Part IV §38; story summary §8; reconciliation §1.9.)

## Open items

Record unresolved implementation and narrative decisions in [docs/design/decisions.md](decisions.md), including access hierarchy and hostile reader, SAINT-5's priority arbitration, radiation cause and boundaries, atmosphere and load thresholds, and stasis behavior. The present document does not establish numerical thresholds or fill those gaps. (Sources: reconciliation §§1.11-1.14, 2.23, 2.26.)
