# Testing Requirements

## Running Tests

- Command: `just test`
- Test files in `wies/core/tests/`

## Test Patterns

- Use Django's TestCase base class
- Use `override_settings` for configuration tests
- Create test data inline, don't rely on fixtures
- All imports at top of file (not inside methods)

## Assertion Style (pytest)

Use pytest-style assertions, not unittest-style:

```python
# Wrong (unittest-style)
self.assertEqual(a, b)
self.assertIn(x, list)
with self.assertRaises(ValidationError):

# Right (pytest-style)
assert a == b
assert x in list
with pytest.raises(ValidationError):
```

## Coverage

- Test views with authenticated users (use `self.client.force_login()`)
- Test permission checks for each role (Beheerder, Consultant, BDM)
- Test form validation

## Before Completing Work

Always run tests to verify changes don't break existing functionality.
