# Analysis: User and Colleague Model Architecture

## Context

We evaluated whether to merge the User and Colleague models. Inputs considered:

1. **Current state**: User (auth) + Colleague (business) with OneToOne link, duplicate fields
2. **~1:1 ratio**: Users and Colleagues are created together; on departure the User is deleted, Colleague kept for history
3. **Issue #138**: Proposal to extract auth into a reusable `wies.auth` app, requiring a clean User model
4. **N+1 concern**: Properties delegating to `user.*` would require `select_related("user")` on every Colleague query
5. **Self-editing**: Users should be able to edit their own first name, last name, and labels (but not email or roles)

---

## Verdict: Keep separate, consolidate labels

**Don't merge.** Issue #138 plans to make User a reusable auth package — merging Wies-specific fields onto it would conflict with that goal.

**Don't use properties for name/email.** The N+1 risk is real — `colleague.name` is accessed in list views (placement tables, assignment panels) where Colleagues are fetched via `select_related("colleague")` but not `select_related("colleague__user")`. Adding a property that hits `user` would silently introduce extra queries.

**Do move labels from User to Colleague.** This is the one concrete improvement worth making now:

- Labels are Wies-specific business data (brand, expertise), not auth data
- Eliminates the duplicate M2M and the awkward priority logic in templates
- Unblocks #138 by making User a clean auth-only model
- No N+1 risk since labels are a M2M (always fetched separately, never via `select_related`)

---

## What to change

### Model

Remove `labels` from User. Labels already exist on Colleague — just stop using User's copy.

```python
# Before
class User(AbstractUser):
    email = models.EmailField(unique=True)
    labels = models.ManyToManyField("Label", related_name="users", blank=True)  # remove this

# After
class User(AbstractUser):
    email = models.EmailField(unique=True)
```

### Self-editing implication

With labels on Colleague, a self-edit form touches **two models**:

- **User**: `first_name`, `last_name`
- **Colleague**: `labels`

This is a standard Django pattern (User + Profile form). The form can save to both in one view. Email and roles (groups) stay read-only — not included in the form.

Note: when a user edits their own name, `Colleague.name` should also be updated to stay in sync (or we accept they may drift). A simple approach: update `Colleague.name` from `f"{first_name} {last_name}"` in the same save.

### Name and email: source of truth vs cache

`Colleague.name` and `Colleague.email` are **cached copies** of User data. They exist as real DB fields (not properties) to avoid N+1 queries and to preserve data when a User is deleted.

| Field | Source of truth                      | Cache             | When cache is authoritative                                                              |
| ----- | ------------------------------------ | ----------------- | ---------------------------------------------------------------------------------------- |
| Name  | `User.first_name` + `User.last_name` | `Colleague.name`  | When `Colleague.user` is NULL (departed)                                                 |
| Email | `User.email`                         | `Colleague.email` | When `Colleague.user` is NULL (departed), and as matching key for initial import/linking |

**Sync approach: service layer.** Update `Colleague.name` and `Colleague.email` in `create_user()`, `update_user()`, and the future self-edit flow. No signals — explicit and easy to follow.

### What to keep as-is

- `Colleague.name` and `Colleague.email` — real fields, no properties, avoids N+1
- `Colleague.user` as optional OneToOne (`null=True`) — needed for departed colleagues
- `hasattr(user, "colleague")` checks — still needed for edge cases

---

## Files to modify

| File                                                  | Change                                                                                               |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `wies/core/models.py`                                 | Remove `labels` M2M from User                                                                        |
| `wies/core/forms.py`                                  | Move label assignment from UserForm to Colleague editing flow                                        |
| `wies/core/services/users.py`                         | Remove label handling from `create_user()`/`update_user()`. Add name/email sync to linked Colleague. |
| `wies/core/jinja2/parts/colleague_panel_content.html` | Remove priority logic, always use `colleague.labels`                                                 |
| `wies/core/querysets.py`                              | Remove `Count("users")` from `annotate_usage_counts()`, only count `colleagues`                      |
| `wies/core/views.py`                                  | Update any label-related view logic                                                                  |
| `wies/core/management/commands/load_full_data.py`     | Assign labels to Colleagues instead of Users                                                         |
| Tests                                                 | Update label-related test data and assertions                                                        |

## Data migration

- For any existing User labels that aren't on the linked Colleague: copy them to `colleague.labels` before removing the field
- Migration needed (removing M2M from User)

## Verification

1. Run `just test`
2. Verify colleague panel shows labels correctly (no more priority logic)
3. Verify label management admin page still shows correct usage counts
4. Verify user creation/editing flow works without label assignment on User
5. Check that label filtering on placement list still works
