---
name: django
description: Django development patterns for Wies. Use when working with views, forms, models, URLs, or any Django-specific code.
---

# Django Patterns for Wies

## Documentation
Always check the latest Django documentation when uncertain about APIs or best practices:
- Django docs: https://docs.djangoproject.com/en/5.2/
- Use WebFetch to verify current syntax and recommendations
- This project uses Django 5.2

## Project Structure
```
wies/
├── core/
│   ├── models.py      # All models
│   ├── views.py       # View functions/classes
│   ├── forms.py       # Django forms with RVOMixin
│   ├── urls.py        # URL routing
│   ├── roles.py       # Role/permission definitions
│   ├── querysets.py   # Custom querysets
│   └── jinja2/        # Jinja2 templates
└── config/
    └── settings/      # Django settings
```

## Models
- All models in `wies/core/models.py`
- Use `verbose_name` for Dutch field labels
- ForeignKey: always use `related_name` and `on_delete`
- Use properties for computed fields (e.g., `effective_start_date`)

```python
class MyModel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Naam")
    parent = models.ForeignKey(
        "Parent",
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        verbose_name = "Mijn Model"
        verbose_name_plural = "Mijn Modellen"
```

## Views
- Use function-based views or Django's generic CBVs
- Always check permissions with `user_can_edit_*` functions from `roles.py`
- Use `@login_required` decorator

```python
@login_required
def my_view(request):
    if not user_can_edit_something(request.user):
        return HttpResponseForbidden()
    # ...
```

## Forms
- Use `RVOMixin` for RVO design system styling
- Define `verbose_name` in model for automatic Dutch labels

```python
class MyForm(RVOMixin, forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ["field1", "field2"]
```

## Templates (Jinja2)
- Located in `wies/core/jinja2/`
- Use jinja-roos-components for UI elements
- CSRF token: `{{ get_csrf_hidden_input(request) }}`
- Static files: `{{ static('path/to/file') }}`

## Testing
- Test files in `wies/core/tests/`
- Use `self.client.force_login(user)` for authenticated tests
- Test permission checks for each role

```python
class MyViewTest(TestCase):
    def test_view_requires_login(self):
        response = self.client.get("/my-url/")
        self.assertEqual(response.status_code, 302)

    def test_view_with_permission(self):
        user = User.objects.create_user(...)
        self.client.force_login(user)
        response = self.client.get("/my-url/")
        self.assertEqual(response.status_code, 200)
```

## HTMX Integration
Views often return partial HTML for HTMX requests:

```python
def my_view(request):
    if request.headers.get("HX-Request"):
        return render(request, "parts/partial.html", context)
    return render(request, "full_page.html", context)
```
