"""File upload handling service."""
import logging
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


def validate_image(file) -> tuple[bool, str | None]:
    """Check that an uploaded file is a valid image.

    Args:
        file: Werkzeug ``FileStorage`` object.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if file is None or file.filename == '':
        return (False, 'No file selected')

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', set())
    if ext not in allowed:
        return (False, f'File type not allowed. Allowed: {", ".join(allowed)}')

    # Check size by reading content length header (may not always be set)
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > max_size:
        return (False, f'File too large. Maximum size: {max_size // (1024 * 1024)} MB')

    return (True, None)


def save_uploaded_file(file, subfolder: str) -> str | None:
    """Save an uploaded image file to the uploads directory.

    Args:
        file: Werkzeug ``FileStorage`` object.
        subfolder: Subdirectory within the upload folder (e.g. ``'menu'``).

    Returns:
        Relative URL path to the saved file, or ``None`` on validation failure.
    """
    is_valid, error = validate_image(file)
    if not is_valid:
        logger.warning('Upload rejected: %s', error)
        return None

    original = secure_filename(file.filename)
    filename = f'{uuid.uuid4().hex}_{original}'

    output_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'], subfolder
    )
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, filename)
    file.save(filepath)

    return f'/static/images/uploads/{subfolder}/{filename}'


def delete_file(file_path: str) -> bool:
    """Delete a file given its relative URL path.

    Args:
        file_path: Relative URL (e.g. ``/static/images/uploads/menu/img.png``).

    Returns:
        ``True`` if the file was deleted, ``False`` otherwise.
    """
    try:
        # Convert relative URL to absolute filesystem path
        # Strip leading /static/ to get path relative to app/static/
        relative = file_path.lstrip('/')
        if relative.startswith('static/'):
            relative = relative[len('static/'):]

        abs_path = os.path.join(
            current_app.root_path, 'static', relative
        )

        if os.path.exists(abs_path):
            os.remove(abs_path)
            return True

        logger.warning('File not found for deletion: %s', abs_path)
        return False
    except OSError:
        logger.exception('Failed to delete file: %s', file_path)
        return False
