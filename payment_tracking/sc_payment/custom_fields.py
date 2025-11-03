# payment_tracking/payment_tracking/custom_fields.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_payment_tracking_fields():
    """Create custom fields for tracking total payments"""

    custom_fields = {
        "Purchase Order": [
            {
                "fieldname": "custom_total_payment",
                "label": "Total Payment",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "precision": 2,
                "insert_after": "rounded_total",
                "in_list_view": 1,
                "in_standard_filter": 1
            }
        ],
        "Sales Order": [
            {
                "fieldname": "custom_total_payment",
                "label": "Total Payment",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "precision": 2,
                "insert_after": "rounded_total",
                "in_list_view": 1,
                "in_standard_filter": 1
            }
        ],
        "Purchase Invoice": [
            {
                "fieldname": "custom_total_payment",
                "label": "Total Payment",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "precision": 2,
                "insert_after": "rounded_total",
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "custom_document_links_details",
                "label": "Document Links Details",
                "fieldtype": "HTML",
                "read_only": 1,
                "insert_after": "custom_total_payment"
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "custom_total_payment",
                "label": "Total Payment",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "precision": 2,
                "insert_after": "rounded_total",
                "in_list_view": 1,
                "in_standard_filter": 1
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "custom_document_links_details",
                "label": "Document Links Details",
                "fieldtype": "HTML",
                "read_only": 1,
                "insert_after": "total_allocated_amount"
            }
        ],
        "Payment Schedule": [
            {
                "fieldname": "custom_invoice_doctype",
                "label": "Invoice Doctype",
                "fieldtype": "Link",
                "options": "DocType",
                "read_only": 0,
                "insert_after": "outstanding"
            },
            {
                "fieldname": "custom_invoice_name",
                "label": "Invoice Name",
                "fieldtype": "Dynamic Link",
                "options": "custom_invoice_doctype",
                "read_only": 0,
                "insert_after": "custom_invoice_doctype"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)

def execute():
    """Execute field creation"""
    create_payment_tracking_fields()