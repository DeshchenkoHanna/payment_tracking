import frappe
from frappe import _


@frappe.whitelist()
def can_create_payment_request(purchase_order, payment_amount):
    """
    Validate if Payment Request can be created (ERPNext standard logic)
    Returns: {can_create: bool, error_message: str}
    """
    po = frappe.get_doc("Purchase Order", purchase_order)
    payment_amount = float(payment_amount)

    # Calculate available amount (same as ERPNext)
    grand_total = po.rounded_total or po.grand_total
    advance_paid = po.advance_paid or 0
    available_amount = grand_total - advance_paid

    # If already fully paid
    if available_amount <= 0:
        return {
            "can_create": False,
            "error_message": _("Payment Entry is already created")
        }

    # Get existing Payment Request amount (all submitted PRs)
    existing_pr_amount = get_existing_payment_request_amount(po)

    # Calculate remaining amount after existing PRs
    remaining_amount = available_amount - existing_pr_amount

    if remaining_amount <= 0:
        return {
            "can_create": False,
            "error_message": _("Payment Request is already created")
        }

    # Check if new PR amount would exceed available
    if payment_amount > remaining_amount:
        return {
            "can_create": False,
            "error_message": _("Payment Request amount ({0}) exceeds available amount ({1})").format(
                frappe.format_value(payment_amount, {"fieldtype": "Currency"}),
                frappe.format_value(remaining_amount, {"fieldtype": "Currency"})
            )
        }

    return {"can_create": True}


def get_existing_payment_request_amount(purchase_order_doc):
    """Get total amount of all submitted Payment Requests against Purchase Order"""
    from frappe.query_builder import DocType
    from frappe.query_builder.functions import Sum

    PR = DocType("Payment Request")

    result = (
        frappe.qb.from_(PR)
        .select(Sum(PR.grand_total))
        .where(PR.reference_doctype == "Purchase Order")
        .where(PR.reference_name == purchase_order_doc.name)
        .where(PR.docstatus == 1)  # Only submitted
    ).run()

    return result[0][0] or 0


def link_payment_request_to_schedule(doc, method=None):
    """
    Link Payment Request back to Payment Schedule after it's created.
    This runs after_insert, so the document already has a name.
    """
    # Only process if it's linked to a Purchase Order
    if doc.reference_doctype != "Purchase Order" or not doc.reference_name:
        return

    # Check if Payment Request has payment_term_pos field
    if not hasattr(doc, 'payment_term_pos') or not doc.payment_term_pos:
        return

    try:
        # Get the Purchase Order
        po = frappe.get_doc("Purchase Order", doc.reference_name)

        # Find the payment schedule row by payment_term_pos (idx)
        for schedule_row in po.payment_schedule:
            if schedule_row.idx == doc.payment_term_pos:
                # Update the custom fields
                schedule_row.custom_invoice_doctype = "Payment Request"
                schedule_row.custom_invoice_name = doc.name
                break

        # Save the Purchase Order (ignore permissions to allow system update)
        po.flags.ignore_validate_update_after_submit = True
        po.flags.ignore_permissions = True
        po.save()

        frappe.msgprint(
            _("Payment Request {0} linked to Payment Schedule row {1}").format(
                frappe.bold(doc.name),
                doc.payment_term_pos
            )
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error linking Payment Request {doc.name} to Purchase Order {doc.reference_name}: {e!s}",
            title="Payment Request Linking Error"
        )


def link_purchase_invoice_to_schedule(doc, method=None):
    """
    Link Purchase Invoice back to Payment Schedule after it's created.
    Purchase Invoice is always linked to the LAST row of Payment Schedule.
    This runs after_insert, so the document already has a name.
    """
    # Only process if it has items linked to a Purchase Order
    if not doc.items:
        return

    # Get the first Purchase Order reference from items
    purchase_order_name = None
    for item in doc.items:
        if item.purchase_order:
            purchase_order_name = item.purchase_order
            break

    if not purchase_order_name:
        return

    try:
        # Get the Purchase Order
        po = frappe.get_doc("Purchase Order", purchase_order_name)

        # Check if Purchase Order has payment schedule
        if not po.payment_schedule or len(po.payment_schedule) == 0:
            return

        # Get the LAST row of payment schedule
        last_row = po.payment_schedule[-1]

        # Check if last row already has an invoice linked
        if last_row.custom_invoice_name:
            # Already linked, skip
            return

        # Link Purchase Invoice to the last row
        last_row.custom_invoice_doctype = "Purchase Invoice"
        last_row.custom_invoice_name = doc.name

        # Save the Purchase Order (ignore permissions to allow system update)
        po.flags.ignore_validate_update_after_submit = True
        po.flags.ignore_permissions = True
        po.save()

        frappe.msgprint(
            _("Purchase Invoice {0} linked to Payment Schedule last row").format(
                frappe.bold(doc.name)
            )
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error linking Purchase Invoice {doc.name} to Purchase Order {purchase_order_name}: {e!s}",
            title="Purchase Invoice Linking Error"
        )


def unlink_purchase_invoice_from_schedule(doc, method=None):
    """
    Remove Purchase Invoice link from Payment Schedule when PI is cancelled.
    This runs before_cancel of Purchase Invoice.
    """
    _do_unlink_purchase_invoice(doc.name, doc.items)


@frappe.whitelist()
def unlink_purchase_invoice_before_cancel(invoice_name):
    """
    Whitelisted API to unlink Purchase Invoice from PO Payment Schedule.
    Called from JS before the cancel flow starts.
    """
    pi = frappe.get_doc("Purchase Invoice", invoice_name)
    _do_unlink_purchase_invoice(pi.name, pi.items)


def _do_unlink_purchase_invoice(invoice_name, items):
    """Core logic to unlink Purchase Invoice from PO Payment Schedule."""
    if not items:
        return

    # Get linked Purchase Order from items
    purchase_order_name = None
    for item in items:
        if item.purchase_order:
            purchase_order_name = item.purchase_order
            break

    if not purchase_order_name:
        return

    try:
        # Find Payment Schedule rows that link to this Purchase Invoice
        schedule_rows = frappe.get_all(
            "Payment Schedule",
            filters={
                "parent": purchase_order_name,
                "parenttype": "Purchase Order",
                "custom_invoice_doctype": "Purchase Invoice",
                "custom_invoice_name": invoice_name
            },
            fields=["name", "idx"]
        )

        if not schedule_rows:
            return

        # Clear the links
        for row in schedule_rows:
            frappe.db.set_value(
                "Payment Schedule",
                row.name,
                {
                    "custom_invoice_doctype": "",
                    "custom_invoice_name": ""
                },
                update_modified=False
            )

    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking Purchase Invoice {invoice_name} from Purchase Order {purchase_order_name}: {e!s}",
            title="Purchase Invoice Unlinking Error"
        )


def unlink_payment_request_from_schedule(doc, method=None):
    """
    Remove Payment Request link from Payment Schedule when PR is cancelled.
    This runs on_cancel of Payment Request.
    """
    # Only process if it's linked to a Purchase Order
    if doc.reference_doctype != "Purchase Order" or not doc.reference_name:
        return

    try:
        # Find Payment Schedule rows that link to this Payment Request
        schedule_rows = frappe.get_all(
            "Payment Schedule",
            filters={
                "parent": doc.reference_name,
                "parenttype": "Purchase Order",
                "custom_invoice_doctype": "Payment Request",
                "custom_invoice_name": doc.name
            },
            fields=["name", "idx"]
        )

        if not schedule_rows:
            return

        # Clear the links
        for row in schedule_rows:
            frappe.db.set_value(
                "Payment Schedule",
                row.name,
                {
                    "custom_invoice_doctype": "",
                    "custom_invoice_name": ""
                },
                update_modified=False
            )

        frappe.msgprint(
            _("Payment Request {0} unlinked from Payment Schedule").format(
                frappe.bold(doc.name)
            )
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error unlinking Payment Request {doc.name} from Purchase Order {doc.reference_name}: {e!s}",
            title="Payment Request Unlinking Error"
        )

