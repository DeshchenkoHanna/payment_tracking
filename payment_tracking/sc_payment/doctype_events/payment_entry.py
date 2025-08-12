# payment_tracking/payment_tracking/sc_payment/doctype_events/payment_entry.py
import frappe
from frappe import _

def update_total_payments(doc, method=None):
    """Update total payment amounts in related documents when Payment Entry changes"""
    
    if not doc.references:
        return
        
    # Get all unique reference documents
    reference_docs = {}
    
    for ref in doc.references:
        if ref.reference_doctype in ["Purchase Order", "Sales Order", "Purchase Invoice", "Sales Invoice"]:
            key = f"{ref.reference_doctype}::{ref.reference_name}"
            if key not in reference_docs:
                reference_docs[key] = {
                    "doctype": ref.reference_doctype,
                    "name": ref.reference_name
                }
    
    # Update total payments for each referenced document
    for ref_key, ref_data in reference_docs.items():
        try:
            update_document_total_payment(ref_data["doctype"], ref_data["name"])
        except Exception as e:
            frappe.log_error(
                f"Error updating total payment for {ref_data['doctype']} {ref_data['name']}: {str(e)}",
                "Payment Tracking Error"
            )

def update_document_total_payment(doctype, docname):
    """Calculate and update total payment for a specific document"""
    
    # Get all payment entries related to this document
    payment_entries = frappe.db.sql("""
        SELECT 
            pe.name,
            pe.docstatus,
            per.allocated_amount,
            pe.payment_type
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per ON pe.name = per.parent
        WHERE 
            per.reference_doctype = %(doctype)s 
            AND per.reference_name = %(docname)s
            AND pe.docstatus = 1
    """, {
        "doctype": doctype,
        "docname": docname
    }, as_dict=True)
    
    total_payment = 0
    
    for pe in payment_entries:
        if pe.payment_type == "Receive":
            total_payment += pe.allocated_amount or 0
        elif pe.payment_type == "Pay":
            total_payment += pe.allocated_amount or 0
    
    # Update the document
    frappe.db.set_value(
        doctype, 
        docname, 
        "custom_total_payment", 
        total_payment,
        update_modified=False
    )
    
    frappe.db.commit()

@frappe.whitelist()
def recalculate_all_payments():
    """Utility function to recalculate all payment totals"""
    
    doctypes = ["Purchase Order", "Sales Order", "Purchase Invoice", "Sales Invoice"]
    
    for doctype in doctypes:
        documents = frappe.get_all(doctype, fields=["name"])
        
        for doc in documents:
            try:
                update_document_total_payment(doctype, doc.name)
            except Exception as e:
                frappe.log_error(
                    f"Error recalculating {doctype} {doc.name}: {str(e)}",
                    "Payment Tracking Recalculation Error"
                )
    
    return _("Payment totals recalculated successfully")