// Starting points for a new note. Each fills in a name, some tags and a body
// the user can edit freely.

export interface NoteTemplate {
  key: string;
  label: string;
  hint: string;
  title: string;
  tags: string[];
  body: string;
}

export const NOTE_TEMPLATES: NoteTemplate[] = [
  {
    key: "boss",
    label: "Boss tips",
    hint: "Phases, attacks, and what worked",
    title: "Boss: ",
    tags: ["boss"],
    body: `## Where
Location, and how to get there.

## Phase 1
- Attacks to watch for:
- How to dodge:

## Phase 2
- What changes:

## What worked
- Weapon or build:
- Strategy:

## Rewards
- [ ] Drop collected
`,
  },
  {
    key: "build",
    label: "Build",
    hint: "Stats, gear and a plan to level into",
    title: "Build: ",
    tags: ["build"],
    body: `## Idea
One line on how this build plays.

## Stats
- Level target:

## Gear
- Weapon:
- Armor:
- Talismans:

## Leveling order
1.
2.
3.
`,
  },
  {
    key: "route",
    label: "Route or walkthrough",
    hint: "Steps in order, ticked off as you go",
    title: "Route: ",
    tags: ["route"],
    body: `## Goal
What this route gets done.

## Steps
- [ ] Step one
- [ ] Step two
- [ ] Step three

## Notes
Anything to remember on the way.
`,
  },
  {
    key: "collectibles",
    label: "Collectibles",
    hint: "A checklist to work through",
    title: "Collectibles",
    tags: ["checklist"],
    body: `## Found
- [ ]
- [ ]
- [ ]

## Still missing
- [ ]
`,
  },
  {
    key: "checklist",
    label: "Checklist",
    hint: "A plain list of things to do",
    title: "To do",
    tags: ["checklist"],
    body: `- [ ] First thing
- [ ] Second thing
- [ ] Third thing
`,
  },
  {
    key: "log",
    label: "Play log",
    hint: "A dated entry for each session",
    title: "Play log",
    tags: ["log"],
    body: `## Session 1
- Where I got to:
- What I did:
- Next time:
`,
  },
];
