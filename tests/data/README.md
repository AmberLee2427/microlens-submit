# Test Data Files

This directory contains test data files used by the test suite.

## test_import.csv

A comprehensive test CSV file for testing the CSV import functionality. This file contains various test cases:

### Valid Solutions (4 rows)
- **simple_1S1L**: Basic 1S1L point lens solution with t0, u0, tE parameters
- **binary_parallax**: 1S2L binary lens with parallax effects, including piEN and piEE parameters
- **finite_source**: 1S1L with finite source effects, including rho parameter
- **duplicate_test**: Another 1S1L solution (used for testing duplicate handling)

### Invalid Solutions (2 rows)
- **missing_params**: 1S2L solution missing required parameters (s, q, alpha)
- **invalid_json**: 1S1L solution with invalid JSON in parameters field

### Test Coverage
This file tests:
- Different model types (1S1L, 1S2L)
- Higher-order effects (parallax, finite-source)
- Parameter parsing (individual columns and JSON fallback)
- Error handling (missing required parameters, invalid JSON)
- Duplicate handling scenarios
- Notes handling (both file paths and content)

### Usage
The file is used by both CLI and API tests to verify the CSV import functionality works correctly with real data. 