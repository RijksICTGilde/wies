"""Static pages, error pages and robots.txt."""

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static

from wies.core.services import access_requests
from wies.core.services.sitemap import sitemap_sections
from wies.core.services.users import (
    is_allowed_email_domain,
)

from .access_requests import ACCESS_REQUEST_SENT_SESSION_KEY, access_request_state

# Static path of the WCAG audit report that /toegankelijkheid/onderzoek/ serves.
# A new audit: drop the HTML next to this one, point this at it, and leave the
# old file in place -- the URL stays put, so the register's link keeps working.
CURRENT_AUDIT_REPORT = "toegankelijkheid/onderzoek-wcag22-2026-09-30.html"


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    email = request.session.get("failed_login_email")
    is_allowed_domain = email and is_allowed_email_domain(email)
    return render(
        request,
        "no_access.html",
        {
            "email": email,
            "is_allowed_domain": is_allowed_domain,
            "allowed_domains": ", ".join(settings.ALLOWED_EMAIL_DOMAINS),
            "access": access_request_state(request),
            "access_states": access_requests.AccessState,
            "rejection_cooldown_days": access_requests.REJECTION_COOLDOWN.days,
            "just_sent": request.session.pop(ACCESS_REQUEST_SENT_SESSION_KEY, False),
        },
    )


def contact(request):
    return render(request, "contact.html")


def faq(request):
    return render(request, "faq.html")


def handleiding(request):
    return render(request, "handleiding.html")


def privacy(request):
    return render(request, "privacy.html")


def beveiliging(request):
    return render(request, "security.html")


def toegankelijkheid(request):
    return render(request, "toegankelijkheid.html")


def sitemap(request):
    return render(request, "sitemap.html", {"sections": sitemap_sections(request)})


# Public because the DigiToegankelijk register links straight at this URL, and
# that URL must never move: it sits in a public register that regulators check.
# Hence the redirect — the report is a static file, so in production its own name
# carries a hash that changes with every new version.
@login_not_required
def toegankelijkheid_onderzoek(request):
    """The WCAG audit report the toegankelijkheidsverklaring points at."""
    return redirect(static(CURRENT_AUDIT_REPORT))


@login_not_required
def error_400(request, exception=None):
    return render(request, "400.html", status=400)


@login_not_required
def error_403(request, exception=None):
    return render(request, "403.html", status=403)


@login_not_required
def error_404(request, exception=None):
    return render(request, "404.html", status=404)


@login_not_required
def error_500(request):
    return render(request, "500.html", status=500)


@login_not_required
def robots_txt(request):
    """Serves robots.txt, blocking crawlers and AI scrapers."""
    content = """# Disallow all crawlers
User-agent: *
Disallow: /

# AI scrapers
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Applebot-Extended
Disallow: /
"""
    return HttpResponse(content, content_type="text/plain")
