"""Suborganization management."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from wies.core.forms import (
    SuborganizationForm,
)
from wies.core.models import (
    Suborganization,
)
from wies.core.querysets import (
    annotate_suborganization_usage_counts,
)


@permission_required("core.view_suborganization", raise_exception=True)
def suborganization_admin(request):
    """Main onderdelen admin page."""
    suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
    return render(request, "suborganization_admin.html", {"suborganizations": suborganizations})


@permission_required("core.add_suborganization", raise_exception=True)
def suborganization_create(request):
    """Creates a suborganization via the sheet (htmx).

    GET opens the sheet, a valid POST saves and re-renders the onderdeel list while
    closing it, an invalid POST re-renders only the body so the sheet keeps
    standing.
    """
    form_post_url = reverse("suborganization-create")
    modal_title = "Onderdeel toevoegen"
    form_button_label = "Voeg onderdeel toe"
    element_id = "suborganizationFormModal"

    if request.method == "POST":
        form = SuborganizationForm(request.POST)
        if form.is_valid():
            suborganization = form.save()
            # The list partial carries the flash block out of band; see the template.
            messages.success(request, f'Onderdeel "{suborganization.name}" is toegevoegd.')
            suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
            response = render(request, "parts/suborganization_list.html", {"suborganizations": suborganizations})
            response["HX-Retarget"] = "#suborganization_list_container"
            response["HX-Trigger"] = "closeModal"
            return response
    else:
        form = SuborganizationForm()
        # Focus the name field on GET only; after a validation error the focus
        # belongs with the failing field instead of jumping back to the top.
        form.fields["name"].widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/generic_form_modal.html",
        {
            "content": form,
            "form_post_url": form_post_url,
            "modal_title": modal_title,
            "form_button_label": form_button_label,
            "modal_element_id": element_id,
            "target_element_id": element_id,
        },
    )


@permission_required("core.change_suborganization", raise_exception=True)
def suborganization_edit(request, public_id):
    """Edits a suborganization. Returns a partial for use with htmx."""
    suborganization = get_object_or_404(Suborganization, public_id=public_id)
    form_post_url = reverse("suborganization-edit", kwargs={"public_id": public_id})
    modal_title = f"Onderdeel wijzigen: {suborganization.name}"
    form_button_label = "Opslaan"
    element_id = "suborganizationFormModal"

    if request.method == "GET":
        form = SuborganizationForm(instance=suborganization)
        form.fields["name"].widget.attrs["autofocus"] = True
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": form_button_label,
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = SuborganizationForm(request.POST, instance=suborganization)
        if form.is_valid():
            form.save()
            messages.success(request, f'Onderdeel "{suborganization.name}" is aangepast.')
            suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
            response = render(request, "parts/suborganization_list.html", {"suborganizations": suborganizations})
            response["HX-Retarget"] = "#suborganization_list_container"
            response["HX-Trigger"] = "closeModal"
            return response
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": form_button_label,
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return HttpResponse(status=405)


@permission_required("core.delete_suborganization", raise_exception=True)
def suborganization_delete(request, public_id):
    """Deletes a suborganization. For use with htmx."""
    suborganization = get_object_or_404(Suborganization, public_id=public_id)
    suborganization_use_count = suborganization.colleagues.count()

    if request.method == "GET":
        # A centred confirmation dialog, not a side sheet, like the rest of Wies.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": f"Onderdeel verwijderen: {suborganization.name}?",
                "dialog_supporting": (
                    f"Weet je zeker dat je dit onderdeel wilt verwijderen? "
                    f"Het wordt gebruikt door {suborganization_use_count} collega('s)."
                ),
                "confirm_label": "Verwijderen",
                "cancel_label": "Annuleren",
                "form_post_url": reverse("suborganization-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        name = suborganization.name  # Read before delete() clears the instance.
        suborganization.delete()
        messages.success(request, f'Onderdeel "{name}" is verwijderd.')
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("suborganization-admin")
        return response
    return HttpResponse(status=405)
