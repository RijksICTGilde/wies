"""Search suggestions for the search input on the list pages."""

from django.shortcuts import render

from wies.core.services.organizations import find_orgs_by_abbreviation


def search_suggestions(request):
    """Returns org abbreviation suggestions for the search input (HTMX partial)."""
    term = request.GET.get("zoek", "")
    orgs = find_orgs_by_abbreviation(term)
    return render(
        request,
        "parts/search_suggestions.html",
        {"org_suggestions": orgs, "search_term": term.strip()},
    )
