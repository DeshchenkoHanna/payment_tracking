"""
Patch: Set allow_on_submit for Payment Schedule custom fields

This patch enables 'allow_on_submit' for custom_invoice_doctype and custom_invoice_name
fields in Payment Schedule child table, allowing them to be updated after parent
document (Purchase Order/Sales Order) is submitted.

Execution: Runs automatically during `bench migrate`
"""

import frappe
from frappe import _


def execute():
    """
    Enable allow_on_submit for Payment Schedule custom fields
    """
    frappe.logger().info("Setting allow_on_submit for Payment Schedule custom fields...")

    # Update custom_invoice_doctype field
    if frappe.db.exists("Custom Field", "Payment Schedule-custom_invoice_doctype"):
        frappe.db.set_value(
            "Custom Field",
            "Payment Schedule-custom_invoice_doctype",
            "allow_on_submit",
            1
        )
        frappe.logger().info("Updated custom_invoice_doctype: allow_on_submit = 1")

    # Update custom_invoice_name field
    if frappe.db.exists("Custom Field", "Payment Schedule-custom_invoice_name"):
        frappe.db.set_value(
            "Custom Field",
            "Payment Schedule-custom_invoice_name",
            "allow_on_submit",
            1
        )
        frappe.logger().info("Updated custom_invoice_name: allow_on_submit = 1")

    frappe.db.commit()

    print("✅ Payment Tracking: Payment Schedule custom fields now allow updates on submit")
