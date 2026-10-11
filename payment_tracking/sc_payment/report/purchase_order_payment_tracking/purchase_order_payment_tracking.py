# Copyright (c) 2026, SwissCluster and contributors
# For license information, please see license.txt
#
# Purchase Order Payment Tracking
# -------------------------------
# For each Purchase Order (filtered) lists every payment-schedule row with the payment
# that is connected to it, and ALSO surfaces every "Pay" payment of the order's
# supplier(s) -- including payments that reference the PO but aren't matched to a
# schedule row, and fully unallocated payments -- so unlinked payments are easy to spot.
# Every document column is a clickable Link / Dynamic Link.

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Purchase Order"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 90},
        {"label": _("PO Status"), "fieldname": "po_status", "fieldtype": "Data", "width": 120},
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 120},
        {"label": _("Row #"), "fieldname": "row", "fieldtype": "Int", "width": 60},
        {"label": _("Payment Term"), "fieldname": "payment_term", "fieldtype": "Data", "width": 130},
        {"label": _("Payment Amount"), "fieldname": "payment_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Paid Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Invoice Type"), "fieldname": "invoice_doctype", "fieldtype": "Data", "width": 110, "hidden": 1},
        {"label": _("Invoice"), "fieldname": "invoice_name", "fieldtype": "Dynamic Link", "options": "invoice_doctype", "width": 150},
        {"label": _("Payment Entry"), "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 160},
        {"label": _("PE Amount (party ccy)"), "fieldname": "pe_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"label": _("Purchase Invoice"), "fieldname": "purchase_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
        {"label": _("Connection"), "fieldname": "connection", "fieldtype": "Data", "width": 200},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80, "hidden": 1},
    ]


def get_data(filters):
    po_filters = {"docstatus": 1, "company": filters.company}
    if filters.get("supplier"):
        po_filters["supplier"] = filters.supplier
    if filters.get("purchase_order"):
        po_filters["name"] = filters.purchase_order
    if filters.get("from_date") and filters.get("to_date"):
        po_filters["transaction_date"] = ["between", [filters.from_date, filters.to_date]]

    pos = frappe.get_all(
        "Purchase Order", filters=po_filters,
        fields=["name", "supplier", "currency", "transaction_date", "status"],
        order_by="transaction_date, name",
    )

    po_cache = {p.name: p for p in pos}

    def po_meta(name):
        """(transaction_date, status) for any PO, cached -- also covers POs referenced by
        orphan payments that fall outside the filtered set."""
        if not name:
            return (None, None)
        p = po_cache.get(name)
        if p is None:
            p = frappe.db.get_value("Purchase Order", name, ["transaction_date", "status"], as_dict=True) or {}
            po_cache[name] = p
        return (p.get("transaction_date"), p.get("status"))

    acct_ccy_cache = {}

    def acct_ccy(account):
        """Currency of a GL account -- the currency a reference's allocated_amount is in."""
        if not account:
            return None
        if account not in acct_ccy_cache:
            acct_ccy_cache[account] = frappe.db.get_value("Account", account, "account_currency")
        return acct_ccy_cache[account]

    data = []
    shown_ref_rows = set()   # Payment Entry Reference.name already shown against a schedule row
    suppliers = set()

    for po in pos:
        suppliers.add(po.supplier)
        sched = frappe.get_all(
            "Payment Schedule",
            filters={"parent": po.name, "parenttype": "Purchase Order"},
            fields=["idx", "payment_term", "payment_amount", "paid_amount",
                    "custom_invoice_doctype", "custom_invoice_name"],
            order_by="idx",
        )
        for row in sched:
            pinv = row.custom_invoice_name if row.custom_invoice_doctype == "Purchase Invoice" else None
            pr_name = row.custom_invoice_name if row.custom_invoice_doctype == "Payment Request" else None
            base = {
                "purchase_order": po.name, "po_date": po.transaction_date, "po_status": po.status,
                "supplier": po.supplier, "row": row.idx,
                "payment_term": row.payment_term, "payment_amount": row.payment_amount,
                "paid_amount": row.paid_amount, "currency": po.currency,
                "invoice_doctype": row.custom_invoice_doctype, "invoice_name": row.custom_invoice_name,
                "purchase_invoice": pinv,
            }
            # Payment Entries connected to THIS schedule row:
            #   by idx  -> PE Reference to the PO with custom_payment_schedule_idx = row idx
            #   by PINV -> PE Reference to the row's Purchase Invoice (custom_invoice_name)
            #   by PR   -> PE Reference whose payment_request = the row's Payment Request
            #              (covers PEs referencing the PO with custom_payment_schedule_idx=0
            #               but carrying the row's Payment Request, e.g. APINV-*)
            conns = frappe.db.sql(
                """
                select per.name as ref_row, per.parent as pe, per.allocated_amount as amt
                from `tabPayment Entry Reference` per
                join `tabPayment Entry` pe on pe.name = per.parent
                where pe.docstatus = 1 and (
                    (per.reference_doctype = 'Purchase Order' and per.reference_name = %(po)s
                       and per.custom_payment_schedule_idx = %(idx)s)
                    or (%(pinv)s is not null and per.reference_doctype = 'Purchase Invoice'
                       and per.reference_name = %(pinv)s)
                    or (%(pr)s is not null and per.payment_request = %(pr)s)
                )
                """,
                {"po": po.name, "idx": row.idx, "pinv": pinv, "pr": pr_name}, as_dict=True,
            )
            if conns:
                for c in conns:
                    shown_ref_rows.add(c.ref_row)
                    data.append({**base, "payment_entry": c.pe, "pe_amount": c.amt,
                                 "connection": _("Paid (row matched)")})
            else:
                data.append({**base, "payment_entry": None, "pe_amount": None,
                             "connection": _("Scheduled / unpaid")})

    # ---- all Pay payments of the in-scope suppliers, even if not matched to a row ----
    if suppliers:
        pe_filters = {"payment_type": "Pay", "party_type": "Supplier",
                      "party": ["in", list(suppliers)], "company": filters.company, "docstatus": 1}
        if filters.get("from_date") and filters.get("to_date"):
            pe_filters["posting_date"] = ["between", [filters.from_date, filters.to_date]]
        pays = frappe.get_all(
            "Payment Entry", filters=pe_filters,
            fields=["name", "party", "paid_to_account_currency", "unallocated_amount"],
            order_by="posting_date, name",
        )
        refs_by_pe = {}
        pay_names = [p.name for p in pays]
        if pay_names:
            for r in frappe.get_all(
                "Payment Entry Reference", filters={"parent": ["in", pay_names]},
                fields=["name", "parent", "reference_doctype", "reference_name", "allocated_amount", "account"],
            ):
                refs_by_pe.setdefault(r.parent, []).append(r)

        for pe in pays:
            refs = refs_by_pe.get(pe.name, [])
            if not refs:
                # fully unallocated payment -- needs linking
                data.append({"purchase_order": None, "supplier": pe.party, "row": None,
                             "payment_entry": pe.name,
                             "pe_amount": pe.unallocated_amount,
                             "connection": _("Unallocated payment"),
                             "currency": pe.paid_to_account_currency})
                continue
            for r in refs:
                if r.name in shown_ref_rows:
                    continue   # already shown against a schedule row
                po_ref = r.reference_name if r.reference_doctype == "Purchase Order" else None
                pd, ps = po_meta(po_ref)
                data.append({
                    "purchase_order": po_ref, "po_date": pd, "po_status": ps,
                    "supplier": pe.party, "row": None,
                    "invoice_doctype": r.reference_doctype, "invoice_name": r.reference_name,
                    "purchase_invoice": r.reference_name if r.reference_doctype == "Purchase Invoice" else None,
                    "payment_entry": pe.name, "pe_amount": r.allocated_amount,
                    "connection": _("Payment not matched to a schedule row"),
                    "currency": acct_ccy(r.account) or pe.paid_to_account_currency,
                })

    return data
