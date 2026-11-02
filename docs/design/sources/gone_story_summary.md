# GONE — Story / Narrative / Gameplay Summary

## Purpose

This document summarizes the current story, narrative structure, game mechanics, world logic, reveal order, and important scene/log concepts for **Gone**. It is intended as implementation context for a coding agent.

The central design rule is:

> **The player is given information, places, tools, memories, and functioning systems — not quest lists or decision trees.**

The game is dark, serious, exploratory, and systemic. Much of the story is reconstructed indirectly through rooms, personal objects, recovered video, damaged computers, archival records, involuntary memories, and the behavior of the ship itself.

---

# 1. Core Premise

The player wakes from a stasis pod aboard a badly damaged, apparently abandoned interstellar ship.

The room is filling with smoke from an electrical fire. The player has **amnesia**, but their procedural memory remains intact: they know how ship systems work, know the ship's layout in flashes, and can perform technically sophisticated tasks without remembering who they are or why they are aboard.

The immediate goal is simply survival and repairing the ship enough to stay alive.

Over the course of the game the player gradually discovers:

- the ship has been adrift for **more than 100 years**;
- the player was not merely a crewmember but an infiltrator / saboteur from the civilization the ship was sent against;
- the ship's crew were not monsters — they were largely ordinary, decent people with families, pets, friends, arguments, political disagreements, and personal lives;
- the player became genuinely close to the captain and genuinely fell in love with the captain's daughter;
- the player sabotaged the ship to prevent the destruction of their home world;
- the captain's daughter discovered the sabotage accidentally, because she was coming to surprise the player and tell them she was pregnant;
- during the confrontation, the player tried to stop/restrain her and she was accidentally shot and killed;
- the captain had been close to refusing the extermination order on moral/legal grounds, but his daughter's death at the hands of an infiltrator convinced him that the enemy would stop at nothing and the extermination was necessary;
- the surviving crew escaped and the player's world was ultimately sterilized anyway;
- the player's sabotage may therefore have helped cause the genocide they were trying to prevent;
- the only reachable habitable world at the end is the civilization the player infiltrated — the former enemy;
- the ship can probably reach it, but only in roughly **30 years**, requiring the player to enter stasis again;
- the ship may not survive the journey, the pod may not work, and the maintenance robot that has alternately saved and attacked the player is still aboard.

The final image is the maintenance robot entering the stasis room and leaning over the player's pod. It is unclear whether it is going to repair something, contain the player, or kill them.

---

# 2. Tone and Narrative Style

## Tone

- Serious
- Dark
- Melancholic
- Human rather than melodramatic
- Politically and morally ambiguous
- Occasional dry / buried Easter eggs, but never broad comedy

## Narrative presentation

Avoid conventional RPG exposition and questing.

There should generally be:

- no mission checklist such as "Repair Astrometrics";
- no dialogue-wheel decision trees;
- no interaction menus saying "Use badge on reader";
- no constant protagonist narration;
- no large expository cutscenes explaining the world;
- no obvious morality meter.

The player acts in the world directly.

Examples:

- If the player has the correct badge and interacts with a reader, the character automatically uses it.
- If they have the correct tool and interact with a damaged panel, the appropriate action occurs.
- If they have a replacement part and interact with the correct socket, it is installed.
- Whether this is strategically wise is left to the player.

The player's decisions come from **where they go, what they repair, what they carry, what power they route, which badge they use, whether they manipulate the maintenance bot, and how much risk they take**.

---

# 3. Protagonist Memory Model

The player has major autobiographical memory loss but retains procedural expertise.

They know:

- how to repair ship systems;
- how to isolate power;
- how to operate environmental control;
- how to navigate the ship in fragments;
- what certain components do;
- how to use technical systems;
- security / engineering procedures that later become evidence about who they were.

They do **not** initially remember:

- their own identity;
- the mission;
- the war;
- the captain;
- the captain's daughter / lover;
- their infiltration;
- their sabotage;
- their role in her death;
- how long the ship has been drifting.

Thoughts should be sparse, tactical, and involuntary.

Examples:

- *Emergency lights. Panel next to the door.*
- *How did I know that?*
- *Wait... who am I?*
- *Power. Secondary generator is straight ahead.*
- *Environmental first.*
- *No!*
- *I remember.*

The UI tells the player what the protagonist knows technically. Internal thoughts should be used only when something is personally significant, instinctive, or emotionally intrusive.

---

# 4. Opening Sequence

## 4.1 Stasis room

The player wakes in an open stasis pod.

Conditions:

- room filling with smoke;
- active electrical fire / sparking system;
- exit door broken/jammed;
- visibility worsening;
- if the player takes too long, they die from smoke.

A fallen piece of ceiling / structural support can be picked up and used as a pry bar.

No explicit interaction menu. The player picks it up, approaches the door, presses the action key, and the character automatically uses it to force the door open.

The opening should begin with physical urgency rather than story exposition.

## 4.2 Dark corridor

Outside the room, the hallway is nearly or completely dark.

This is the first time the protagonist hears their own internal voice:

> *Emergency lights. Panel next to the door.*

The player interacts with the panel.

Emergency lights begin blinking / pulsing down the corridor.

Then:

> *How did I know that?*
>
> *Wait... who am I?*

Then the character's technical instincts immediately override introspection:

> *Power. Secondary generator is straight ahead.*

The player is at one end of the hall. The secondary generator room is directly ahead at the other end.

## 4.3 Secondary generator / first terminal

The secondary generator room contains a functioning emergency-powered console.

Initially the ship layout is available only in a very limited form.

Possible system display:

- MAIN POWER: OFFLINE
- PRIMARY SENSOR NETWORK: OFFLINE
- NAVIGATION: UNAVAILABLE
- EXTERNAL TELEMETRY: UNAVAILABLE
- DAMAGE CONTROL: NO DATA

The character understands that main power must come back before most sensors are useful.

Thought:

> *Need main power before the sensors will tell me anything.*

Then:

> *Environmental first.*

Environmental status shows something like:

- OXYGEN RECYCLING: OFFLINE
- CO2 SCRUBBING: OFFLINE
- ATMOSPHERIC CIRCULATION: MINIMAL
- PRIMARY ENVIRONMENTAL CONTROLLER: NO RESPONSE
- CO2 RISING

There may be an estimated breathable-atmosphere window, but it does not have to behave like a visible game timer.

The secondary generator can only partially restore systems. It does not solve the ship.

---

# 5. Power and Environmental Gameplay

Restoring main power is **not** equivalent to restoring the whole ship.

The main reactor can produce power, but distribution is fragmented because:

- buses are damaged;
- distribution hardware is broken;
- computers are offline;
- breakers are damaged;
- local wiring is destroyed;
- parts of the ship are isolated;
- some compartments are irradiated / unsafe;
- sections may have no sensors or environmental control.

The player has to keep repairing power delivery and computing infrastructure throughout the game.

## Environmental control

Before main power is online, the player can restore environmental control only partially and only to selected areas.

The player may need to choose which compartments receive:

- oxygen recycling;
- CO2 scrubbing;
- circulation;
- pressure / temperature control.

A newly powered section takes time to become safely breathable.

The player can enter a section after turning environmental support off, but oxygen and air quality deteriorate. If they remain too long:

- vision worsens;
- movement / cognition can degrade;
- they eventually collapse.

If they simply die, normal death rules apply.

If they become unconscious and the maintenance bot finds them, the bot may return them to stasis.

---

# 6. Main Power and SAINT-5 Maintenance Robot

When main power comes back online, a large autonomous maintenance robot becomes active.

Designation: **SAINT-5**.

Visually, it is an enormous industrial machine vaguely evocative of Johnny 5, but not a comedy character. It is bulky, durable, has manipulator arms, industrial tools, and a drill. It is designed to survive serious physical punishment.

It is not armed in the conventional sense.

The player is a soft human body; SAINT-5 is heavy industrial machinery.

The player generally cannot damage or destroy it meaningfully.

## First behavior after activation

The robot immediately begins repairing the ship.

One of its first actions is to return to the original stasis room and:

- extinguish the small electrical fire;
- repair damaged wiring / electrical infrastructure;
- begin restoring that compartment.

This establishes that the robot is genuinely a maintenance system, not simply an enemy.

## Hostility

When SAINT-5 encounters the conscious player, it attacks.

Initially the player assumes:

- its sensors are damaged;
- its friend/foe system is broken;
- it is simply malfunctioning.

Later the player learns that it has been instructed that the protagonist is dangerous.

Its actual behavior is closer to:

- if protagonist is active/conscious and cannot be safely contained: lethal force permitted;
- if protagonist is unconscious: return them to stasis.

Thus SAINT-5 can both preserve and attack the protagonist without contradiction.

## It is not hunting the player

This is critical.

SAINT-5 is primarily trying to repair the ship.

It has a maintenance queue and travels to faults such as:

- electrical shorts;
- sparks;
- damaged doors;
- local wiring faults;
- small fires;
- damaged machinery;
- other maintainable systems.

It does **not** generally chase the player across the ship unless they are in its current area / path or otherwise provoke its security behavior.

The player is usually faster.

## Player / robot cooperation

The game should require uneasy indirect cooperation.

The robot can repair things the player would otherwise have to repair manually.

The player can also manipulate its priorities by creating faults.

For example:

- create a small electrical short elsewhere;
- overload a panel;
- intentionally cause a serviceable electrical fault;
- redirect its maintenance queue;
- lure it away from an area the player needs to access.

Sometimes the best choice is to let SAINT-5 repair something.

Sometimes it is better to do the repair personally because SAINT-5's presence is too dangerous.

Sometimes the player needs to create a distraction to move it elsewhere.

The bot knows its operational limits. For example, it generally avoids a heavily irradiated section until radiation is dealt with.

---

# 7. Internal Sensors and Map

The player eventually acquires a wearable arm device that functions as a portable console.

Initially it provides:

- ship map / schematic;
- connected system status;
- environmental information where available;
- power state where connected;
- access / door information.

However, before internal sensors are repaired it does **not** provide a live damage map or reliable SAINT-5 location.

Even after sensors return, the map should only know what functioning sensors actually know.

If SAINT-5 moves into an unmonitored area, its marker can disappear.

Likewise:

- damage appears only where telemetry works;
- fires are visible only where detected;
- breaches may remain unknown;
- some areas remain blind.

This preserves uncertainty and prevents the wrist device from becoming omniscient.

---

# 8. Death, Stasis, and Hidden Century Timeline

The game has a hidden pseudo-life system tied to stasis.

If the player collapses from low oxygen and SAINT-5 finds them unconscious, it can return them to the stasis pod.

The player then does **not** necessarily wake up soon.

They awaken only when some later fault, power failure, ship damage, or stasis emergency causes the pod to release them again.

This can happen after **years or decades**.

The player does not initially know this.

The concept is that the player can effectively receive roughly three stasis rescues / "lives," but unreliably.

Possible hidden intervals might total more than a century, for example several decades per cycle.

The ship changes subtly between awakenings:

- some repaired systems fail again;
- new sections deteriorate;
- SAINT-5 has repaired other systems;
- dust / corrosion / wear increase;
- some compartments become depressurized or newly damaged;
- formerly working systems may have failed.

The player initially attributes this to ship deterioration rather than elapsed decades.

## Difficulty modes

Easy mode:

- conventional save/load is available;
- player can effectively cheat death through saves.

Hard mode:

- no conventional save/load;
- death is serious;
- stasis rescue is the only partial recovery mechanism when conditions allow it.

---

# 9. Early Personal Discovery: Player's Quarters

Soon after main power / basic access improves, one of the first places the protagonist naturally wants to go is **their own quarters**.

This is not a quest marker. The player simply knows where their room is.

## Entering the quarters: memory transition

When the player enters, the room appears not as it is now, but as the protagonist remembers it.

The transition should not be explicitly announced as a flashback.

The room is suddenly:

- clean;
- pristine;
- warm;
- bright;
- intact;
- clearly lived in;
- part of a new, healthy ship.

The player can walk around normally.

They see:

- a picture of themselves with a woman;
- personal effects;
- evidence of a shared intimate life;
- a uniform resembling what she wore;
- possibly other ordinary relationship details.

The protagonist may have a sensory-memory impression of her — effectively "smelling" her even though the actual scent obviously cannot survive a century.

This is memory as sensation, not literal present-day smell.

## Desk console scene

The player sits at / activates the console.

The image initially appears corrupted, like a damaged digital video file with black blocks / digital tearing.

Then the woman's face resolves.

Possible line:

> "Hi honey. If you see this then I'm actually waiting for you in astrometrics because I was coming to surprise you but... you decided to slack off early."

The important facts:

- she clearly loves the protagonist;
- she expected to find them in their room;
- she is now in astrometrics;
- she had a "surprise" for them.

The player does **not** yet know the surprise was that she was pregnant.

The video then fails abruptly.

Example:

> MAIN SYSTEM FAULT AT ADDRESS 14F4:9000  
> SYSTEM UNAVAILABLE

When the player looks up from the console, the memory is gone.

The room is now:

- old;
- damaged;
- corroded;
- faded;
- deteriorated like the rest of the ship.

The picture is still physically / digitally present in some form as appropriate, but the contrast is the point.

No exposition should explain why the room changed.

---

# 10. Badge and Access System

The player finds their own security badge in / around their quarters.

The badge provides:

- their name;
- identity;
- useful access to parts of the ship.

Initially the badge is purely beneficial.

When the player interacts with a reader while carrying it, it is automatically used.

The player does not choose from a menu.

Over time, however, using the badge causes certain systems to react more aggressively.

The ship is not simply malfunctioning. The protagonist's identity has been marked as a threat.

## Later corpse / alternate badge

Later the player finds another dead crewmember and their badge.

Using this badge:

- grants less access;
- may produce "insufficient clearance";
- but does not provoke the same hostile response.

This is the first strong proof that security is not merely broken.

The system knows who the protagonist is and treats them differently.

This should be discovered experimentally, not explained immediately.

---

# 11. Astrometrics and the Lover's Badge

The woman from the quarters recording is the captain's daughter and the protagonist's lover.

The player does not know this at first.

Because her video said she was waiting in astrometrics, the player may naturally choose to go there, but the game does not create a mission objective.

## No flashback on entering

Entering astrometrics itself does not trigger a major memory.

The player explores the damaged room.

They find **her security badge**.

When they pick it up, a memory flashes:

- pristine astrometrics;
- her body on the floor;
- blood;
- possibly the removed S-drive component nearby, but without context;
- protagonist reaction: *"No!"*

Then snap back to the present.

The player learns only:

- she died here;
- the protagonist was present or saw her body;
- something terrible happened.

They do not yet know why she died or who killed her.

Her badge grants higher access, including command areas and the captain's quarters.

---

# 12. Captain's Quarters and Family Relationship Reveal

Using her badge, the player can enter command areas and eventually the captain's quarters.

The captain's console has a personal screensaver / rotating image set.

Images include:

1. The protagonist, the captain, and the daughter together, relaxed and obviously close.
2. The daughter as a teenager beside a younger version of the captain.
3. The daughter as a baby in the captain's arms beside a woman who strongly resembles the adult daughter.

The game does not explicitly say "she is his daughter."

The player should infer it.

This also reveals that the protagonist was not merely romantically involved with her but was close enough to the captain to be part of the family circle.

The captain is effectively a father figure to the protagonist in a twisted retrospective sense.

---

# 13. Crew Rooms, Logs, Mementos, and Misdirection

Many rooms / offices can be explored.

Their contents should either:

- humanize the crew;
- provide incomplete evidence;
- create plausible misdirection;
- reveal political disagreement;
- deepen relationships;
- or quietly foreshadow later truths.

Crew should not all be saints.

They can be:

- kind;
- funny;
- selfish;
- impatient;
- hard-line;
- sentimental;
- politically divided;
- loving parents;
- animal lovers;
- militarists;
- critics of command;
- critics of the enemy;
- critics of their own society.

The point is that they are ordinary people, not a lineup of villains.

Some personal material should be purely sweet and contain no clue at all.

Examples:

- child drawings;
- videos of pets;
- birthday messages;
- stupid jokes;
- complaints about stolen food / coffee;
- affectionate messages;
- mundane relationship material.

Other material can be true but misleading because the player lacks context.

Example:

> "He's been acting strange for days."

The player may initially assume this refers to the captain or another suspect. Much later they learn it referred to the protagonist.

The game should prefer **incomplete truths over fake clues**.

---

# 14. The Captain's Old Memoir

One recovered personal recording from the captain predates the crisis and illustrates how he once thought about interstellar war.

Approximate content:

> "Despite what you might read in science fiction, war is unlikely in space. For one, life is rare. We have only ever encountered it once. Secondly, war is generally over resources and there is little worth fighting for. If you dig something out of the ground but it costs you ten times what it is worth to do so, you don't fight someone to lose your shirt over the right to do it again — no, that sounds stupid. Computer, sto—"

The recording cuts off casually.

Purpose:

- humanize the captain;
- establish that interstellar war seems economically irrational;
- set up the game's central question: **what kind of resource conflict could actually make space war happen?**

---

# 15. Historical Archive: Discovery of the Other Civilization

The ship includes a historical archive.

Unlike personal media, archival records can remain digitally pristine because of preservation technology / redundancy.

The player can find very old footage — approximately a century before the mission — showing the discovery of intelligent life on another planet.

The species looks remarkably similar to the player's apparent species.

At first the player assumes:

> "We discovered aliens that look almost exactly like us."

Much later the player learns:

> **The protagonist is one of those aliens.**

The game does not need to over-explain why the two species are biologically similar unless useful later.

---

# 16. Why the Other Civilization Needs Help

The enemy civilization is undergoing irreversible biosphere collapse.

They do **not** merely need water, oxygen, or a rare mineral.

They need a massive quantity of **living ecological stock and biological infrastructure** that they cannot reproduce locally fast enough.

This may include:

- compatible microbial ecosystems;
- soil / oceanic starter ecologies;
- seed banks;
- embryo / reproductive stock;
- medical cell lines;
- agricultural biological systems;
- industrial bioreactor output;
- associated technical support and infrastructure.

Their biosphere has lost critical complexity / compatibility needed to sustain civilization at planetary scale.

They still have:

- water;
- oxygen;
- energy;
- technology;
- industry;
- spacecraft.

But without enormous external biological support they face probable extinction in roughly a century.

Long before extinction, they face:

- food collapse;
- migration;
- failed states;
- disease;
- violence;
- mass refugee flows;
- political radicalization;
- global pandemonium.

The donor / origin civilization **could** help them, but the cost would be enormous:

- decades of lower consumption;
- major industrial diversion;
- rationing;
- severe economic contraction;
- potentially strict population controls such as a one-child policy for generations;
- major sacrifice of living standards.

The refusal is therefore not "we literally cannot help."

It is closer to:

> "Saving them would radically reduce our own quality of life for decades or a century."

---

# 17. Hypocrisy and the Hard-Line Argument

The collapsing civilization is not uniformly noble.

Even while claiming desperation, it still has:

- extreme inequality;
- elites living lavishly;
- "cloud mansions" / luxury high-altitude or orbital habitats;
- wasteful consumption;
- military spending;
- political corruption;
- wealthy people consuming absurd resources while ordinary people suffer.

This gives critics a credible argument:

> "Why should our children eat paste because they destroyed their planet while they still have people living in cloud mansions?"

Importantly, hard-line speakers may deliberately treat the alien civilization collectively rather than distinguishing elites from ordinary people.

This is a political pole, not an objective description.

A representative crew log:

> "I am so tired of the bleeding hearts telling us to be understanding.
>
> They came to us, hat in hand, asking us to drag our own civilization halfway back to the Stone Age so they could keep theirs alive.
>
> They live in cloud mansions. They burn through their atmosphere for sport. They waste resources they supposedly don't have, and then tell us our children should eat paste because they destroyed their world.
>
> And when we said no?
>
> To their credit, they stopped begging.
>
> They attacked us.
>
> Suicidally. Pointlessly. They knew they couldn't win and they did it anyway.
>
> So I'm done pretending this is some misunderstanding.
>
> No demonstration of force. No aid package. No humanitarian mission.
>
> Give them what they asked for, what they sought, and what they've earned.
>
> Oblivion.
>
> Deliver the coup de grace and send them home to whatever god will still have them."

---

# 18. Political Radicalization and Why the War Escalates

The alien civilization originally asked for help.

The origin civilization refused the scale of aid requested.

The alien civilization then launched a desperate attack and lost.

Because extinction is still coming, they cannot simply give up.

Their logic is:

> "If we stop, we die."

Over time, ecological collapse radicalizes their government.

A new leader emerges who is genuinely dangerous:

- authoritarian;
- nationalist / survivalist;
- centralizes power;
- crushes domestic opposition;
- redirects industry toward war;
- argues that they will not "die politely";
- treats the origin civilization's resources as morally stolen or withheld survival resources;
- plans further war.

The protagonist does **not** like this leader or their politics.

The protagonist's motivation is not ideological loyalty.

They simply do not want everyone they have ever known to die.

## Infiltration is real

The alien civilization heavily infiltrates the origin civilization.

The political paranoia on the origin world is therefore not entirely imaginary.

There really are:

- spies;
- infiltrators;
- saboteurs;
- enemy agents;
- sleeper assets.

The protagonist is one of them.

However, the origin civilization's response becomes increasingly authoritarian and indiscriminate:

- innocent people are accused;
- refugees are treated as potential agents;
- security powers expand;
- dissent is treated as disloyalty;
- people are ruined by suspicion.

The intended thematic analogy is roughly:

> McCarthyism can be destructive and unjust even when actual spies really exist.

The threat is real; the repression is also real.

---

# 19. Refugees

As the alien world deteriorates, refugee flows increase despite the enormous distance and low survival odds.

The origin civilization increasingly turns refugees away.

This is politically and morally significant because the origin civilization had previously evolved into a relatively egalitarian, quasi-utopian society.

The captain is disturbed by the change.

He has seen:

- resource scarcity rhetoric become politically dominant;
- refugees turned away;
- security powers expand;
- language shift from "shortage" to "survival";
- ordinary dissent framed as disloyalty.

The allegory should be recognizable but not a one-to-one contemporary political mapping.

---

# 20. The Captain's Daughter / Lover

The captain's daughter is politically compassionate / "bleeding heart" by temperament.

She is not secretly informed about the extermination mission.

She believes the public story:

- the aliens asked for aid;
- aid was refused;
- they attacked in desperation;
- they lost;
- her society is responding increasingly harshly.

She thinks the refusal to help was morally wrong even though helping would be extremely costly.

Her personality is important:

- loyal to family;
- comfortable with military culture;
- proud of her father in many ways;
- politically humanitarian;
- loves animals / strays;
- "never met a stray she didn't want to keep";
- has a wild streak;
- stubborn;
- morally idealistic but not omniscient.

Part of why the protagonist genuinely falls in love with her is this trait: she cannot leave suffering alone.

In a thematic sense, the protagonist is one of her "strays," although she does not know their real origin.

## Daughter's political / philosophical log

Representative version:

> The problem with science is that it sells doubt.
>
> Uncertainty. Probabilities. Improbabilities. "This is what the evidence says today, and tomorrow we may know better."
>
> It asks you to look at the evidence and decide what it means.
>
> Religion sells certainty. Politics sells certainty. Sometimes something much darker does too. One simple truth. One explanation. Someone to belong to. Someone to blame.
>
> And history is full of things that could have gone the other way.
>
> An industrialist has a heart attack the morning he's supposed to launch some grand project. A financial panic kills an investment that, thirty years later, we realize would have been an environmental catastrophe. Someone wins an election by a fraction of a percent. Someone misses a train. Someone doesn't.
>
> Change any one of them and maybe we're the ones asking for help now.
>
> That's what bothers me when people talk about them as though they deserve this.
>
> Maybe they destroyed their world. Maybe their leaders are monsters. Maybe ours are better.
>
> But there were a thousand places where chance could have put us where they are and them where we are.
>
> Religion can tell you it was destiny.
>
> Politics can tell you it proves we were superior.
>
> And something uglier can tell you that because we have more than we need, we somehow earned the right to keep it while somebody else dies.
>
> We're all guilty of something.
>
> None of us are better.
>
> We need to be, though.
>
> I think that's what being human requires.
>
> Or, at least, that's the significance I assign to the evidence at hand.

She can also be wrong or simplistic about some things, especially the scale of infiltration. She should not be the author's omniscient moral mouthpiece.

---

# 21. The Protagonist's Infiltration and Relationships

The protagonist originally became close to the captain **because infiltration was their mission**.

The relationship with the captain began instrumentally.

The captain later introduced the protagonist to his daughter.

The relationship with her became genuine.

This distinction is central:

> **The friendship began as infiltration. The love affair became real.**

By the time of the final crisis, the protagonist has two real loyalties:

- the people of their birth world;
- the people they have come to love aboard the ship.

The protagonist may:

- despise their own authoritarian leader;
- disagree with their own side's politics;
- sympathize with criticisms of their own society;
- understand the origin civilization's fear;
- genuinely love the captain and daughter.

None of this changes the core choice:

> if the ship completes its mission, everyone the protagonist has ever known on their home world may die.

The protagonist is loyal to people, not ideology.

---

# 22. The Public Mission vs. the Actual Mission

The crew believes the mission is essentially:

- a peace / enforcement mission;
- a massive show of force;
- delivery of an aid package;
- diplomacy backed by overwhelming military capability;
- an attempt to compel a settlement and stop further attacks.

Even the captain believes this.

The real mission is sealed in the ship's computer and inaccessible even to the captain until they are near the target.

The captain receives the real orders only late in the voyage.

The actual mission is extermination.

## Primary extermination method

Trigger a chain reaction / catastrophic event in the target atmosphere that destroys the biosphere.

## Backup: bioweapon

A highly contagious, completely fatal biological agent designed to kill the target species.

Because of the extraordinary biological similarity between the species, the weapon would also kill the ship's crew if containment failed.

It therefore must be handled extremely carefully.

## Final backup: S-drive atmospheric initiation

If other methods fail, initiate a large S-fold inside the target planet's atmosphere.

This ship has the largest S-drive ever constructed.

The effect is expected to catastrophically damage the atmosphere / biosphere.

The ship itself is therefore a final weapon.

---

# 23. S-Drive / H-Drive Logic

Only a simple explanation needs to appear in the main game, but the internal logic must remain coherent.

## S-drive

Creates the folded-space geometry / wave.

Think of it as creating the medium or "water."

## H-drive

Efficiently rides / accelerates through that folded-space geometry.

Think of it as the "surfboard."

H without S is useless for interstellar travel because there is no folded-space structure to ride.

## Regular propulsion

Conventional propulsion can still move the ship while S-folded space is active, but inefficiently — effectively pushing against the fold rather than surfing it.

Travel times:

- **S + H:** ~5 years for the relevant interstellar trip.
- **S + conventional propulsion:** ~30 years.
- **No S:** normal-space propulsion only; interstellar travel becomes effectively impossible within a human lifetime, more like taking a rocket to Betelgeuse and dying millennia before arrival.

## Atmospheric S-drive history

Historically, smaller S-drives were sometimes present on atmosphere-capable ships.

Operators discovered that activating them in atmosphere could damage the atmosphere / surrounding region.

The issue was not merely deliberate misuse. In emergencies, crews facing a conventional propulsion failure would sometimes activate the S-drive to save themselves despite regulations.

That creates an obvious human-factors problem:

> It is easy to say "never activate this in atmosphere" until the alternative is dying in a crash.

The origin world therefore banned atmosphere-capable ships from carrying operational S-drives.

The current vessel is unprecedented:

- no ship this large has ever been built;
- no S-drive this large has ever existed.

The final contingency weapon is therefore based on scaling up a known atmospheric hazard to an unprecedented level.

This history may never be required exposition, but an optional archive item can exist:

**Environmental Effects of Atmospheric S-Drive Operation**

This can document historical incidents and the resulting ban.

The main game only needs to explain what S and H do and why repairing S matters.

---

# 24. Sabotage Timeline

## Earlier in the voyage: H-drive sabotage

The protagonist sabotages the H-drive as part of the original infiltration mission.

This is intended to slow the ship dramatically.

However, it is done **too late** to prevent the ship from getting dangerously close to the target world.

With H damaged, S-drive plus regular propulsion can still continue the voyage, just much more slowly.

## Near the target: real orders unlock

The sealed mission package opens.

The protagonist discovers the real extermination order and its contingencies.

Now the protagonist knows that even disabling the primary weapon is not enough because the S-drive itself can be used to devastate the planet.

## S-drive sabotage

The protagonist removes a critical, portable S-drive component.

This is much more extreme than the earlier H-drive sabotage because without the S-drive, the ship is effectively stranded on an interstellar scale.

The protagonist takes the component to astrometrics / uses astrometrics as part of the next stage of sabotage.

The exact reason can be that astrometrics is needed to:

- verify fold geometry;
- erase or alter stored fold solutions;
- determine whether the ship can still complete the mission;
- otherwise finish disabling the drive / route.

---

# 25. How the Daughter Discovers the Sabotage

The captain's daughter is **not investigating the traitor**.

She is coming to surprise the protagonist because she has discovered she is pregnant and intends to tell them.

Earlier, the message in the protagonist's quarters says she was coming to surprise them but they "slacked off early" and left.

She goes looking for them.

She finds the protagonist in astrometrics with the removed S-drive component.

She is competent enough to recognize it immediately.

There is no innocent reason for the protagonist to have this component in astrometrics.

She connects the facts:

- the earlier H-drive sabotage;
- unexplained system problems;
- her father's investigation of a traitor;
- protagonist behaving strangely;
- critical S-drive component removed and in their possession.

She realizes:

> **The protagonist is the saboteur.**

Possible key line:

> "It was you."

---

# 26. Her Death

The protagonist cannot let her leave because she will immediately tell her father.

The protagonist does not deliberately decide to murder her.

Instead:

- tries to restrain her;
- tries to stop her leaving;
- possibly draws a weapon to force her to stop;
- she struggles / reaches for the weapon;
- the gun fires;
- she is killed.

The protagonist probably could not intentionally execute her.

However, the story should not absolve them with "it was just an accident."

They:

- created the situation;
- were carrying out sabotage;
- prevented her from leaving;
- introduced the weapon / force;
- caused the confrontation.

They are responsible.

Her pregnancy is revealed much later through:

- medical record;
- private diary;
- unsent message;
- or another understated source.

The player then realizes that the "surprise" in the quarters video was the pregnancy.

A minimal protagonist thought may be:

> *The surprise.*

---

# 27. The Captain's Moral Crisis

The captain is a career military officer, not a bleeding-heart ideologue like his daughter.

When the real extermination order unlocks, he is horrified.

His dilemma is:

- refuse a lawful order -> treason;
- obey an unlawful order -> war crime.

He is increasingly convinced the extermination order is morally repugnant and probably illegal.

He is also not certain that his personal judgment overrides Command.

He has nearly decided to refuse.

Representative private log:

> "To hell with Command.
>
> I'm not a baby killer.
>
> Even if this saves a hundred lives on our side. A thousand. A million. And I doubt it saves anything close to that.
>
> I cannot justify genocide to end a war we cannot ultimately lose.
>
> Billions of people. Hundreds of millions of children. Not combatants. Not infiltrators. Not soldiers. Children.
>
> Command can relieve me for insubordination. They can try me for treason. Hell, maybe I get to be the first person executed in a century.
>
> To hell with it.
>
> I'm not doing this.
>
> I'll execute the mission everyone aboard thinks we came here to execute. We'll demonstrate overwhelming force. We'll deliver the aid package. We'll make speeches about peace and cooperation and send everyone home feeling very pleased with themselves.
>
> Platitudes and goodwill without enough action to change anything.
>
> But I will not kill an entire world.
>
> Not because Command thinks they may remain a threat.
>
> Not because refusing is dangerous.
>
> Not under any circumstances."

Important: he reaches this position **before his daughter is killed**, but the protagonist does not know it.

---

# 28. How Her Death Changes the Captain

The captain later learns:

- his daughter was killed;
- the killer was the protagonist;
- the protagonist was an enemy infiltrator;
- the protagonist had been his closest friend / trusted confidant;
- the protagonist was romantically involved with his daughter;
- she was pregnant with the protagonist's child.

From his perspective, this proves Command's darkest argument:

> the enemy's desperation erases every boundary;
> they will infiltrate anything;
> betray anyone;
> sacrifice anyone;
> even kill the mother of their own unborn child if necessary to save their world.

The captain's previous moral hesitation collapses.

He concludes the enemy truly will never stop because they cannot stop — extinction makes any sacrifice rational.

A possible emotional logic:

> *I kept telling myself desperation did not make them monsters.*
>
> *He loved her.*
>
> *She was carrying his child.*
>
> *And when she stood between him and his objective, he killed her.*
>
> *What exactly am I waiting for them to become?*

He becomes resolved to execute the extermination order.

This is the central causal irony:

> **The protagonist may have convinced the captain to commit the genocide they were trying to prevent.**

The counterfactual should remain unknowable. The game should not definitively prove the world would have survived if the protagonist had done nothing.

But the possibility is real.

---

# 29. Captain / Protagonist Final Confrontation

Despite everything, the captain cannot bring himself to kill the protagonist.

He knocks the protagonist unconscious and has them locked in stasis.

This is psychologically complicated:

- the protagonist was his closest friend;
- the protagonist betrayed him;
- the protagonist caused his daughter's death;
- the protagonist was the father of his unborn grandchild;
- the protagonist is now his last living connection to his daughter.

In a twisted way, the captain is a father figure and the protagonist is the last remnant of his family.

The reason the game begins with the protagonist in stasis is ultimately:

> **the captain put them there.**

The captain may have intended them to:

- stand trial later;
- remain contained;
- be recovered by authorities;
- or simply survive because he could not kill them.

He does not know that this choice will preserve them for more than a century.

---

# 30. Crew Escape and Destruction of the Protagonist's World

For much of the game, the player may believe the sabotage killed everyone aboard.

This creates guilt:

> "I killed these people."

Very late, the player discovers that the crew **did use the escape pods / escape systems and survived the ship disaster**.

For a moment this seems like relief.

Then the player learns the worse truth:

The surviving crew were still able to complete / authorize / enable the extermination mission.

The protagonist's home world was devastated completely:

- biosphere destroyed;
- all life effectively eliminated;
- planet rendered uninhabitable.

The protagonist's mission failed.

The precise mechanism by which the escaped crew ensured this can remain to be finalized, but it must be coherent with the larger extermination plan.

The emotional result is more important:

> The protagonist betrayed friends, killed the person they loved, destroyed the ship, and still failed to save anyone.

Potential deeper realization:

> **They may have helped cause the genocide by changing the captain's mind.**

---

# 31. Hidden Timeline: More Than 100 Years Adrift

The ship has been drifting for more than a century.

The protagonist survived only because of a fluke involving:

- stasis;
- intermittent power;
- SAINT-5 maintenance;
- repeated faults / emergency wake cycles;
- extraordinary luck.

The game should not explain the timeline early.

Clues can include:

- extreme corrosion / aging;
- faded physical materials;
- clocks that disagree;
- isolated systems with different uptime histories;
- batteries / components that have obviously cycled repeatedly;
- parts replaced multiple times by SAINT-5;
- rooms that look dramatically older than the player's memories.

The player sees the ship in memories / videos as:

- new;
- clean;
- unrusted;
- pristine;
- comfortable;
- alive.

The present ship is:

- dark;
- corroded;
- scarred;
- deteriorated;
- fragmented.

The narrative does not comment on the contrast. It simply exists until the timeline reveal makes it obvious.

---

# 32. Endgame Destination

Once enough navigation and external systems are restored, the player finally learns:

- more than 100 years have passed;
- their home world is dead;
- everyone they knew there is dead;
- there is only one reachable habitable world.

That world is the former enemy civilization — the origin world of the captain and crew.

The ship's original interstellar performance with S + H would have allowed roughly a **5-year** trip.

The H-drive remains irreparably / effectively destroyed.

If the player restores the S-drive, the ship can still travel using folded space plus conventional propulsion.

Estimated trip:

> **~30 years.**

There is no viable alternative.

The ship may not survive.

The player cannot remain awake because:

- life support is too degraded;
- oxygen / supplies are insufficient;
- the journey is too long.

The only plausible survival choice is to return to stasis.

The pod itself is degraded and unreliable.

So the endgame choice is effectively:

- enter stasis and take a poor chance at reaching the enemy world alive;
- or remain awake and certainly die before arrival.

There need not be a labeled "LIVE / DIE" decision.

If the player enters the pod, the game proceeds to the canonical ending image.

If they refuse, oxygen / time eventually kills them.

---

# 33. Final Image

The player returns to the same stasis room where the game began.

The ship is now repaired enough to depart, but still badly compromised.

The player closes themselves into the pod.

The ship begins the long journey.

Then:

- metallic footsteps;
- SAINT-5 enters the crew / stasis area;
- it approaches the pod;
- it looks over the player;
- an arm / tool unfolds.

Cut to black.

Meaning is deliberately unresolved.

SAINT-5 might be:

- repairing the pod;
- checking a fault;
- following containment protocol;
- disconnecting the pod;
- preparing to kill the protagonist;
- doing something completely routine that merely looks threatening.

The ambiguity works because throughout the game SAINT-5 has genuinely done both life-preserving and lethal things.

---

# 34. Thematic Core

The game is not about proving one civilization morally superior.

Important thematic tensions:

## Need vs. entitlement

The alien civilization genuinely needs massive help or faces extinction.

But parts of that civilization are also:

- wasteful;
- unequal;
- militarized;
- politically extreme;
- unwilling to fully sacrifice their own elites' comfort.

## Sacrifice vs. self-preservation

The origin civilization could probably save them, but only at extraordinary social and economic cost.

The question becomes:

> How much does one civilization owe another when survival for one means severe sacrifice for the other?

## Real threats vs. paranoia

Enemy infiltration is real.

The protagonist is proof.

But the origin civilization still becomes increasingly repressive, exclusionary, and unjust.

## Loyalty vs. morality

The captain is a professional officer confronting an order he believes may be illegal.

The protagonist is an infiltrator who hates aspects of their own government but cannot allow their people to be exterminated.

The daughter loves her society and father while morally opposing their treatment of the aliens.

## Contingency / history

Many outcomes depend on small events:

- the captain introducing the protagonist to his daughter;
- the daughter choosing to surprise the protagonist;
- the protagonist leaving their quarters early;
- the gun going off;
- the captain changing his mind after her death;
- the crew escaping;
- the protagonist surviving stasis for a century.

No one is fully in control of history.

---

# 35. Important Causal Symmetry

Two emotionally central retrospective conclusions:

## Captain

> **"I killed my daughter by introducing you to her."**

## Protagonist

> **"I killed my world by killing her."**

Neither statement is objectively complete, but both are emotionally and causally plausible.

This symmetry should remain implicit rather than being spelled out in one giant explanatory scene.

---

# 36. Easter Eggs / References

The game can contain subtle references while maintaining a serious tone.

Rules:

- no winking at the player;
- references should work as ordinary world detail if not recognized;
- prefer model numbers, UI messages, system names, filenames, manufacturer names, physical design cues;
- older references can go over younger players' heads without affecting the scene.

Examples already discussed:

## BSOD

Advanced ship computers can still fail with an ugly blue-screen-style system fault.

This is funny only by implication.

## SAINT-5

The maintenance robot is an enormous Johnny-5-like industrial machine marked **SAINT-5**.

The reference should not turn the robot comedic.

## Other possible buried references

Potential options:

- `0xDEADBEEF` in diagnostics;
- HTTP-ish `418` status somewhere obscure;
- old compatibility subsystem names;
- `C:\>` appearing in an ancient system layer;
- subtle `9000` references;
- obscure classic-SF / old-computer manufacturer or subsystem names.

Use sparingly.

---

# 37. Implementation / Narrative Design Rules

## Do

- Let the player discover rather than be told.
- Let mechanics carry narrative information.
- Use rooms and system behavior as evidence.
- Make badges useful mechanically and narratively.
- Make memories visual and sensory, not explanatory monologues.
- Keep logs personal, biased, and incomplete.
- Preserve multiple plausible interpretations until late.
- Keep SAINT-5 mechanically useful as well as threatening.
- Make power / environment / sensors genuinely systemic.
- Let old memories show the ship pristine without explaining the contrast.
- Let the player infer family relationships from images.
- Let the player naturally choose destinations from information rather than quest markers.
- Keep technobabble only where it serves gameplay or story.

## Do not

- Add explicit quest lists like "Repair Astrometrics."
- Add dialogue trees for ordinary interactions.
- Explain every memory.
- Make the protagonist constantly ask obvious questions aloud.
- Turn the crew into villains to justify the protagonist.
- Turn the aliens into innocent saints.
- Make the daughter omniscient or secretly aware of the real mission.
- Make the captain knowingly carry genocide orders from the start.
- Make SAINT-5 simply hunt the player like a conventional monster.
- Give the player a conventional weapon and boss fight against SAINT-5.
- Over-explain S/H physics.
- Resolve the final SAINT-5 / stasis ambiguity.

---

# 38. Current Reveal Order — High-Level

A rough intended reveal sequence:

1. Wake in smoke-filled stasis room.
2. Escape using fallen structural piece.
3. Emergency lights / first procedural-memory thoughts.
4. Secondary generator.
5. Discover environmental collapse.
6. Restore limited environment to selected areas.
7. Restore main power.
8. SAINT-5 activates and begins repairing ship.
9. SAINT-5 attacks player on encounter.
10. Player reaches own quarters.
11. Pristine-memory room / lover's video / "surprise" / astrometrics.
12. Return to ruined present.
13. Find own badge and wearable console.
14. Gain useful access, unknowingly provoking more security behavior.
15. Explore / repair ship with no explicit quest list.
16. Reach astrometrics.
17. Find lover's badge.
18. Flash: her bloody body / "No!"
19. Her badge opens command and captain's quarters.
20. Captain's screensaver reveals she is his daughter and protagonist was close to both.
21. More crew logs / personal rooms / political disagreement.
22. Captain's old memoir about why space war makes no sense.
23. Historical archive showing discovery of the other civilization.
24. Evidence that enemy infiltrators really existed.
25. Evidence that protagonist's badge / identity is specifically targeted.
26. Another crewmember's badge works without provoking security -> security is not simply broken.
27. Captain's logs reveal a suspected traitor and compromised systems, creating reasonable doubt about protagonist's guilt.
28. Political / humanitarian logs reveal the alien ecological crisis and aid dispute.
29. Daughter's diaries reveal her compassionate politics and opposition to refusing aid.
30. Hard-line crew logs reveal hatred / collective blame / desire for extermination.
31. Real mission briefing becomes accessible using captain's badge / security knowledge.
32. Reveal: public mission was false; actual mission is planetary extermination.
33. Reveal: captain received these orders only near arrival and was close to refusing.
34. Reveal: protagonist was actually an infiltrator from the target civilization.
35. Reveal: protagonist sabotaged H-drive earlier.
36. Reveal: protagonist removed critical S-drive component after learning the contingency.
37. Full astrometrics memory: daughter catches protagonist with S-drive component.
38. Reveal: she was coming to say she was pregnant.
39. Confrontation memory: accidental gunshot / her death.
40. Captain's reaction: her death convinces him the extermination is necessary.
41. Reveal: captain knocks protagonist out and puts them in stasis rather than killing them.
42. Player believes sabotage killed most/all crew.
43. Very late reveal: crew escaped.
44. Very late reveal: extermination succeeded anyway; protagonist's world is dead.
45. Reveal: more than 100 years have passed.
46. Only reachable habitable world is former enemy civilization.
47. Restore S-drive / missing component; H remains unusable.
48. Final travel estimate ~30 years.
49. Player must re-enter stasis or die before arrival.
50. SAINT-5 approaches pod.
51. Cut to black.

---

# 39. Open / Not Yet Fully Decided

These items remain available for design work:

- exact name / terminology of the two civilizations / species;
- exact biological reason for extreme compatibility between the species;
- exact mechanics of how the surviving crew ultimately completed / authorized the extermination after abandoning the ship;
- exact form of the primary atmospheric chain-reaction weapon;
- exact name and form of the critical removable S-drive component;
- exact reason astrometrics is needed for the final S-drive sabotage step;
- exact dates / travel durations / century drift duration;
- exact number and timing of hidden stasis-rescue cycles;
- exact crew roster and which rooms / logs belong to which people;
- exact security hierarchy / badge access levels;
- exact cause and boundaries of irradiated armory section;
- exact implementation of hard-mode death / persistence;
- exact amount of player freedom to ignore astrometrics initially;
- whether the protagonist's world / species has a single name used publicly or multiple political identities;
- how explicit the captain's final pro-extermination shift should be in logs versus reconstruction from evidence.

---

# 40. One-Sentence Story Summary

**A technically skilled amnesiac wakes aboard a century-old derelict, slowly discovers they were an infiltrator who sabotaged the ship to save their dying world, accidentally killed the woman they loved while doing so, may have convinced her father to carry out the genocide they were trying to prevent, and must finally repair the same ship well enough to spend thirty years in stasis traveling to the civilization they once betrayed because it is the only habitable world left.**
