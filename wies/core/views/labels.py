"""Label and label-category management."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.forms.utils import ErrorDict
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from wies.core.forms import (
    LabelCategoryFormSet,
    LabelForm,
)
from wies.core.models import (
    Label,
    LabelCategory,
)
from wies.core.querysets import (
    annotate_usage_counts,
)

from ._common import hx_redirect


@permission_required("core.view_labelcategory", raise_exception=True)
def label_admin(request):
    """Main label admin page."""
    categories = annotate_usage_counts(LabelCategory.objects.all())
    return render(request, "label_admin.html", {"categories": categories})


# The sheet both renames existing categories and adds new ones.
@permission_required(["core.change_labelcategory", "core.add_labelcategory"], raise_exception=True)
def label_category_manage(request):
    """All categories in one sheet: rename, pick a colour, add rows.

    Adding a row (``extra_row``) and dropping an unsaved one
    (``delete_new_row_index``) post the current state back and re-render only the
    body without validating, so typed values survive and "naam is verplicht" does
    not flash on empty rows. Deleting an existing category goes through
    ``label-category-delete``.
    """
    queryset = LabelCategory.objects.all()
    prefix = LabelCategoryFormSet().prefix

    invalid_post = False
    if request.method == "POST":
        is_rerender = "extra_row" in request.POST or "delete_new_row_index" in request.POST
        if is_rerender:
            data = request.POST.copy()
            if "extra_row" in data:
                total = int(data.get(f"{prefix}-TOTAL_FORMS", 0) or 0)
                data[f"{prefix}-TOTAL_FORMS"] = str(total + 1)
            else:
                data = _drop_new_category_row(data, prefix, data.get("delete_new_row_index"))
            formset = LabelCategoryFormSet(data, queryset=queryset)
            # Don't validate on a row mutation: the user is still typing. Setting
            # an empty error dict suppresses the lazy full_clean.
            for form in formset.forms:
                form._errors = ErrorDict(renderer=form.renderer)
            if "extra_row" in request.POST and formset.forms:
                # Focus the row that was just added, as the old JS did.
                formset.forms[-1].fields["name"].widget.attrs["autofocus"] = True
            return _render_category_manage_body(request, formset)

        formset = LabelCategoryFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "De categorieën zijn aangepast.")
            return hx_redirect(reverse("label-admin"))
        invalid_post = True
    else:
        formset = LabelCategoryFormSet(queryset=queryset)

    if formset.forms:
        formset.forms[0].fields["name"].widget.attrs["autofocus"] = True

    # On error only the body is refreshed: the sheet is already open, and
    # re-sending the whole sheet would stack a second one on top.
    template = "parts/label_category_manage_body.html" if invalid_post else "parts/label_category_manage_sheet.html"
    return _render_category_manage_body(request, formset, template=template)


def _drop_new_category_row(data, prefix, drop_index):
    """Drops one not-yet-saved row from the posted formset data.

    New rows are renumbered contiguously: a gap in the indexes would come back as
    an empty row on the next re-render. Saved rows keep their index — a
    modelformset binds the first INITIAL_FORMS forms to the queryset in order, so
    moving one to another slot would save it as a new object.
    """
    try:
        drop = int(drop_index)
    except TypeError, ValueError:
        return data

    initial = int(data.get(f"{prefix}-INITIAL_FORMS", 0) or 0)
    total = int(data.get(f"{prefix}-TOTAL_FORMS", 0) or 0)
    if drop < initial:
        # Only new rows can be dropped this way; ignore a bogus index.
        return data

    result = data.copy()
    # Collect the field values per index, drop the removed one, then renumber the
    # new rows contiguously from INITIAL_FORMS.
    new_rows = []
    for i in range(initial, total):
        if i == drop:
            continue
        new_rows.append({k[len(f"{prefix}-{i}-") :]: v for k, v in data.items() if k.startswith(f"{prefix}-{i}-")})
    for i in range(initial, total):
        for key in [k for k in result if k.startswith(f"{prefix}-{i}-")]:
            del result[key]
    for offset, fields in enumerate(new_rows):
        i = initial + offset
        for name, value in fields.items():
            result[f"{prefix}-{i}-{name}"] = value
    result[f"{prefix}-TOTAL_FORMS"] = str(initial + len(new_rows))
    return result


def _render_category_manage_body(request, formset, template="parts/label_category_manage_body.html"):
    return render(
        request,
        template,
        {
            "formset": formset,
            "form_post_url": reverse("label-category-manage"),
        },
    )


def label_form(request, public_id=None):
    """One sheet for both adding and editing a label (category + name)."""
    # One view, two routes, so the permission depends on which one: checked
    # before the lookup, so a missing label does not answer differently.
    if not request.user.has_perm("core.change_label" if public_id else "core.add_label"):
        raise PermissionDenied
    label = get_object_or_404(Label, public_id=public_id) if public_id else None
    is_edit = label is not None

    invalid_post = False
    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            label = form.save()
            messages.success(request, f'Label "{label.name}" is {"aangepast" if is_edit else "toegevoegd"}.')
            return hx_redirect(reverse("label-admin"))
        invalid_post = True
    else:
        form = LabelForm(instance=label, category_id=request.GET.get("categorie"))

    form.fields["name"].widget.attrs["autofocus"] = True

    # On error only the body is refreshed: the sheet is already open, and
    # re-sending the whole sheet would stack a second one on top.
    template = "parts/label_form_body.html" if invalid_post else "parts/label_form_sheet.html"

    return render(
        request,
        template,
        {
            "content": form,
            "modal_title": "Label wijzigen" if is_edit else "Label toevoegen",
            "form_button_label": "Opslaan" if is_edit else "Voeg label toe",
            "form_post_url": (
                reverse("label-form-edit", kwargs={"public_id": label.public_id})
                if is_edit
                else reverse("label-form-create")
            ),
            "modal_element_id": "labelFormModal",
        },
    )


def _category_delete_warning(category):
    """The confirmation text; the labels always go with the category."""
    count = category.labels.count()
    if count == 0:
        return f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen?"
    return (
        f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen? "
        f"De {count} labels erin worden ook verwijderd."
    )


@permission_required("core.delete_labelcategory", raise_exception=True)
def label_category_delete(request, public_id):
    """Deletes a label category, after the confirmation dialog. For use with htmx."""
    category = get_object_or_404(LabelCategory, public_id=public_id)
    if request.method == "GET":
        # A dialog, not a sheet: the question comes from the manage sheet, which
        # has to stay visible behind the confirmation.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Categorie verwijderen?",
                "dialog_supporting": _category_delete_warning(category),
                "confirm_label": "Verwijder categorie en labels",
                "cancel_label": "Behoud categorie",
                "form_post_url": reverse("label-category-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        category_name = category.name  # Read before delete() clears the instance.
        # The labels cascade away with the category.
        category.delete()
        messages.success(request, f"Categorie '{category_name}' succesvol verwijderd")
        return hx_redirect(reverse("label-admin"))
    return HttpResponse(status=405)


@permission_required("core.delete_label", raise_exception=True)
def label_delete(request, public_id):
    """Deletes a label, after the confirmation dialog. For use with htmx."""

    label = get_object_or_404(Label, public_id=public_id)

    label_use_count = label.colleagues.count()

    if request.method == "GET":
        # A centred confirmation dialog, not a side sheet, like the rest of Wies.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": f"Label verwijderen: {label.name}?",
                "dialog_supporting": (
                    f"Weet je zeker dat je dit label wilt verwijderen? Het wordt gebruikt op {label_use_count} plekken."
                ),
                "confirm_label": "Verwijderen",
                "cancel_label": "Annuleren",
                "form_post_url": reverse("label-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        label_name = label.name  # Read before delete() clears the instance.
        label.delete()
        messages.success(request, f'Label "{label_name}" is verwijderd.')
        return hx_redirect(reverse("label-admin"))

    return HttpResponse(status=405)
