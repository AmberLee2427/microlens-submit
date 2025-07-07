# Refactoring Plan: Package Structure

## Roadmap

### Phase 1: Create New Package Structure

1. Create models package - Move Solution, Event, Submission classes
2. Create dossier package - Move HTML generation functions
3. Create cli package - Move CLI commands
4. Create utils module - Move shared utilities (CSV import, etc.)

### Phase 2: Update Imports and Dependencies
1. Update internal imports - Fix all import statements
2. Update _init_.py - Maintain backward compatibility
3. Update tests - Fix test imports

### Phase 3: Cleanup and Validation
1. Remove old files - Delete the original large files
2. Run full test suite - Ensure everything works
3. Update documentation - Fix any broken doc references

## New Package Structure

microlens_submit/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── solution.py      # Solution class
│   ├── event.py         # Event class  
│   └── submission.py    # Submission class
├── cli/
│   ├── __init__.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py      # init command
│   │   ├── add_solution.py
│   │   ├── validate.py
│   │   ├── dossier.py
│   │   └── export.py
│   └── main.py          # Main CLI entry point
├── dossier/
│   ├── __init__.py
│   ├── dashboard.py     # Dashboard generation
│   ├── event_page.py    # Event page generation
│   ├── solution_page.py # Solution page generation
│   └── utils.py         # Shared HTML utilities
├── validation.py        # Parameter validation (already separate)
└── utils.py            # Shared utilities (CSV import, etc.)

## Step-by-Step Implimentation Plan

1. Create the new package structure
  * `microlens_submit/models/` (done, Solution moved)
  * `microlens_submit/dossier/`
  * `microlens_submit/cli/`
  * `microlens_submit/utils.py` (for shared helpers)

2. Move classes and functions
  * Move `Event` and `Submission` to `models/event.py` and `models/submission.py`
  * Move dossier generation functions to `dossier/`
  * Move CLI commands to `cli/`
  * Move CSV import and other helpers to `utils.py`

3. Update imports
  * Update all internal imports to use the new structure
  * Update `__init__.py` files for backward compatibility

4. Update tests and docs
  * Update test imports and any direct references in documentation

5. Remove old monolithic files
  * Once all code is moved and imports are fixed, delete the old large files

6. Test
  * Run the full test suite after each major move

7. Git
  * status. add. commit