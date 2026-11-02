# GONE design decisions

> **Status:** This English ledger records why the Spanish story bible at `docs/design/biblia.md` says what it says after the November 2026 intake. The bible holds the story. This ledger records accepted rulings, open decisions and facts the story deliberately leaves unknown.

## 1. Rulings from the November 2026 intake

1. **Her death.** She dies accidentally while he tries to restrain her. He remains responsible because he blocks her departure and uses force. Exact gun handling remains open. Sources: [`gone_story_summary.md`](sources/gone_story_summary.md) §26; [`Gone_Naleya_Story_Synopsis.pdf`](sources/Gone_Naleya_Story_Synopsis.pdf), passage 14. Affected: `docs/design/biblia.md`, `docs/design/story-reference.md`.
2. **Earth's fate.** Records establish devastation and a home he cannot return to. They do not prove every person died, and the docs must not reveal survivors. Sources: synopsis passages 19–20; story summary §§31–32. Affected: `docs/design/biblia.md`, `docs/design/story-reference.md`.
3. **Transit estimates.** S-drive plus H-drive takes about five years; S-drive plus conventional propulsion takes about thirty Earth years. Without S-drive, the interstellar trip is not survivable. Exact distances and dates remain open. Sources: story summary §23; language reference, numbers and time sections; synopsis passage 20. Affected: `docs/design/biblia.md`, `docs/design/story-reference.md`, `docs/design/ship-systems-and-security.md`, `docs/design/language/nalesha-reference.md`.
4. **Sabotage has two stages.** Earlier, he sabotages H-drive to delay the ship as part of his original mission. Near the target, after sealed orders unlock, he removes a critical S-drive component and takes it to astrometrics. Why that room is needed remains open. Sources: story summary §24; synopsis passages 10 and 12. Affected: bible, story reference and puzzle progression.
5. **Captain's decision.** Before her death, the captain judges the order wrong and resolves to refuse it. Whether he formally transmitted a refusal remains open. After her death, he believes Command was right and carries out the order. Unable to kill his daughter's mate, he knocks him out and has him placed in stasis. The counterfactual remains unknowable. Sources: story summary §§27–29; synopsis passages 7 and 15–16. Affected: bible and story reference.
6. **Genocide execution.** The captain bears responsibility, but the mechanism, contingency used and timing relative to evacuation are unsettled. Sources: story summary §§22, 29–30; synopsis passage 15. Affected: bible, story reference and ship systems/security.
7. **Crew knowledge.** Until sealed orders unlock near the target, the crew, including the captain, believes the public mission. The daughter never learns the real orders. Hard-line logs express opinions and do not prove the writer knew the sealed plan. Sources: story summary §§22, 27. Affected: bible and story reference.
8. **Progression order.** Bible chapter order remains emotional and reveal order, not a movement lock. Lore pickups do not gate movement. The early-cabin route in the puzzle handoff is a proposal. Sources: puzzle progression handoff §§1–3, 11–13; story summary §38. Affected: bible, story reference and puzzle progression.
9. **Badges.** Selecting the carried credential is player equipment state; presenting it at a reader is contextual and automatic. SAINT-5 recognizes bodies, not cards. Sources: puzzle handoff §§6, 13; story summary §§10–11. Affected: bible, ship systems/security and puzzle progression.
10. **Bot name and tone.** The maintenance bot is SAINT-5. The Johnny-5 reference stays understated and the bot is not comic. Sources: story summary §§6, 36–37. Affected: bible, story reference and ship systems/security.
11. **Bot at awakening.** The synopsis phrase that a maintenance robot is still working compresses its century-long history. SAINT-5 visibly reactivates when main power returns. Sources: story summary §§6, 31; puzzle handoff §8. Affected: bible, story reference and ship systems/security.
12. **Emergency lights.** Switch-powered emergency red is steady. Blinking belongs to the automatic fire circuit. Sources: `app/hallway.gd` lines 53–67; `ship-systems-and-security.md`, power and lighting. Affected: bible and ship systems/security.
13. **Language labels.** Nalesha is the reference's working language name; Naleya is the synopsis project name using the same v0.13 grammar and script. They are not two languages. Final public naming remains open. Sources: [language reference](sources/Gone_Naleya_Language_Reference.pdf), opening/version statement; [story synopsis](sources/Gone_Naleya_Story_Synopsis.pdf), opening. Affected: bible, story reference and language references.
14. **Synopsis vocabulary.** The eleven roots in the synopsis are an addendum to v0.13, not content already present in the language reference. Sources: story synopsis, vocabulary addendum. Affected: bible and language references.
15. **Negation erratum.** In language reference line 539, “nu no kuta” should be “nu cha kuta,” following the defined prohibition pattern. Sources: language reference, grammar and example. Affected: language references.
16. **Retro references.** `0xDEADBEEF`, `C:\\>`, `9000`, `418` and `14F4:9000` remain author-facing placeholders until each rendering is decided for native base-eight notation or perceived Spanish. Sources: story summary §36; language reference, number rules. Affected: bible and language references.
17. **Power-room geography.** Leaving the stasis room along +X, the hall light switch is beside the stasis hatch at about x=6.2, z=+0.85, to the right of that doorway. The power-room door is the last door on the left, at x=27 on the -Z wall, before the x=30 end wall. Sources: puzzle handoff §1 and baseline; `app/hallway.gd` lines 53–67. Affected: puzzle progression and ship systems/security.
18. **Society ranks and daughter's post.** H §11 proposals and pending decisions are not established. The seven suggested English rank names remain rejected. The daughter has no assigned service post. Sources: [society handoff](sources/Gone_Society_History_and_Ranks_Agent_Handoff.md) §11. Affected: bible, society history/command and language reference.
19. **Character names.** Names in language examples are examples, not cast assignments. Sources: language reference, names section; society handoff §11. Affected: bible, story reference and language references.
20. **Ship description.** The ship is the crew civilization's interstellar ship on a sealed extermination mission under a public aid/peace cover. The old “colonial warship” label and dog threat are retired. Sources: story summary §§22, 36–37; concept history; puzzle handoff. Affected: bible, story reference and ship systems/security.
21. **Destination.** The crew's homeworld, Our Planet, is habitable and is the only habitable world he can reach. His survival, arrival and whether its people protect him remain unconfirmed. Sources: [story synopsis](sources/Gone_Naleya_Story_Synopsis.pdf), passage 20; story summary §§31–32. Affected: bible and story reference.
22. **Resolved decisions.** The accidental-death account and the approximate five-year S+H and thirty-Earth-year S+conventional transit estimates are accepted. Open questions are limited to the gun choreography, exact distances and dates, and whether the S-drive component is mandatory or can be substituted at a cost. Sources: story summary §§23, 26; story synopsis passages 14 and 20. Affected: bible and story reference.
23. **Style scope.** Style restrictions apply to prose added or rewritten in this documentation change; untouched passages are outside this pass. Sources: story summary §37 and the maintained writing rules for this change.

## 2. Open decisions

### Story and characters
- Exact choreography of her accidental death, including who draws the gun and how it fires. The accidental-death account itself is settled. Source: story summary §26.
- Whether the captain formally transmitted a refusal before reversing. Source: story summary §27; synopsis passage 7.
- Exact medium for the pregnancy reveal. Source: story summary §25.
- Protagonist's name, cover biography, formal onboard role and detailed recruitment route; daughter's name and exact service post. Sources: story summary §§4–5, 20; society handoff §11.
- Exact crew roster, owners of rooms/logs, and extent to which the captain's final shift appears in logs. Source: story summary §39.
- Whether Earth would have been spared without sabotage is deliberately unknowable. Sources: story summary §§28, 38.

### Mission, weapons and transit
- Exact mechanism, contingency and timing used to execute the genocide relative to evacuation. Sources: synopsis passage 15; story summary §§29–30.
- Exact primary atmospheric chain-reaction weapon and which contingency succeeded. Source: story summary §39.
- Exact names and political identities of the two civilizations, plus biological reason for their compatibility. Source: story summary §39.
- Exact distances and dates for the voyage. Approximate five-year S+H and thirty-Earth-year S+conventional estimates are accepted. Source: story summary §23.

### Stasis and time
- Neurological cause of amnesia, stasis energy budget, engineering lifetime, drift position/velocity, lack of rescue and local-to-Earth calendar conversion. Sources: story summary §§18, 31–32; language reference, numbers and time sections.
- Exact number and timing of hidden stasis-rescue cycles and hard-mode death/persistence implementation. Sources: story summary §39; puzzle handoff §13.

### Systems, security and the bot
- Exact S-drive component name/form, why astrometrics is needed, and whether the component is mandatory or can be replaced at a cost. Sources: story summary §§24, 39; puzzle handoff §13, decision I.
- Bot rules for attacking, returning an unconscious protagonist to stasis, choosing urgent repairs, and avoiding endless diversion. Source: puzzle handoff §13, decision G.
- Exact security hierarchy, badge levels, first hostile device and fair escape; alternate crew-badge location and timing. Sources: story summary §39; puzzle handoff §13, decisions E–F.
- Cause and boundaries of the irradiated armory. Source: story summary §39.
- Captain's execution logistics and the post-escape action of the surviving crew. Sources: story summary §§29–30, 39.

### Progression and geography
- Puzzle handoff questions: room mapping; whether secondary power gates the first hub; power tradeoff behavior; recognition of the protagonist's quarters; first device to reveal badge danger and a fair escape; alternate badge location; bot rules; exact death choreography; exact distances and dates; and S-drive component substitution. Sources: puzzle handoff §§2, 9, 13; story summary §§23, 26.
- Player freedom to ignore astrometrics initially and distinction between physical routes and lore gates. Sources: story summary §39; puzzle handoff §§3, 13.
- Exact room assignments and loop geometry beyond the verified opening baseline. Source: puzzle handoff §§2, 13.
- How the first hub power tradeoff feels in play and whether it has a recovery route. Source: puzzle handoff §13, decision C.

### Society and command
- Reformer and historical figures' names, dates, population totals, massacre mechanism, death toll and duration, and exact geological timescale. Sources: society handoff §§1–10.
- Parenthood, adoption, infertility, inheritance, household departure, exclusivity, communications engineering, and precise democratization sequence. Sources: society handoff §§4–5, 10.
- Dual appointment equality, offices, disagreement, succession, modern service qualifications, career grades and the daughter's actual position. Source: society handoff §11.
- Rejected grade suggestions Learner, Member, Proven Member, Guide, Keeper, Senior Keeper and High Keeper remain unadopted. Source: society handoff §11.

### Language and presentation
- Whether the public language name settles on Nalesha, Naleya or another name. Sources: language reference opening; synopsis opening.
- Cause of perceived Spanish, exact local second/year lengths, old network sound changes and rendering of each retro reference. Sources: language reference §§1, 3, 14; story summary §39.
- Integrate the eleven synopsis roots into a future language release and decide its version. Source: story synopsis vocabulary addendum.
- Verify native glyph shapes and typesetting from the original PDFs or assets. Sources: archived language reference and synopsis PDFs.

## 3. Deliberately unanswered

- **Universal death on Earth:** records show devastation but do not establish that every human died. Do not reveal confirmed survivors either. Sources: synopsis passages 19–20.
- **Survival of transit:** whether the protagonist survives the thirty-Earth-year voyage is unconfirmed. Source: synopsis passage 20.
- **Arrival:** whether the ship reaches Our Planet is unconfirmed. Source: synopsis passage 20.
- **Protection:** whether Our Planet protects or accepts him is unconfirmed. Source: synopsis passage 20.
- **SAINT-5's last act:** the final image shows the bot approach the closed pod and unfold a tool. Its intent and action remain unresolved. Source: story summary §33.
- **Counterfactual:** whether Earth would have been spared if the protagonist had not sabotaged the ship is unknowable. Sources: story summary §§28, 38.

## 4. Known code follow-ups outside the docs

The two comments below describe the power-room door as being on the right, but geometry and tests place it on the left when walking out of stasis along +X. The door is on the -Z wall at x=27; the hall switch is on the right at z=+0.85. The puzzle handoff baseline and `app/hallway.gd` lines 53–67 support the coordinates and geometry. This is a separate code follow-up, not part of the documentation change.

- `app/game.gd`, lines 20–21: comments describe the power room as behind the corridor's last right-hand door.
- `app/power_room.gd`, line 3: comment likewise calls it the last right-hand door.

Sources: puzzle handoff §1 and baseline. No code files are changed here.
