# AGENTS.md – Cinema Monitor

## Scope

* This file provides instructions for AI coding agents working on this Python project.
* Prioritise clarity, testability, and long‑term maintainability over micro‑optimisation.

---

## Languages & Tech

* Primary language: **Python** (3.10+ unless otherwise stated).
* Avoid introducing additional languages, frameworks, or services unless:

  * they are clearly necessary, and
  * their use is documented in the main README and referenced here.

---

## Architecture & Separation of Concerns

Always favour clear, composable structure over monolithic scripts.

At minimum, keep the following concerns **separate**:

* **HTTP / networking**

  * Request/response handling
  * Session/retry logic
* **Parsing layer**

  * HTML / SVG / JSON / other input formats
  * Input validation and normalisation
* **Internal domain representation**

  * e.g., seat map representation, data models, value objects
  * Operations that transform raw parsed data into domain objects
* **Core decision / optimisation logic**

  * e.g., optimal seat selection logic, scoring functions, ranking & filtering

Prefer small, focused modules and functions over large, multi‑responsibility objects.

---

## Style & Implementation Rules

* Use **Python only (or mainly)** for implementation.
* **Follow established Python and SWE best practices throughout**—including type hinting, consistent formatting, clean design patterns, and strong separation of concerns.
* Prefer **small, testable units** over monolithic scripts.
* Write code that is easy to test in isolation (minimal hidden I/O and global state).
* Avoid clever one-liners when they hurt clarity — explicit is better than implicit.

### Configuration & Magic Values

* Do **not** hard-code magic values where avoidable.
* Centralise configurable parameters, for example:

  * optimal row/column index ranges
  * scoring weights
  * thresholds / limits
* Place these in a dedicated configuration module, dataclass, or settings file.

### Performance vs Clarity

* Avoid premature micro‑optimisation.
* Favour clarity, correctness, and debuggability over squeezing out every millisecond.
* Optimise only when a **measured bottleneck** is identified.

---

## Reasoning & Explanations

When adding non‑trivial code (new module, class, or complex function):

* Briefly explain your **reasoning and trade‑offs** before or alongside the implementation via:

  * a short comment or docstring, and/or
  * a concise design note in the PR/commit message.

The explanation should cover:

* what the component does,
* why it is structured this way,
* any important trade‑offs or constraints.

Keep explanations tight but meaningful; aim for **signal over verbosity**.

---

## Documentation

Maintain an updated, lightweight documentation trail:

* Keep a high‑level overview of the project (architecture, main flows) in the README or `/docs`.
* Record key decisions and alternatives considered (ADR‑style is ideal but optional).
* When a design choice changes, update the corresponding docs **in the same PR**.
* Treat documentation as **living**: every new feature, edit, or modification must be reflected immediately.
* Preserve a **didactic tone**: documentation should quietly teach—clarifying intent, reasoning, and patterns for future contributors.

In particular, ensure documentation answers:

* *Why* some choices were made.
* *How* we chose to implement them.
* Any assumptions or constraints that shaped the design.

---

## Testing

* For any non‑trivial logic, add or update tests.
* Structure code so that core logic is testable without network or I/O.
* Prefer fast, deterministic tests over slow or flaky ones.

Minimal expectations:

* Tests for the core decision/selection logic.
* Tests for parsing and domain transformations (especially edge cases).
* Regression tests for previously fixed bugs where relevant.

---

## How to Extend This File

If you (agent or human) introduce:

* new subsystems,
* non‑obvious workflows,
* or additional tools/commands,

then extend this `AGENTS.md` with:

* brief usage notes,
* expectations for behaviour,
* and any constraints the new pieces impose on the rest of the codebase.

Keep entries concise and operational. This file is a **working contract** between the project and its AI agents.
