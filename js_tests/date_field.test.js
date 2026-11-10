const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const {
  dateProblem,
  unmetWith,
} = require("../wies/core/static/js/date_field.js");

// An nldd-date-field as the guard sees it: ownValidity() is the component's
// own verdict on the typed text, closest("[hidden]") whether it is shown.
function field(own, hidden) {
  return {
    ownValidity: () => own,
    closest: (selector) => (selector === "[hidden]" && hidden ? {} : null),
  };
}

const BAD = {
  flags: { badInput: true },
  message: "Vul een datum in als dd-mm-jjjj",
};

describe("dateProblem", () => {
  it("names text that is no date in the field's own words", () => {
    assert.equal(dateProblem(field(BAD)), "Vul een datum in als dd-mm-jjjj");
  });

  it("finds nothing in an empty or valid field", () => {
    assert.equal(dateProblem(field(null)), null);
  });

  it("skips a field that is switched off", () => {
    assert.equal(dateProblem(field(BAD, true)), null);
  });

  it("finds nothing on a field without the check", () => {
    assert.equal(dateProblem({ closest: () => null }), null);
  });
});

describe("unmetWith", () => {
  it("adds its id beside the server's errors", () => {
    assert.equal(
      unmetWith("error-end_date-1", "date-field-error-1", true),
      "error-end_date-1 date-field-error-1",
    );
  });

  it("adds it once", () => {
    assert.equal(
      unmetWith("date-field-error-1", "date-field-error-1", true),
      "date-field-error-1",
    );
  });

  it("removes only its own id", () => {
    assert.equal(
      unmetWith(
        "error-end_date-1 date-field-error-1",
        "date-field-error-1",
        false,
      ),
      "error-end_date-1",
    );
    assert.equal(unmetWith(null, "date-field-error-1", false), "");
  });
});
