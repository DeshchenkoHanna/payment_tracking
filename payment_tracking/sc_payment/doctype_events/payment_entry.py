# payment_tracking/payment_tracking/sc_payment/doctype_events/payment_entry.py
import frappe
from frappe import _
# import debugpy


def populate_payment_schedule_idx(doc, method=None):
    """
    Before submit: set custom_payment_schedule_idx on each Payment Entry Reference row.
    This maps each reference to the correct Payment Schedule row by idx,
    fixing the bug where duplicate payment_term values cause all matching rows to be updated.
    """
    for ref in doc.get("references"):
        if not ref.payment_term or not ref.reference_name:
            continue

        if ref.get("custom_payment_schedule_idx"):
            continue

        # Find the matching Payment Schedule row by payment_term
        # If multiple rows share the same payment_term, pick the first one
        # that hasn't already been assigned to another reference
        assigned_idxs = {
            r.get("custom_payment_schedule_idx")
            for r in doc.get("references")
            if r.get("custom_payment_schedule_idx")
            and r.reference_name == ref.reference_name
            and r.payment_term == ref.payment_term
        }

        schedule_rows = frappe.get_all(
            "Payment Schedule",
            filters={"parent": ref.reference_name, "payment_term": ref.payment_term},
            fields=["idx"],
            order_by="idx asc",
        )

        for row in schedule_rows:
            if row.idx not in assigned_idxs:
                ref.custom_payment_schedule_idx = row.idx
                break


def update_total_payments(doc, method=None):
    """Update total payment amounts in related documents when Payment Entry changes"""

    if not doc.references:
        return
        
    # Get all unique reference documents (direct references)
    reference_docs = {}
    for ref in doc.references:
        if ref.reference_doctype in ["Purchase Order", "Sales Order", "Purchase Invoice", "Sales Invoice"]:
            key = f"{ref.reference_doctype}::{ref.reference_name}"
            if key not in reference_docs:
                reference_docs[key] = {
                    "doctype": ref.reference_doctype,
                    "name": ref.reference_name
                }
                
    # Find indirect references (Orders linked to Invoices)
    indirect_docs = find_indirect_references(reference_docs)
    
    # Combine direct and indirect references
    all_docs = {**reference_docs, **indirect_docs}
    
    # Update total payments for each referenced document
    for _ref_key, ref_data in all_docs.items():
        try:
            update_document_total_payment(ref_data["doctype"], ref_data["name"])
        except Exception as e:
            error_msg = f"Error updating total payment for {ref_data['doctype']} {ref_data['name']}: {e!s}"
            frappe.log_error(error_msg, "Payment Tracking Error")

def find_indirect_references(direct_refs):
    """Find Orders that are indirectly referenced through Invoices"""

    indirect_docs = {}

    for _key, ref_data in direct_refs.items():
        doctype = ref_data["doctype"]
        docname = ref_data["name"]
        
        # If Payment Entry references an Invoice, find the related Order(s)
        if doctype == "Sales Invoice":
            # Get Sales Orders linked to this Sales Invoice
            linked_orders = frappe.db.sql("""
                SELECT DISTINCT si_item.sales_order as order_name
                FROM `tabSales Invoice Item` si_item
                WHERE si_item.parent = %(invoice_name)s 
                AND si_item.sales_order IS NOT NULL
                AND si_item.sales_order != ''
            """, {"invoice_name": docname}, as_dict=True)
            
            for order in linked_orders:
                if order.order_name:
                    key = f"Sales Order::{order.order_name}"
                    if key not in indirect_docs:
                        indirect_docs[key] = {
                            "doctype": "Sales Order",
                            "name": order.order_name
                        }
        
        elif doctype == "Purchase Invoice":
            # Get Purchase Orders linked to this Purchase Invoice
            linked_orders = frappe.db.sql("""
                SELECT DISTINCT pi_item.purchase_order as order_name
                FROM `tabPurchase Invoice Item` pi_item
                WHERE pi_item.parent = %(invoice_name)s 
                AND pi_item.purchase_order IS NOT NULL
                AND pi_item.purchase_order != ''
            """, {"invoice_name": docname}, as_dict=True)
            
            for order in linked_orders:
                if order.order_name:
                    key = f"Purchase Order::{order.order_name}"
                    if key not in indirect_docs:
                        indirect_docs[key] = {
                            "doctype": "Purchase Order",
                            "name": order.order_name
                        }
        
        # If Payment Entry references an Order, find related Invoices
        elif doctype == "Sales Order":
            # Get Sales Invoices linked to this Sales Order
            linked_invoices = frappe.db.sql("""
                SELECT DISTINCT si_item.parent as invoice_name
                FROM `tabSales Invoice Item` si_item
                WHERE si_item.sales_order = %(order_name)s
                AND si_item.parent IS NOT NULL
                AND si_item.parent != ''
            """, {"order_name": docname}, as_dict=True)
            
            for invoice in linked_invoices:
                if invoice.invoice_name:
                    key = f"Sales Invoice::{invoice.invoice_name}"
                    if key not in indirect_docs:
                        indirect_docs[key] = {
                            "doctype": "Sales Invoice",
                            "name": invoice.invoice_name
                        }
        
        elif doctype == "Purchase Order":
            # Get Purchase Invoices linked to this Purchase Order
            linked_invoices = frappe.db.sql("""
                SELECT DISTINCT pi_item.parent as invoice_name
                FROM `tabPurchase Invoice Item` pi_item
                WHERE pi_item.purchase_order = %(order_name)s
                AND pi_item.parent IS NOT NULL
                AND pi_item.parent != ''
            """, {"order_name": docname}, as_dict=True)
            
            for invoice in linked_invoices:
                if invoice.invoice_name:
                    key = f"Purchase Invoice::{invoice.invoice_name}"
                    if key not in indirect_docs:
                        indirect_docs[key] = {
                            "doctype": "Purchase Invoice",
                            "name": invoice.invoice_name
                        }
    
    return indirect_docs

def update_document_total_payment(doctype, docname):
    """Calculate and update total payment for a specific document"""
    
    # Get direct payments to this document
    direct_payments = frappe.db.sql("""
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
    
    
    # Get indirect payments (for Orders through related Invoices)
    indirect_payments = []
    if doctype == "Sales Order":
        # Get payments to Sales Invoices linked to this Sales Order
        indirect_payments = frappe.db.sql("""
            SELECT DISTINCT
                pe.name,
                pe.docstatus,
                per.allocated_amount,
                pe.payment_type
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per ON pe.name = per.parent
            INNER JOIN `tabSales Invoice Item` si_item ON per.reference_name = si_item.parent
            WHERE 
                per.reference_doctype = 'Sales Invoice'
                AND si_item.sales_order = %(docname)s
                AND pe.docstatus = 1
        """, {"docname": docname}, as_dict=True)
        
    elif doctype == "Purchase Order":
        # Get payments to Purchase Invoices linked to this Purchase Order
        indirect_payments = frappe.db.sql("""
            SELECT DISTINCT
                pe.name,
                pe.docstatus,
                per.allocated_amount,
                pe.payment_type
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per ON pe.name = per.parent
            INNER JOIN `tabPurchase Invoice Item` pi_item ON per.reference_name = pi_item.parent
            WHERE 
                per.reference_doctype = 'Purchase Invoice'
                AND pi_item.purchase_order = %(docname)s
                AND pe.docstatus = 1
        """, {"docname": docname}, as_dict=True)
    
    
    # Combine direct and indirect payments
    all_payments = direct_payments + indirect_payments
    
    total_payment = 0
    
    # Calculate total from all payment entries
    for pe in all_payments:
        amount = pe.allocated_amount or 0
        if pe.payment_type in ["Receive", "Pay"]:
            total_payment += amount
    
    # Check if the custom field exists
    if not frappe.db.has_column(doctype, "custom_total_payment"):
        frappe.throw(f"Custom field 'custom_total_payment' not found in {doctype}. Please reinstall the app.")
        return
    
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
                    f"Error recalculating {doctype} {doc.name}: {e!s}",
                    "Payment Tracking Recalculation Error"
                )
    
    return _("Payment totals recalculated successfully")


