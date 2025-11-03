"""
Patch: Update Payment Tracking Custom Fields

This patch ensures all custom fields are created/updated with the latest definitions.
Useful when:
- Adding new custom fields
- Modifying existing field properties (read_only, labels, etc.)
- Updating app on existing installations

Execution: Runs automatically during `bench migrate`
"""

import frappe
from frappe import _


def execute():
    """
    Main patch execution function
    This runs once per site when patch is applied
    """
    frappe.logger().info("Starting Payment Tracking custom fields update...")

    # Import custom fields creation
    from payment_tracking.sc_payment.custom_fields import create_payment_tracking_fields

    # Create/update all custom fields
    # The update=True parameter ensures existing fields are updated, not duplicated
    create_payment_tracking_fields()

    frappe.logger().info("Payment Tracking custom fields updated successfully")
    print("✅ Payment Tracking: Custom fields updated successfully")
