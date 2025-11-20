import csv
import uuid
from io import StringIO

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

from wies.core.models import User, Brand


def create_user(first_name, last_name, email, brand=None, groups=None):
    random_username = uuid.uuid4()
    user = User.objects.create(
        username=random_username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        brand=brand
    )
    if groups:
        user.groups.set(groups)
    return user


def update_user(user, first_name, last_name, email, brand=None, groups=None):
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.brand = brand
    user.save()
    if groups is not None:
        user.groups.set(groups)
    return user


def import_users_from_csv(csv_file):
    """
    Import users from a CSV file.

    Expected CSV columns:
    - first_name (required)
    - last_name (required)
    - email (required)
    - brand (optional, brand name)
    - Beheerder (optional, "y" or "n")
    - Consultant (optional, "y" or "n")
    - BDM (optional, "y" or "n")

    Returns a dictionary with:
    - success: True if all users imported, False if validation errors
    - users_created: Number of users created
    - brands_created: Number of new brands created
    - created_brands: List of brand names that were created
    - errors: List of validation error messages (empty if success=True)
    """
    # Read and decode CSV file
    try:
        csv_content = csv_file.read().decode('utf-8')
    except UnicodeDecodeError:
        return {
            'success': False,
            'users_created': 0,
            'brands_created': 0,
            'created_brands': [],
            'errors': ['Invalid CSV file encoding. Please use UTF-8.']
        }

    # Parse CSV
    csv_reader = csv.DictReader(StringIO(csv_content))

    # Validate required columns
    required_columns = {'first_name', 'last_name', 'email'}

    if not csv_reader.fieldnames:
        return {
            'success': False,
            'users_created': 0,
            'brands_created': 0,
            'created_brands': [],
            'errors': ['CSV file is empty or has no headers.']
        }

    csv_columns = set(csv_reader.fieldnames)
    missing_columns = required_columns - csv_columns

    if missing_columns:
        return {
            'success': False,
            'users_created': 0,
            'brands_created': 0,
            'created_brands': [],
            'errors': [f'Missing required columns: {", ".join(sorted(missing_columns))}']
        }

    # Read all rows and validate
    rows = []
    errors = []
    emails_found = set()

    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
        row_errors = []

        # Validate required fields
        if not row.get('first_name', '').strip():
            row_errors.append(f"Row {row_num}: first_name is required")
        if not row.get('last_name', '').strip():
            row_errors.append(f"Row {row_num}: last_name is required")
        if not row.get('email', '').strip():
            row_errors.append(f"Row {row_num}: email is required")

        # Validate email format
        email = row.get('email', '').strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                row_errors.append(f"Row {row_num}: invalid email format '{email}'")

        # Validate group columns
        for group_name in ['Beheerder', 'Consultant', 'BDM']:
            if group_name in row:
                value = row[group_name].strip().lower()
                if value not in {'y', 'n', ''}:
                    row_errors.append(
                        f"Row {row_num}: {group_name} must be 'y' or 'n', got '{row[group_name]}'"
                    )

        # Check for duplicate emails in this CSV
        if email:
            if email in emails_found:
                row_errors.append(f"Row {row_num}: duplicate email '{email}' in CSV")
            else:
                emails_found.add(email)

        if row_errors:
            errors.extend(row_errors)
        else:
            rows.append(row)

    # If validation errors, return them
    if errors:
        return {
            'success': False,
            'users_created': 0,
            'brands_created': 0,
            'created_brands': [],
            'errors': errors
        }

    # All validation passed, now create users
    users_created = 0
    created_brands = []
    brand_cache = {}  # Cache to avoid duplicate DB queries

    # Get all groups once
    groups_dict = {
        'Beheerder': Group.objects.get(name='Beheerder'),
        'Consultant': Group.objects.get(name='Consultant'),
        'BDM': Group.objects.get(name='Business Development Manager'),
    }

    for row in rows:
        print('row', row)
        first_name = row['first_name'].strip()
        last_name = row['last_name'].strip()
        email = row['email'].strip()
        brand_name = row.get('brand', '').strip()

        # Handle brand
        brand = None
        if brand_name:
            # Check cache first
            if brand_name in brand_cache:
                brand = brand_cache[brand_name]
            else:
                # Try to get existing brand
                brand = Brand.objects.filter(name=brand_name).first()
                if not brand:
                    # Create new brand
                    brand = Brand.objects.create(name=brand_name)
                    created_brands.append(brand_name)
                brand_cache[brand_name] = brand

        # Determine which groups to assign
        groups_to_assign = []
        for group_name in ['Beheerder', 'Consultant', 'BDM']:
            if row.get(group_name, '').strip().lower() == 'y':
                group = groups_dict.get(group_name)
                if group:
                    groups_to_assign.append(group)

        # Check if user with this email already exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # Skip existing users
            errors.append(f"User with email '{email}' already exists, skipped")
            continue

        # Create user
        create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            brand=brand,
            groups=groups_to_assign
        )
        users_created += 1

    return {
        'success': True,
        'users_created': users_created,
        'brands_created': len(created_brands),
        'created_brands': created_brands,
        'errors': errors  # May contain warnings when success is True
    }
