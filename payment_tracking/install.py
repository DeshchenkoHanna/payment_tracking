import frappe
from .sc_payment.custom_fields import create_payment_tracking_fields

def after_install():
    """Run after app installation"""
    try:
        # Create custom fields
        create_payment_tracking_fields()
        
        frappe.msgprint("Payment Tracking app installed successfully!")
        
    except Exception as e:
        frappe.log_error(f"Error during Payment Tracking installation: {str(e)}")
        frappe.throw(f"Installation failed: {str(e)}")