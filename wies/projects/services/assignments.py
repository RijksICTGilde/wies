from ..models import Note, Assignment, Colleague


def create_note(assignment, colleague, message):
    """
    Create a new note for an assignment.
    
    Args:
        assignment (Assignment): The assignment instance
        colleague (Colleague): The colleague instance creating the note
        message (str): The note message
    
    Returns:
        Note: The created note instance
    """
    note = Note.objects.create(
        assignment=assignment,
        colleague=colleague,
        message=message
    )
    
    return note