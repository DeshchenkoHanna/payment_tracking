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
            },
            {
                "fieldname": "custom_manual_payment_schedule",
                "label": "Manual Payment Amount",
                "fieldtype": "Check",
                "insert_after": "payment_schedule",
                "description": "Skip automatic recalculation of Payment Schedule amounts",
                "translatable": 0
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
        "Payment Request": [
            {
                "fieldname": "custom_due_date",
                "label": "Due Date",
                "fieldtype": "Date",
                "insert_after": "transaction_date"
            }
        ],
        "Payment Entry Reference": [
            {
                "fieldname": "custom_payment_schedule_idx",
                "label": "Payment Schedule Idx",
                "fieldtype": "Int",
                "read_only": 1,
                "hidden": 1,
                "insert_after": "payment_term"
            }
        ],
        "Payment Schedule": [
            {
                "fieldname": "custom_invoice_doctype",
                "label": "Invoice Doctype",
                "fieldtype": "Select",
                "options": "Payment Request\nSales Invoice\nPurchase Invoice",
                "read_only": 0,
                "allow_on_submit": 1,
                "insert_after": "outstanding"
            },
            {
                "fieldname": "custom_invoice_name",
                "label": "Invoice Name",
                "fieldtype": "Dynamic Link",
                "options": "custom_invoice_doctype",
                "read_only": 0,
                "allow_on_submit": 1,
                "insert_after": "custom_invoice_doctype"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)

def execute():
    """Execute field creation"""
    create_payment_tracking_fields()
