__version__ = "0.0.1"

import erpnext.accounts.doctype.payment_entry.payment_entry as pe_module
import erpnext.accounts.utils as accounts_utils_module
from frappe.utils import flt


# =============================================================================
# Patch 1: get_reference_as_per_payment_terms
# Include Payment Schedule idx when creating PE from PO/PI with payment terms
# =============================================================================

def _patched_get_reference_as_per_payment_terms(
    payment_schedule, dt, dn, doc, grand_total, outstanding_amount, party_account_currency
):
    """Patched version that includes Payment Schedule idx in each reference dict."""
    references = []
    is_multi_currency_acc = (doc.currency != doc.company_currency) and (
        party_account_currency != doc.company_currency
    )

    for payment_term in payment_schedule:
        payment_term_outstanding = flt(
            payment_term.payment_amount - payment_term.paid_amount,
            payment_term.precision("payment_amount"),
        )
        if not is_multi_currency_acc:
            payment_term_outstanding = flt(
                payment_term_outstanding * doc.get("conversion_rate"),
                payment_term.precision("payment_amount"),
            )

        if payment_term_outstanding:
            references.append(
                {
                    "reference_doctype": dt,
                    "reference_name": dn,
                    "bill_no": doc.get("bill_no"),
                    "due_date": doc.get("due_date"),
                    "total_amount": grand_total,
                    "outstanding_amount": outstanding_amount,
                    "payment_term_outstanding": payment_term_outstanding,
                    "payment_term": payment_term.payment_term,
                    "allocated_amount": payment_term_outstanding,
                    "custom_payment_schedule_idx": payment_term.idx,
                }
            )

    return references


pe_module.get_reference_as_per_payment_terms = _patched_get_reference_as_per_payment_terms


# =============================================================================
# Patch 2: update_reference_in_payment_entry
# Copy custom_payment_schedule_idx and payment_term when advance payment is allocated to invoice
# NOTE: We do NOT update Payment Schedule here - CustomPaymentEntry.update_payment_schedule()
# handles that when the PE is saved/submitted after allocation
# =============================================================================

_original_update_reference_in_payment_entry = accounts_utils_module.update_reference_in_payment_entry


def _patched_update_reference_in_payment_entry(
    d, payment_entry, do_not_save=False, skip_ref_details_update_for_pe=False, dimensions_dict=None
):
    """
    Patched version that:
    1. Copies custom_payment_schedule_idx from original PO/SO reference to new PI/SI reference
    2. Copies payment_term from original reference

    NOTE: Payment Schedule update is handled by CustomPaymentEntry.update_payment_schedule()
    when the PE is saved after allocation, so we don't update it here to avoid double updates.
    """
    # Capture the original row's data before calling original function
    original_idx = None
    original_payment_term = None

    if d.voucher_detail_no:
        existing_rows = payment_entry.get("references", {"name": d["voucher_detail_no"]})
        if existing_rows:
            original_row = existing_rows[0]
            original_idx = original_row.get("custom_payment_schedule_idx")
            original_payment_term = original_row.get("payment_term")

    # Call original function
    row = _original_update_reference_in_payment_entry(
        d, payment_entry, do_not_save, skip_ref_details_update_for_pe, dimensions_dict
    )

    # Copy custom_payment_schedule_idx and payment_term to the new row if it was an advance allocation
    if row and original_idx:
        if not row.get("custom_payment_schedule_idx"):
            row.custom_payment_schedule_idx = original_idx
        if not row.get("payment_term") and original_payment_term:
            row.payment_term = original_payment_term

    return row


accounts_utils_module.update_reference_in_payment_entry = _patched_update_reference_in_payment_entry
