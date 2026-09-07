# gone: story

## The opening

Seven stasis pods in a rectangular room. The player wakes in the seventh,
flat on their back, eyes aimed at the ceiling. The ceiling is wounded:
cable trays torn open, wires hanging in loops, insulation split. Sparks
arc through them at irregular intervals, strobing the room in white
against the permanent red of the emergency lighting. Smoke drifts down
from the ceiling in slow sheets.

Eyes open in stages. The first blink is a smear of light and blur. The
second resolves shapes: wires, smoke, a red glow. The third holds, and
the player can look around.

What they see: walls, and six other stasis pods. All empty. Some stand
open with their occupancy blankets still hanging; some are sealed and
dark, their status indicators dead. Nobody waits. Nobody answers.

The player's body remembers things the player does not: how to pop the
pod's restraint, how to swing out, how to stand despite legs full of
pins and needles. They cross the room on unsteady feet, and try the only
door. It shudders, clunks, and does not open. The room holds its red
silence.

That is where issue #1 ends, and where the story starts: the player must
make this door open, and everything they learn while doing it is a piece
of what happened here.

## The ship

A colonial escort frigate (working designation; the name is discoverable
story content). Military-industrial: damage control lockers, munitions
racks long secured, crew mess, ops deck, engineering aft. The ship
survived something, and the something left wounds in a pattern the player
learns to read: shrapnel scars run bow-to-stern on the port side; the
fires started in engineering and were fought compartment by compartment;
the evacuation, if that is what it was, left in a hurry and left
personal effects behind.

## The crew

Gone. Not one body in the opening chapters, only traces: a duty roster
with a name half-erased, meal trays abandoned mid-shift, a locker of
civilian clothes that belongs to no one the player meets. The mystery of
the crew is the spine of the story, revealed through what they left:
terminals, datapads, audio logs, and the ship's own security footage,
which the player can scrub through on in-world monitors. Some of the
footage is gameplay: watching where a crew member ran tells you which
hatch they used.

## Who you are

Amnesia, but the practical kind: skills intact, identity missing. You
can solder a bus bar but not say what rank holds that certification. The
story delivers identity as evidence:

- Your name appears in other people's logs before you ever find your own.
- Your quarters exist, and someone else's things are mixed with yours.
- Muscle memory moments play in the first hours (your hands run a breaker
  sequence you never chose to learn) and fade as the picture completes.

The design rule from the concept doc holds: competence without identity.
The player is never told who they were; they assemble it, and the
assembled answer is a choice the game acknowledges but does not grade.

## Story delivery channels

- **Terminals and datapads**: text, readable at the player's pace. Ships
  systems mail, personal notes, maintenance complaints that map to
  repairs the player will perform.
- **Crew audio logs**: performed voice, recovered in pieces. The sibling
  `voices` project (cast, recordings, library tooling) is the natural
  production pipeline for these.
- **Security monitors**: in-world, scrubbable video. Doubles as gameplay
  (recon of compartments before entering) and as the story's most
  reliable witness. Playback uses the video playback options surveyed in
  the technology doc, with an image-sequence fallback.
- **Environmental storytelling**: the wounds and debris of the ship
  itself, readable without a single word.
- **Scripted moments**: a custom timeline system (Bevy has no cutscene
  tooling; we build a small one) for controlled beats like the wake-up.

## Threat arc

The dog comes first. It was the crew's animal; something aboard or in
the food supply changed it. It hunts by sound in the compartment graph,
and it teaches the player the rules the later threats follow: listen,
move quietly, use doors, know two ways out. What comes after the dog is
deliberately unspecified in this document; the writing will earn it from
what the crew's evidence says happened. The constraint from the concept
doc stands: threats live in the ship's systems and can be delayed,
avoided, or trapped rather than outgunned.

## Chapter one arc

1. **Wake** (issue #1). The stasis room beat described above.
2. **The first repair.** Local power to the stasis room: the player finds
   the room's breaker cabinet, scavenges a fuse or bypasses the fault,
   and the door opens. The payoff is the first lighting-state crossfade
   the player causes, from emergency red toward partial power.
3. **The corridor.** First exposure to the wider ship, first smoke
   management, first signs of the crew's departure.
4. **First log.** The first terminal message addressed to people who are
   not here, one of whom might be the player.
5. **The dog's presence.** Heard before seen: claws on floor plate
   somewhere below. Chapter one ends with the first full encounter, and
   the player survives it without a weapon.

## Tone

Isolation, competence, and repair as agency. The ship is not a haunted
house; it is a machine that is badly hurt and can be healed one system at
a time. Fear comes from being alone in a dark machine that makes honest
noises, not from scripted startles. Reference points for mood: the
derelict-ship passages of Battlestar Galactica, the crew-horror dread of
Alien, identity-through-terminals in System Shock and SOMA, diegetic
interfaces in Dead Space. We borrow their discipline, not their monsters.

## Working title

`gone` is the working title: the crew, the memory, the ship's mission,
possibly the player's old self. A final title is a later decision.
