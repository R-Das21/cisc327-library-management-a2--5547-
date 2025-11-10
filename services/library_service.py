"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .payment_service import PaymentGateway
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books,  get_patron_borrowed_books,
)
import re
# Utilities 

def _parse_dt(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None


def _monetize(amount: float) -> float:
    try:
        return float(f"{float(amount):.2f}")
    except Exception:
        return 0.0


def _compute_fee_from_due_and_end(due_dt: datetime, end_dt: datetime) -> Tuple[float, int]:
    if not due_dt or not end_dt:
        return 0.0, 0
    days_overdue = (end_dt.date() - due_dt.date()).days
    if days_overdue <= 0:
        return 0.0, 0
    first_seven = min(days_overdue, 7)
    remainder = max(days_overdue - 7, 0)
    fee = first_seven * 0.50 + remainder * 1.00
    fee = min(fee, 15.00)
    return _monetize(fee), int(days_overdue)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def get_catalog_display() -> List[Dict]:
    books = get_all_books() or []
    formatted: List[Dict] = []
    for b in books:
        available = int(b.get('available_copies', 0) or 0)
        total = int(b.get('total_copies', 0) or 0)
        formatted.append({
            'id': b.get('id'),
            'title': b.get('title'),
            'author': b.get('author'),
            'isbn': b.get('isbn'),
            'available_copies': available,
            'total_copies': total,
            'availability': f"{available} / {total}",
            'can_borrow': available > 0,
        })
    return formatted

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)

    if current_borrowed >= 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."

    # Verify book exists
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."

    # Confirm this patron currently has this book borrowed
    current = get_patron_borrowed_books(patron_id) or []
    active = next((r for r in current if int(r.get('book_id')) == int(book_id)), None)
    if not active:
        return False, "No active borrow record found for this patron and book."

    # Compute late fee BEFORE returning
    due_dt = active.get('due_date')
    if not isinstance(due_dt, datetime):
        due_dt = _parse_dt(due_dt)
    end_dt = datetime.now()
    fee_amt, days_overdue = _compute_fee_from_due_and_end(due_dt, end_dt)

    # Record return date and increment availability
    if not update_borrow_record_return_date(patron_id, book_id, end_dt):
        return False, "Database error while recording the return."
    if not update_book_availability(book_id, +1):
        return False, "Database error while updating book availability."

    if fee_amt > 0:
        return True, (f'Returned "{book.get("title")}". Late fee: ${fee_amt:.2f} '
                      f'(overdue by {days_overdue} day(s)).')
    else:
        return True, f'Returned "{book.get("title")}" on time. No late fee.'

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate the current late fee for an actively borrowed book.
    If the book is not actively borrowed by the patron, returns status 'not_found'.
    """
    current = get_patron_borrowed_books(patron_id) or []
    active = next((r for r in current if int(r.get('book_id')) == int(book_id)), None)
    if not active:
        return {'fee_amount': 0.0, 'days_overdue': 0, 'status': 'not_found'}

    due_dt = active.get('due_date')
    if not isinstance(due_dt, datetime):
        due_dt = _parse_dt(due_dt)

    fee_amt, days_overdue = _compute_fee_from_due_and_end(due_dt, datetime.now())
    status = 'ok' if days_overdue > 0 else 'not_overdue'
    return {
        'fee_amount': _monetize(fee_amt),
        'days_overdue': int(days_overdue),
        'due_date': due_dt.strftime("%Y-%m-%d") if due_dt else None,
        'status': status
    }

def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    
    TODO: Implement R6 as per requirements
    """
    if search_term is None:
        return []
    term = str(search_term).strip()
    if not term:
        return []

    stype = (search_type or "").strip().lower()
    books = get_all_books() or []
    results = []

    if stype == "isbn":
        norm_term = re.sub(r"\D", "", term)
        for b in books:
            isbn = re.sub(r"\D", "", str(b.get('isbn', "")))
            if isbn == norm_term and isbn:
                results.append(b)
    elif stype in ("title", "author"):
        low_term = term.lower()
        for b in books:
            val = str(b.get(stype, "") or "").lower()
            if low_term in val:
                results.append(b)
    else:
        low_term = term.lower()
        for b in books:
            title = str(b.get('title', "") or "").lower()
            author = str(b.get('author', "") or "").lower()
            if low_term in title or low_term in author:
                results.append(b)

    formatted: List[Dict] = []
    for b in results:
        available = int(b.get('available_copies', 0) or 0)
        total = int(b.get('total_copies', 0) or 0)
        formatted.append({
            'id': b.get('id'),
            'title': b.get('title'),
            'author': b.get('author'),
            'isbn': b.get('isbn'),
            'available_copies': available,
            'total_copies': total,
            'availability': f"{available} / {total}",
            'can_borrow': available > 0,
        })
    return formatted
    

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Current status report for a patron, including current borrows and full borrow history.
    """
    report = {
        'patron_id': patron_id,
        'current_borrows': [],
        'current_borrow_count': 0,
        'total_late_fees': 0.0,
        'history': [],
        'status': 'ok',
    }

    # validate patron id
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        report['status'] = 'invalid_patron_id'
        return report

    # Current borrows  
    current = get_patron_borrowed_books(patron_id) or []
    total_fees = 0.0
    for r in current:
        due_dt = r.get('due_date')
        if not isinstance(due_dt, datetime):
            due_dt = _parse_dt(due_dt)
        fee_amt, days_overdue = _compute_fee_from_due_and_end(due_dt, datetime.now())
        total_fees += fee_amt
        report['current_borrows'].append({
            'book_id': r.get('book_id'),
            'title': r.get('title'),
            'due_date': due_dt.strftime("%Y-%m-%d") if due_dt else None,
            'days_overdue': days_overdue,
            'late_fee': _monetize(fee_amt),
        })

    report['current_borrow_count'] = len(report['current_borrows'])
    report['total_late_fees'] = _monetize(total_fees)

    # Borrowing history 
    try:
        import database as db
        conn = db.get_db_connection()
        rows = conn.execute(
            """
            SELECT br.book_id, b.title, br.borrow_date, br.due_date, br.return_date
            FROM borrow_records br
            JOIN books b ON b.id = br.book_id
            WHERE br.patron_id = ?
            ORDER BY br.borrow_date DESC
            """,
            (patron_id,)
        ).fetchall()
        conn.close()

        history = []
        for row in rows:
            bd = _parse_dt(row["borrow_date"])
            dd = _parse_dt(row["due_date"])
            rd = _parse_dt(row["return_date"]) if row["return_date"] else None
            history.append({
                'book_id': row['book_id'],
                'title': row['title'],
                'borrow_date': bd.strftime("%Y-%m-%d") if bd else None,
                'due_date': dd.strftime("%Y-%m-%d") if dd else None,
                'return_date': rd.strftime("%Y-%m-%d") if rd else None,
            })
        report['history'] = history
    except Exception:
        # If anything fails, leave history empty 
        report['history'] = []

    return report
def pay_late_fees(patron_id: str, book_id: int, payment_gateway: PaymentGateway = None) -> Tuple[bool, str, Optional[str]]:
    """
    Process payment for late fees using external payment gateway.
    
    NEW FEATURE FOR ASSIGNMENT 3: Demonstrates need for mocking/stubbing
    This function depends on an external payment service that should be mocked in tests.
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book with late fees
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str, transaction_id: Optional[str])
        
    Example for you to mock:
        # In tests, mock the payment gateway:
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123", "Success")
        success, msg, txn = pay_late_fees("123456", 1, mock_gateway)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits.", None
    
    # Calculate late fee first
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    
    # Check if there's a fee to pay
    if not fee_info or 'fee_amount' not in fee_info:
        return False, "Unable to calculate late fees.", None
    
    fee_amount = fee_info.get('fee_amount', 0.0)
    
    if fee_amount <= 0:
        return False, "No late fees to pay for this book.", None
    
    # Get book details for payment description
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found.", None
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process payment through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN THEIR TESTS!
    try:
        success, transaction_id, message = payment_gateway.process_payment(
            patron_id=patron_id,
            amount=fee_amount,
            description=f"Late fees for '{book['title']}'"
        )
        
        if success:
            return True, f"Payment successful! {message}", transaction_id
        else:
            return False, f"Payment failed: {message}", None
            
    except Exception as e:
        # Handle payment gateway errors
        return False, f"Payment processing error: {str(e)}", None


def refund_late_fee_payment(transaction_id: str, amount: float, payment_gateway: PaymentGateway = None) -> Tuple[bool, str]:
    """
    Refund a late fee payment (e.g., if book was returned on time but fees were charged in error).
    
    NEW FEATURE FOR ASSIGNMENT 3: Another function requiring mocking
    
    Args:
        transaction_id: Original transaction ID to refund
        amount: Amount to refund
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate inputs
    if not transaction_id or not transaction_id.startswith("txn_"):
        return False, "Invalid transaction ID."
    
    if amount <= 0:
        return False, "Refund amount must be greater than 0."
    
    if amount > 15.00:  # Maximum late fee per book
        return False, "Refund amount exceeds maximum late fee."
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process refund through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN YOUR TESTS!
    try:
        success, message = payment_gateway.refund_payment(transaction_id, amount)
        
        if success:
            return True, message
        else:
            return False, f"Refund failed: {message}"
            
    except Exception as e:
        return False, f"Refund processing error: {str(e)}"