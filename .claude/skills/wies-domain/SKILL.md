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

- **Office assistent** - User administration (users, labels, merken, contract hours); may grant every role, including its own
- **Consultant** - View-only, plus the text fields of an opdracht they are placed on
- **BDM** - Business Development Manager; every wies-sourced opdracht, and contract hours
- Application administration (`STAFF_EMAILS`) is not a role; see `features/roles.md`

## Date Inheritance

Placements and Services can inherit dates from their parent Assignment:

- If `start_date` is None, use Assignment's date
- Properties handle this: `effective_start_date`

## Key Business Rules

- Assignments have status: draft, active, completed
- Placements track colleague availability
- Labels categorize by Merk, Expertise, Thema
