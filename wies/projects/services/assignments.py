from ..models import Note, Assignment, Colleague


def create_note(assignment, colleague, message):
    return Note.objects.create(
        assignment=assignment,
        colleague=colleague,
        message=message
    )
