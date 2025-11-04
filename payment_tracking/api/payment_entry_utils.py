import frappe

@frappe.whitelist()
def get_connected_orders_for_payment_entry(payment_entry_name):
    """
    Get connected Purchase Orders and Sales Orders for a Payment Entry
    through linked invoices.
    """
    try:
        # Get the Payment Entry document
        payment_entry = frappe.get_doc("Payment Entry", payment_entry_name)

        connected_orders = []

        # Process each reference in the Payment Entry
        for ref in payment_entry.references:
            if ref.reference_doctype == "Sales Invoice":
                # Get Sales Orders linked to this Sales Invoice
                sales_orders = frappe.db.sql("""
                    SELECT DISTINCT si_item.sales_order
                    FROM `tabSales Invoice Item` si_item
                    WHERE si_item.parent = %s
                    AND si_item.sales_order IS NOT NULL
                    AND si_item.sales_order != ''
                """, (ref.reference_name,), as_dict=True)

                for order in sales_orders:
                    if order.sales_order:
                        connected_orders.append({
                            "reference_doctype": "Sales Order",
                            "reference_name": order.sales_order
                        })

            elif ref.reference_doctype == "Purchase Invoice":
                # Get Purchase Orders linked to this Purchase Invoice
                purchase_orders = frappe.db.sql("""
                    SELECT DISTINCT pi_item.purchase_order
                    FROM `tabPurchase Invoice Item` pi_item
                    WHERE pi_item.parent = %s
                    AND pi_item.purchase_order IS NOT NULL
                    AND pi_item.purchase_order != ''
                """, (ref.reference_name,), as_dict=True)

                for order in purchase_orders:
                    if order.purchase_order:
                        connected_orders.append({
                            "reference_doctype": "Purchase Order",
                            "reference_name": order.purchase_order
                        })

        # Remove duplicates
        unique_orders = []
        seen = set()
        for order in connected_orders:
            key = f"{order['reference_doctype']}::{order['reference_name']}"
            if key not in seen:
                seen.add(key)
                unique_orders.append(order)

        return unique_orders

    except Exception as e:
        frappe.log_error(f"Error in get_connected_orders_for_payment_entry: {e!s}")
        return []

@frappe.whitelist()
def get_party_name(party_type, party_id):
    """
    Get party name safely
    """
    try:
        if party_type == "Customer":
            result = frappe.db.get_value("Customer", party_id, "customer_name")
        elif party_type == "Supplier":
            result = frappe.db.get_value("Supplier", party_id, "supplier_name")
        else:
            return party_id

        return result if result else party_id

    except Exception as e:
        frappe.log_error(f"Error in get_party_name: {e!s}")
        return party_id
