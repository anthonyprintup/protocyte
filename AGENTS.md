# Repository Instructions

- After completing any task that edits C++ files, run `clang-format` on the touched C++ files before final verification.
- Treat `.cpp`, `.hpp`, `.cc`, `.hh`, `.cxx`, and `.hxx` files as C++ files for this rule.
- Do not manually edit generated smoke test outputs under `smoke/generated/`, including
  `smoke/generated/protocyte/runtime/runtime.hpp`; regenerate them from the source generator/runtime changes instead.
- When generating commits or committing code, follow the Conventional Commits 1.0.0 specification: https://www.conventionalcommits.org/en/v1.0.0/
