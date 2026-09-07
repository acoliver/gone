# gone (working title): game concept

## Pitch

You wake from stasis with no memory, alone on a derelict military starship.
The crew is gone. Power is failing, smoke hangs in the corridors, and
something is alive aboard. You survive by scavenging, hiding, and repairing
the ship system by system, and every repair you complete pushes back the
dark and uncovers what happened to the people who left their belongings
behind.

The game is first person, dark, and built around high-end rendering:
volumetric smoke, emergency lighting, baked-and-crossfaded global
illumination, and a filmic post pipeline. The fantasy is not power. The
fantasy is competence: your hands know this ship even if you do not know
your own name.

## Setting

A colonial warship in the Battlestar Galactica tradition: industrial,
military, lived-in. Riveted bulkheads, cable runs, hydraulic doors, damage
control lockers, stasis racks for long transits. The ship is adrift and
internally wounded: dead compartments, localized fires long smothered,
hull breaches sealed with foam, emergency power only where circuits still
hold.

The ship is the level, the puzzle, and the story archive at once. Its
layout is a graph of compartments connected by hatches and crawlways, which
keeps navigation legible and lets threats and sound travel in believable
ways.

## Design pillars

1. **Atmosphere is the first antagonist.** Before any creature appears,
   darkness, smoke, failing power, and the ship's own noises are the
   opposition. The opening has no enemy at all and must still feel
   dangerous.
2. **Competence without identity.** The protagonist has amnesia but intact
   skills. Players learn who they were through evidence: logs, duty
   rosters, personal effects, other people's messages about them. Occasional
   "muscle memory" moments (your hands move through a breaker sequence
   before you decide to) fade as the game proceeds.
3. **Repair is progression.** Restoring power, atmosphere, hull, and comms
   is both the gameplay loop and the narrative engine. Each repair has a
   visible payoff: a compartment moves from red emergency light to working
   light, fog clears as atmosphere scrubbers spin up.
4. **Scrappy survival, not gunfantasy.** Tools before weapons. A pry bar,
   a flashlamp, a soldering iron, a door you can seal behind you. Combat,
   when it arrives, is tense and marginal, and running or sealing a hatch
   is usually the smarter play.

## Core loop

Explore a dark compartment. Find a failed ship system blocking progress.
Scavenge tools and knowledge (manuals, codes, spare parts). Perform the
repair through a diegetic minigame. Watch the ship state visibly improve.
Gain access to the next compartment and the next piece of the story.
Repeat under escalating threat.

## The ship systems simulation

Underneath the rendering, the ship is a simulated graph, kept headless and
unit-testable so it never depends on the engine's render layer:

- **Power grid**: nodes (batteries, generators, breakers, loads) and edges
  (bus runs). Breakers trip, loads brown out, rerouting has consequences.
- **Atmosphere**: per-compartment smoke density, oxygen, pressure. Drives
  fog rendering and player stamina and coughing.
- **Hull integrity**: breaches, foam patches, compartments sealed or open.
- **Comms**: antennae, relays, damaged transceivers. Gates story delivery.

Repairs are diegetic interfaces onto this simulation: reroute power at a
breaker panel, patch a hull breach, align a dish by hand, bypass a jammed
door's circuits. The minigame is the ship's real interface, not a popup.

## The player character

Name unknown at the start. Crew occupation unknown, discoverable. Physical
capabilities: walk, crouch, climb short ledges, carry limited tools,
interact with panels and valves. No inventory grid fantasy; a small
toolbelt of equipment the player earns.

## Threats

Escalation starts small and grounded:

- **Milestone threat one: a dog.** A former crew animal, now rabid or
  changed. It hunts by sound, patrols the compartment graph on authored
  waypoints, and forces the player to move quietly and use doors. This is
  the tutorial enemy for the stealth and sound systems.
- Later threats (months out, kept deliberately unspecified here) build on
  the same rules: they live in the ship's graph, they respond to light and
  sound, and they can be delayed, avoided, or trapped rather than
  outgunned.

## Art direction

Dark, filmic, physically grounded. Materials are industrial: painted steel,
worn floor plate, rubber gaskets, cloth. Lighting carries the emotion:
emergency red, sparks, flashlight spill, the slow sunrise of a restored
deck. Volumetric smoke is a first-class material, not a decal. The target
is 4K at 60 FPS on the dev machine (Apple M4 Max), with quality tiers for
lesser hardware. Greybox first; art passes come after the feel is proven.

## Audio direction

Diegetic-first: the ship's sounds are the score. Breakers, airflow, hull
creak, distant thumps, the dog's claws on floor plate. Crew voices exist
only as recordings (audio logs), which pairs with the sibling `voices`
project for performance and casting. Music is sparse and sourced, if it
exists at all.

## Milestones

- **M1, the stasis room (epic #2).** Wake up, blink, see the room, get
  out of the pod, walk, reach the door, and the door does not open. The
  full opening beat is specified at the end of this document.
- **M2, hands.** Interaction surfaces, toolbelt, pickup and carry, the
  first diegetic panel.
- **M3, first repair.** Restore local power to open the stasis room door;
  the first lighting-state crossfade pays off.
- **M4, story channel.** Terminals, datapads, the first audio log, the
  first security monitor with scrubbable video.
- **M5, the dog.** Sound propagation, waypoint patrols, stealth movement,
  the first encounter.
- **M6, chapter one playable.** Art pass on chapter one compartments,
  pacing, save/load.

## The opening beat (issue #1 scope)

A rectangular stasis room. Seven stasis pods. The player wakes inside the
seventh pod, lying back, eyes aimed at the ceiling.

The ceiling has torn cable runs: hanging wires, insulation split,
occasional electrical sparks that strobe the room. Smoke drifts from the
ceiling, denser there than at floor level. The only light is emergency
red: the pods' dead indicators and a few red maintenance fixtures.

The player's eyes open in stages (the blink pass). They see sparks, smoke,
red light. Looking around from the pod, the room shows nothing but walls
and the other six pods, all empty, some still closed, all dead.

The player sits up, climbs out of the pod, stands, and walks. Movement is
slow to steady, like limbs waking. They cross the room to the only door
and try it. The door does not open: a shudder, a clunk, and it holds.
That is the end of epic #2. The stuck door is the hook that pulls the
player into the repair loop.
