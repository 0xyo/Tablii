"""QR code generation service for table links."""
import logging
import os

import qrcode
from flask import current_app, request

logger = logging.getLogger(__name__)


def generate_qr_code(data: str, filename: str) -> str | None:
    """Generate a QR code PNG and save it to the uploads directory.

    Args:
        data: The URL or text to encode.
        filename: Output filename (e.g. ``table_slug_1.png``).

    Returns:
        Relative URL path to the saved image, or ``None`` on error.
    """
    try:
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        output_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'], 'qrcodes'
        )
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)
        img.save(filepath)

        return f'/static/images/uploads/qrcodes/{filename}'
    except Exception:
        logger.exception('Failed to generate QR code for %s', filename)
        return None


def get_table_url(restaurant_slug: str, table_id: int) -> str:
    """Build the public URL a customer scans to start a session.

    Args:
        restaurant_slug: Restaurant's URL slug.
        table_id: Table primary key.

    Returns:
        Full URL like ``https://host/r/my-resto-ab12/table/3``.
    """
    return f'{request.host_url}r/{restaurant_slug}/table/{table_id}'


def generate_table_qr(
    restaurant_slug: str, table_id: int, table_number: int
) -> str | None:
    """Generate and save a QR code for a specific table.

    Args:
        restaurant_slug: Restaurant's URL slug.
        table_id: Table primary key.
        table_number: Human-readable table number (used in filename).

    Returns:
        Relative URL path to the QR image, or ``None`` on error.
    """
    url = get_table_url(restaurant_slug, table_id)
    filename = f'table_{restaurant_slug}_{table_number}.png'
    return generate_qr_code(url, filename)
