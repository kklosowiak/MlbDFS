---
name: Roster_Hardening
description: Enforces strict DraftKings Classic roster positions, batting order floors, and stacking isolation rules for MLB DFS.
---

# Roster_Hardening Skill

This skill contains the "Ground Truth" constraints for building high-leverage, compliant DraftKings MLB Classic lineups. Use this skill to verify optimization integrity and roster legality.

## 1. Roster Configuration (DK Classic)
All lineups must strictly follow the official 10-player structure:
- **P** (Pitcher) x2
- **C** (Catcher) x1
- **1B** (First Base) x1
- **2B** (Second Base) x1
- **3B** (Third Base) x1
- **SS** (Shortstop) x1
- **OF** (Outfield) x3

> [!IMPORTANT]
> **No Flexible Slots**: Remove any logic for `ULT`, `UTIL`, or `INF` when this skill is active. Positions must be exact matches to the DK field.

## 2. PA Floor (Batting Order Filter)
To ensure maximum plate appearance volume, every hitter in the roster (including one-offs) must satisfy the following:
- **Constraint**: `hitter.slot <= 6`
- **Logic**: Only hitters projected in the Top 6 slots of their official starting lineup are eligible for selection.

## 3. Stacking Isolation (The Secondary Fork)
When building 'Clean Stacks', the engine must support two distinct paths and select the one with the highest Prop Alpha weighted projection:

### Path A: The 5-3 Stack
- **Primary**: 5-man stack from Team A.
- **Secondary**: 3-man stack from Team B (must be from a different game than Team A).

### Path B: The 5-1-1-1 Stack
- **Primary**: 5-man stack from Team A.
- **One-Offs**: 3 individual hitters from 3 DIFFERENT games (none can be from the Team A game).

> [!IMPORTANT]
> **Game Independence Mandate**: One-off hitters must be selected from games strictly independent of the primary stack.
> - **Rule**: If a team is used for a 5-man stack, no players from the opposing team of that game can be selected as one-offs.
> - **Path B Logic**: In a 5-1-1-1 structure, exactly 4 unique games must be represented in the hitting roster.
