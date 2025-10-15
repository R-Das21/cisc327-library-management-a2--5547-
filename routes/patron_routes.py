"""
Patron Routes - Patron status report page (R7 UI)
"""

from flask import Blueprint, render_template, request, flash
from library_service import get_patron_status_report

patron_bp = Blueprint('patron', __name__)


@patron_bp.route('/status', methods=['GET'])
def status():
    """
    Display patron status report with a simple form to enter patron ID.
    """
    patron_id = request.args.get('patron_id', '').strip()
    report = None
    if patron_id:
        report = get_patron_status_report(patron_id)
        # Surface invalid patron id feedback in UI
        if report.get('status') == 'invalid_patron_id':
            flash('Invalid patron ID. Must be exactly 6 digits.', 'error')
    return render_template('patron_status.html', patron_id=patron_id, report=report)
