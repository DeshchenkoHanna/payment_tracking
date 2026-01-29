"""
Purchase Order payment schedule customizations
"""

import frappe
from frappe.utils import flt


def before_validate(doc, method):
    """
    Skip automatic payment schedule recalculation when manual mode is enabled.

    The standard ERPNext behavior recalculates payment_amount based on invoice_portion
    in set_payment_schedule(). When custom_manual_payment_schedule is checked,
    we store the manual payment_amount and restore it after the standard calculation runs.
    Other columns (base_payment_amount, outstanding, base_outstanding) are recalculated
    from the manual payment_amount.
    """
    if doc.get("custom_manual_payment_schedule") and doc.get("payment_schedule"):
        # Store only payment_amount - other columns will be recalculated from it
        doc._manual_payment_amounts = {
            row.name or row.idx: row.payment_amount
            for row in doc.payment_schedule
        }


def validate(doc, method):
    """
    Restore manual payment amounts after standard validation has run.
    Recalculate base_payment_amount, outstanding, base_outstanding from payment_amount.
    """
    if doc.get("custom_manual_payment_schedule") and hasattr(doc, "_manual_payment_amounts"):
        conversion_rate = flt(doc.get("conversion_rate")) or 1

        for row in doc.payment_schedule:
            key = row.name or row.idx
            if key in doc._manual_payment_amounts:
                # Restore manual payment_amount
                row.payment_amount = doc._manual_payment_amounts[key]

                # Recalculate dependent columns from payment_amount
                row.base_payment_amount = flt(
                    row.payment_amount * conversion_rate,
                    row.precision("base_payment_amount")
                )
                row.outstanding = row.payment_amount
                row.base_outstanding = row.base_payment_amount

        # Clean up temporary attribute
        del doc._manual_payment_amounts
