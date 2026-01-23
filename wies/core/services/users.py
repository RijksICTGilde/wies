import csv
import uuid
from io import StringIO

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from wies.core.errors import EmailNotAvailableError, InvalidEmailDomainError
from wies.core.models import DEFAULT_LABELS, Label, LabelCategory, User
from wies.core.services.events import create_event


def is_allowed_email_domain(email: str) -> bool:
    """Check if the email address has an allowed domain."""
    allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", [])
    if not allowed_domains:
        return True
    return any(email.lower().endswith(domain) for domain in allowed_domains)


def create_user(creator: User, first_name, last_name, email, labels=None, groups=None):
    """
    :param creator: can be None when user create is triggered from system itself
    """

    if groups is None:
        groups = []

    # Validate email domain
    if not is_allowed_email_domain(email):
        raise InvalidEmailDomainError(email)

    # django built in User model necessitates a username, this generates a random one
    random_username = uuid.uuid4()

    if User.objects.filter(email=email).exists():
        raise EmailNotAvailableError(email)

    user = User.objects.create(
        username=random_username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    label_names = []
    if labels:
        user.labels.set(labels)
        label_names = [label.name for label in labels]
    if groups:
        user.groups.set(groups)

    creator_user_email = creator.email if creator is not None else ""
    context = {
        "created_id": user.id,
        "username": str(random_username),  # casting uuid to str to have serializable json
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "label_names": label_names,
        "group_names": [group.name for group in groups],
    }
    create_event(creator_user_email, "User.create", context=context)

    return user


def update_user(updater, user, first_name, last_name, email, labels=None, groups=None):
    """
    :param updater: user that performs the update action. Can be None if done by system
    """

    if groups is None:
        groups = []

    # Validate email domain
    if not is_allowed_email_domain(email):
        raise InvalidEmailDomainError(email)

    try:
        user_with_email = User.objects.get(email=email)
        if user_with_email.id != user.id:
            raise EmailNotAvailableError(email)
    except User.DoesNotExist:
        pass

    user.first_name = first_name
    user.last_name = last_name
    user.email = email

    label_names = []
    if labels is not None:
        user.labels.set(labels)
        label_names = [label.name for label in labels]

    user.save()
    if groups:
        user.groups.set(groups)

    updater_user_email = updater.email if updater is not None else ""
    context = {
        "updated_id": user.id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "label_names": label_names,
        "group_names": [group.name for group in groups],
    }
    create_event(updater_user_email, "User.update", context=context)
    return user


def create_users_from_csv(creator, csv_content: str):
    """
    Create users from a CSV file.

    Expected CSV columns:
    - first_name (required)
    - last_name (required)
    - email (required)
    - brand (optional, label name - will be assigned from "Merk" category, auto-created if needed)
    - Beheerder (optional, "y" or "n")
    - Consultant (optional, "y" or "n")
    - BDM (optional, "y" or "n")

    Returns a dictionary with:
    - success: True if all users imported, False if validation errors
    - users_created: Number of users created
    - labels_created: Number of new labels created
    - created_labels: List of label names that were created
    - errors: List of validation error messages (empty if success=True)
    """

    csv_reader = csv.DictReader(StringIO(csv_content))

    # Validate required columns
    required_columns = {"first_name", "last_name", "email"}

    if not csv_reader.fieldnames:
        return {
            "success": False,
            "users_created": 0,
            "brands_created": 0,
            "created_brands": [],
            "errors": ["CSV file is empty or has no headers."],
        }

    csv_columns = set(csv_reader.fieldnames)
    missing_columns = required_columns - csv_columns

    if missing_columns:
        return {
            "success": False,
            "users_created": 0,
            "brands_created": 0,
            "created_brands": [],
            "errors": [f"Missing required columns: {', '.join(sorted(missing_columns))}"],
        }

    # Read all rows and validate
    rows = []
    errors = []
    emails_found = set()

    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
        row_errors = []

        if not row.get("first_name", "").strip():
            row_errors.append(f"Row {row_num}: first_name is required")
        if not row.get("last_name", "").strip():
            row_errors.append(f"Row {row_num}: last_name is required")
        if not row.get("email", "").strip():
            row_errors.append(f"Row {row_num}: email is required")

        email = row.get("email", "").strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                row_errors.append(f"Row {row_num}: invalid email format '{email}'")

            if not is_allowed_email_domain(email):
                allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", [])
                domains_str = ", ".join(allowed_domains)
                row_errors.append(f"Row {row_num}: email '{email}' has invalid domain. Allowed: {domains_str}")

        for group_name in ["Beheerder", "Consultant", "BDM"]:
            if group_name in row:
                value = row[group_name].strip().lower()
                if value not in {"y", "n", ""}:
                    row_errors.append(f"Row {row_num}: {group_name} must be 'y' or 'n', got '{row[group_name]}'")

        if email:
            if email in emails_found:
                row_errors.append(f"Row {row_num}: duplicate email '{email}' in CSV")
            else:
                emails_found.add(email)

        if row_errors:
            errors.extend(row_errors)
        else:
            rows.append(row)

    if errors:
        return {"success": False, "users_created": 0, "labels_created": 0, "created_labels": [], "errors": errors}

    users_created = 0
    created_labels = []
    label_mapping = {}  # mapping from str to Label, to avoid many DB queries

    merken_category, _ = LabelCategory.objects.get_or_create(
        name="Merk", defaults={"color": DEFAULT_LABELS["Merk"]["color"]}
    )

    # Get all groups once
    groups_dict = {
        "Beheerder": Group.objects.get(name="Beheerder"),
        "Consultant": Group.objects.get(name="Consultant"),
        "BDM": Group.objects.get(name="Business Development Manager"),
    }

    for row in rows:
        first_name = row["first_name"].strip()
        last_name = row["last_name"].strip()
        email = row["email"].strip()
        brand_name = row.get("brand", "").strip()

        # Handle label assignment from brand column
        labels_to_assign = []
        if brand_name:
            if brand_name in label_mapping:
                label = label_mapping[brand_name]
            else:
                label, created = Label.objects.get_or_create(name=brand_name, category=merken_category)
                label_mapping[brand_name] = label
                if created:
                    created_labels.append(brand_name)
            labels_to_assign.append(label)

        groups_to_assign = []
        for group_name in ["Beheerder", "Consultant", "BDM"]:
            if row.get(group_name, "").strip().lower() == "y":
                group = groups_dict.get(group_name)
                if group:
                    groups_to_assign.append(group)

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # Skip existing users
            errors.append(f"User with email '{email}' already exists, skipped")
            continue

        create_user(
            creator,
            first_name=first_name,
            last_name=last_name,
            email=email,
            labels=labels_to_assign,
            groups=groups_to_assign,
        )
        users_created += 1

    return {
        "success": True,
        "users_created": users_created,
        "labels_created": len(created_labels),
        "created_labels": created_labels,
        "errors": errors,  # May contain warnings when success is True
    }
