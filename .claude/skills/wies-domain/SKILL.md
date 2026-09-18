---
name: wies-domain
description: Wies project domain knowledge including Dutch government terminology, roles, and business logic. Use when working with placements, assignments, colleagues, or understanding project context.
---

# Wies Domain Knowledge

## Core Concepts (Dutch terms)

- **Plaatsing** - Placement of a colleague on a service
- **Opdracht** - Assignment/project for a ministry
- **Dienst** - Service/work needed for an assignment
- **Collega** - Colleague (person with skills)
- **Ministerie** - Government ministry

## User Roles

- **Gebruikersbeheer** - User administration (users/labels); granted only by platform administration
- **Opdrachtbeheer** - May edit/delete any assignment and see all history; granted only by platform administration
- Platform administration (`STAFF_EMAILS`) is not a role; see `features/roles.md`
- **Consultant** - View-only access
- **BDM** - Business Development Manager (creates assignments)

## Date Inheritance

Placements and Services can inherit dates from their parent Assignment:

- If `start_date` is None, use Assignment's date
- Properties handle this: `effective_start_date`

## Key Business Rules

- Assignments have status: draft, active, completed
- Placements track colleague availability
- Labels categorize by Merk, Expertise, Thema
