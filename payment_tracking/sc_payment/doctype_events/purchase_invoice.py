"""
Purchase Invoice payment schedule customizations
"""

import frappe
from frappe.utils import flt


def before_save(doc, method):
    """
    Fix payment schedule when inherited from a PO.

    This runs AFTER ERPNext's validate/set_payment_schedule which incorrectly:
    - Recalculates payment_amount based on (grand_total - total_advance) instead of keeping PO values
    - Sets outstanding = payment_amount (ignoring paid_amount)
    - Copies paid_amount from PO (which shouldn't happen for new PI)

    Issues fixed:
    1. Restore original payment_amount from linked PO
    2. Reset paid_amount to 0 for new PI
    3. Set outstanding = payment_amount - paid_amount
    """
    if not doc.get("payment_schedule"):
        return

    # Only fix for draft invoices (not yet submitted)
    if doc.docstatus != 0:
        return

    # Get linked PO from items
    po_name = None
    for item in doc.get("items", []):
        if item.get("purchase_order"):
            po_name = item.purchase_order
            break

    # Fetch original payment_amount values from PO
    po_schedule_map = {}
    if po_name:
        po_schedule = frappe.get_all(
            "Payment Schedule",
            filters={"parent": po_name},
            fields=["idx", "payment_amount", "base_payment_amount", "payment_term"],
            order_by="idx"
        )
        for ps in po_schedule:
            po_schedule_map[ps.idx] = ps

    for row in doc.payment_schedule:
        # Restore original payment_amount from PO if available
        if row.idx in po_schedule_map:
            po_row = po_schedule_map[row.idx]
            row.payment_amount = po_row.payment_amount
            row.base_payment_amount = po_row.base_payment_amount

        # For new PI, paid_amount should be 0 (no payments made to PI yet)
        row.paid_amount = 0
        row.base_paid_amount = 0
        row.discounted_amount = 0

        # Fix outstanding = payment_amount - paid_amount
        row.outstanding = flt(row.payment_amount) - flt(row.paid_amount)
        row.base_outstanding = flt(row.base_payment_amount) - flt(row.base_paid_amount)


def before_submit(doc, method):
    """
    Fix payment schedule before submit.

    ERPNext's validate process recalculates payment_amount based on (grand_total - total_advance).
    We need to restore the original values from PO and fix outstanding before the document is saved.
    """
    if not doc.get("payment_schedule"):
        return

    # Get linked PO from items
    po_name = None
    for item in doc.get("items", []):
        if item.get("purchase_order"):
            po_name = item.purchase_order
            break

    if not po_name:
        return

    # Fetch original payment_amount values from PO
    po_schedule = frappe.get_all(
        "Payment Schedule",
        filters={"parent": po_name},
        fields=["idx", "payment_amount", "base_payment_amount"],
        order_by="idx"
    )
    po_schedule_map = {ps.idx: ps for ps in po_schedule}

    # Fix values in doc before save
    for row in doc.payment_schedule:
        if row.idx in po_schedule_map:
            po_row = po_schedule_map[row.idx]
            row.payment_amount = po_row.payment_amount
            row.base_payment_amount = po_row.base_payment_amount
            # Fix outstanding = payment_amount - paid_amount
            row.outstanding = flt(row.payment_amount) - flt(row.paid_amount)
            row.base_outstanding = flt(row.base_payment_amount) - flt(row.base_paid_amount)
