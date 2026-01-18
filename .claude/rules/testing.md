# Testing Requirements

## Running Tests
- Command: `just test`
- Test files in `wies/core/tests/`

## Test Patterns
- Use Django's TestCase base class
- Use `override_settings` for configuration tests
- Create test data inline, don't rely on fixtures

## Coverage
- Test views with authenticated users (use `self.client.force_login()`)
- Test permission checks for each role (Beheerder, Consultant, BDM)
- Test form validation

## Before Completing Work
Always run tests to verify changes don't break existing functionality.
