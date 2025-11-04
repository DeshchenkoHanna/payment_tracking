import frappe
from frappe import _

@frappe.whitelist()
def create_payment_request_from_so(sales_order, payment_amount, payment_term=None, due_date=None, payment_term_pos=None):
    """
    Create Payment Request from Sales Order
    """
    # Get Sales Order document
    so = frappe.get_doc("Sales Order", sales_order)

    # Create new Payment Request
    pr = frappe.new_doc("Payment Request")

    # Set basic fields
    pr.payment_request_type = "Inward"
    pr.party_type = "Customer"
    pr.party = so.customer
    pr.currency = so.currency
    pr.company = so.company

    # Set reference to Sales Order
    pr.reference_doctype = "Sales Order"
    pr.reference_name = so.name

    # Set amount
    pr.grand_total = float(payment_amount)

    # Set payment term position for linking back
    if payment_term_pos:
        pr.payment_term_pos = int(payment_term_pos)

    # Set payment term if provided
    if payment_term:
        pr.payment_term = payment_term

    # Set due date if provided
    if due_date:
        pr.schedule_date = due_date

    # Set mode of payment (optional, can be set by user later)
    pr.mode_of_payment = None

    # Insert the document
    pr.insert(ignore_permissions=True)

    return pr.name

@frappe.whitelist()
def can_create_payment_request(sales_order, payment_amount):
    """
    Validate if Payment Request can be created (ERPNext standard logic)
    Returns: {can_create: bool, error_message: str}
    """
    so = frappe.get_doc("Sales Order", sales_order)
    payment_amount = float(payment_amount)

    # Calculate available amount (same as ERPNext)
    grand_total = so.rounded_total or so.grand_total
    advance_paid = so.advance_paid or 0
    available_amount = grand_total - advance_paid

    # If already fully paid
    if available_amount <= 0:
        return {
            "can_create": False,
            "error_message": _("Payment Entry is already created")
        }

    # Get existing Payment Request amount (all submitted PRs)
    existing_pr_amount = get_existing_payment_request_amount(so)

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


def get_existing_payment_request_amount(sales_order_doc):
    """Get total amount of all submitted Payment Requests against Sales Order"""
    from frappe.query_builder import DocType
    from frappe.query_builder.functions import Sum

    PR = DocType("Payment Request")

    result = (
        frappe.qb.from_(PR)
        .select(Sum(PR.grand_total))
        .where(PR.reference_doctype == "Sales Order")
        .where(PR.reference_name == sales_order_doc.name)
        .where(PR.docstatus == 1)  # Only submitted
    ).run()

    return result[0][0] or 0


def link_payment_request_to_schedule(doc, method=None):
    """
    Link Payment Request back to Payment Schedule after it's created.
    This runs after_insert, so the document already has a name.
    """
    # Only process if it's linked to a Sales Order
    if doc.reference_doctype != "Sales Order" or not doc.reference_name:
        return

    # Check if Payment Request has payment_term_pos field
    if not hasattr(doc, 'payment_term_pos') or not doc.payment_term_pos:
        return

    try:
        # Get the Sales Order
        so = frappe.get_doc("Sales Order", doc.reference_name)

        # Find the payment schedule row by payment_term_pos (idx)
        for schedule_row in so.payment_schedule:
            if schedule_row.idx == doc.payment_term_pos:
                # Update the custom fields
                schedule_row.custom_invoice_doctype = "Payment Request"
                schedule_row.custom_invoice_name = doc.name
                break

        # Save the Sales Order (ignore permissions to allow system update)
        so.flags.ignore_validate_update_after_submit = True
        so.flags.ignore_permissions = True
        so.save()

        frappe.msgprint(
            _("Payment Request {0} linked to Payment Schedule row {1}").format(
                frappe.bold(doc.name),
                doc.payment_term_pos
            )
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error linking Payment Request {doc.name} to Sales Order {doc.reference_name}: {e!s}",
            title="Payment Request Linking Error"
        )


def link_sales_invoice_to_schedule(doc, method=None):
    """
    Link Sales Invoice back to Payment Schedule after it's created.
    Sales Invoice is always linked to the LAST row of Payment Schedule.
    This runs after_insert, so the document already has a name.
    """
    # Only process if it has items linked to a Sales Order
    if not doc.items:
        return

    # Get the first Sales Order reference from items
    sales_order_name = None
    for item in doc.items:
        if item.sales_order:
            sales_order_name = item.sales_order
            break

    if not sales_order_name:
        return

    try:
        # Get the Sales Order
        so = frappe.get_doc("Sales Order", sales_order_name)

        # Check if Sales Order has payment schedule
        if not so.payment_schedule or len(so.payment_schedule) == 0:
            return

        # Get the LAST row of payment schedule
        last_row = so.payment_schedule[-1]

        # Check if last row already has an invoice linked
        if last_row.custom_invoice_name:
            # Already linked, skip
            return

        # Link Sales Invoice to the last row
        last_row.custom_invoice_doctype = "Sales Invoice"
        last_row.custom_invoice_name = doc.name

        # Save the Sales Order (ignore permissions to allow system update)
        so.flags.ignore_validate_update_after_submit = True
        so.flags.ignore_permissions = True
        so.save()

        frappe.msgprint(
            _("Sales Invoice {0} linked to Payment Schedule last row").format(
                frappe.bold(doc.name)
            )
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error linking Sales Invoice {doc.name} to Sales Order {sales_order_name}: {e!s}",
            title="Sales Invoice Linking Error"
        )

