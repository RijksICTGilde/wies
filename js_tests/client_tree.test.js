const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { orgNodeIdToFilter } = require("../wies/core/static/js/client_tree.js");

const UUID = "11111111-2222-3333-4444-555555555555";

describe("orgNodeIdToFilter", () => {
  it("maps a plain org node to the org param (subtree filter)", () => {
    assert.deepEqual(orgNodeIdToFilter(UUID), { name: "org", value: UUID });
  });

  it("maps a self- node to org_self", () => {
    assert.deepEqual(orgNodeIdToFilter("self-" + UUID), {
      name: "org_self",
      value: UUID,
    });
  });

  it("maps a top-level type folder to org_type", () => {
    assert.deepEqual(orgNodeIdToFilter("group-Agentschap"), {
      name: "org_type",
      value: "Agentschap",
    });
  });

  it("maps a scoped nested folder to org_type_in (ministry:type)", () => {
    assert.deepEqual(orgNodeIdToFilter("group-" + UUID + "-Agentschap"), {
      name: "org_type_in",
      value: UUID + ":Agentschap",
    });
  });

  it("keeps a type label that contains hyphens and spaces intact", () => {
    assert.deepEqual(
      orgNodeIdToFilter("group-" + UUID + "-Zelfstandig bestuursorgaan"),
      { name: "org_type_in", value: UUID + ":Zelfstandig bestuursorgaan" },
    );
  });
});
