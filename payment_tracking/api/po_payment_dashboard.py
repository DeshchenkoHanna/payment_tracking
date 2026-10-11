# Copyright (c) 2026, SwissCluster and contributors
# For license information, please see license.txt
#
# Server data for the "PO Payment Tracking" dashboard page.
# Groups by Purchase Order and places each connected payment on the schedule row it
# corresponds to, matched by priority:
#   1) custom_payment_schedule_idx == row idx
#   2) the row's Payment Request (custom_invoice is a PR, PE reference payment_request = it)
#   3) equal amount (row payment_amount == reference allocated_amount)
# Connected payments that don't land on a row are listed under the PO ("extra"); the
# supplier's payments that reference nothing (or other docs) are listed as "unmatched".

import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_data(company, supplier=None, purchase_order=None, from_date=None, to_date=None):
    po_filters = {"docstatus": 1, "company": company}
    if supplier:
        po_filters["supplier"] = supplier
    if purchase_order:
        po_filters["name"] = purchase_order
    if from_date and to_date:
        po_filters["transaction_date"] = ["between", [from_date, to_date]]

    pos = frappe.get_all(
        "Purchase Order", filters=po_filters,
        fields=["name", "supplier", "supplier_name", "currency", "transaction_date", "status",
                "grand_total", "rounded_total"],
        order_by="transaction_date, name",
    )

    pinv_cache, ccy_cache = {}, {}

    def _pinv(p):
        if not p:
            return (None, None)
        if p not in pinv_cache:
            d = frappe.db.get_value("Purchase Invoice", p, ["grand_total", "posting_date"], as_dict=True) or {}
            pinv_cache[p] = (d.get("grand_total"), d.get("posting_date"))
        return pinv_cache[p]

    def pinv_amount(p):
        return _pinv(p)[0]

    def pinv_date(p):
        return _pinv(p)[1]

    def acct_ccy(a):
        if not a:
            return None
        if a not in ccy_cache:
            ccy_cache[a] = frappe.db.get_value("Account", a, "account_currency")
        return ccy_cache[a]

    groups = []
    used_refs = set()   # Payment Entry Reference .name shown against a PO (row or extra)
    suppliers = set()

    for po in pos:
        suppliers.add(po.supplier)
        sched = frappe.get_all(
            "Payment Schedule",
            filters={"parent": po.name, "parenttype": "Purchase Order"},
            fields=["idx", "payment_term", "payment_amount", "custom_invoice_doctype", "custom_invoice_name"],
            order_by="idx",
        )
        # every payment connected to this PO: direct PO references + references to the PO's invoices
        refs = frappe.db.sql(
            """
            select per.name as ref, per.parent as pe, per.allocated_amount as amt,
                   per.custom_payment_schedule_idx as idx, per.payment_request as pr,
                   per.reference_doctype as rdt, per.reference_name as rname, per.account as account,
                   pe.posting_date as pdate
            from `tabPayment Entry Reference` per
            join `tabPayment Entry` pe on pe.name = per.parent
            where pe.docstatus = 1 and (
                (per.reference_doctype = 'Purchase Order' and per.reference_name = %(po)s)
                or (per.reference_doctype = 'Purchase Invoice' and per.reference_name in
                    (select pii.parent from `tabPurchase Invoice Item` pii where pii.purchase_order = %(po)s))
            )
            order by pe.posting_date, per.idx
            """,
            {"po": po.name}, as_dict=True,
        )

        rows = []
        for s in sched:
            rows.append({
                "row": s.idx, "payment_term": s.payment_term, "payment_amount": s.payment_amount,
                "invoice_doctype": s.custom_invoice_doctype, "invoice_name": s.custom_invoice_name,
                "_pr": s.custom_invoice_name if s.custom_invoice_doctype == "Payment Request" else None,
                "payments": [], "paid_sum": 0.0,
            })

        placed = set()

        def place(ref, row):
            # a term row can hold several payments (e.g. partial payments of one milestone)
            row["payments"].append({
                "payment_entry": ref["pe"], "pe_amount": ref["amt"],
                "currency": acct_ccy(ref["account"]),
            })
            row["paid_sum"] += flt(ref["amt"])
            ref["_term"] = row["payment_term"]
            placed.add(ref["ref"])
            used_refs.add(ref["ref"])

        # 1) by schedule-idx
        for ref in refs:
            if ref["ref"] in placed or not ref["idx"]:
                continue
            for row in rows:
                if row["row"] == ref["idx"]:
                    place(ref, row); break
        # 2) by the row's Payment Request
        for ref in refs:
            if ref["ref"] in placed or not ref["pr"]:
                continue
            for row in rows:
                if row["_pr"] and row["_pr"] == ref["pr"]:
                    place(ref, row); break
        # 3) exact amount into a not-yet-paid row
        for ref in refs:
            if ref["ref"] in placed:
                continue
            for row in rows:
                if row["paid_sum"] == 0 and flt(row["payment_amount"]) == flt(ref["amt"]):
                    place(ref, row); break
        # 4) fill: drop into the first row that still has room, so several partial
        #    payments of one term collect on that term's row
        for ref in refs:
            if ref["ref"] in placed:
                continue
            amt = flt(ref["amt"])
            target = None
            for row in rows:
                remaining = flt(row["payment_amount"]) - row["paid_sum"]
                if remaining > 0.01 and remaining + 0.01 >= amt:
                    target = row; break
            if target is None:
                for row in rows:
                    if row["paid_sum"] < flt(row["payment_amount"]) - 0.01:
                        target = row; break
            if target is not None:
                place(ref, target)

        for row in rows:
            row.pop("_pr", None)
            row.pop("paid_sum", None)

        # payments that didn't fit any term row -> shown under the PO
        extra = []
        for ref in refs:
            if ref["ref"] in placed:
                continue
            used_refs.add(ref["ref"])
            extra.append({
                "invoice_doctype": ref["rdt"], "invoice_name": ref["rname"],
                "payment_entry": ref["pe"], "pe_amount": ref["amt"],
                "currency": acct_ccy(ref["account"]),
            })

        # summary totals for the PO head line
        paid_total = sum(flt(r["amt"]) for r in refs)
        pinv_names = frappe.db.sql_list(
            """select distinct pii.parent from `tabPurchase Invoice Item` pii
               join `tabPurchase Invoice` pi on pi.name = pii.parent
               where pii.purchase_order = %s and pi.docstatus = 1""", po.name)
        invoiced_total = sum(flt(pinv_amount(p)) for p in pinv_names)

        # the PO's invoices (Date, Invoice, Amount)
        invoices = []
        for p in pinv_names:
            amt, dt = _pinv(p)
            invoices.append({"date": dt, "invoice": p, "amount": amt})
        invoices.sort(key=lambda x: (str(x["date"]) if x["date"] else ""))

        # the PO's payment references (Date, Payment, Amount, Reference, PR, Payment term)
        payments = [{
            "date": ref.get("pdate"), "payment": ref["pe"], "amount": ref["amt"],
            "reference_doctype": ref["rdt"], "reference_name": ref["rname"],
            "pr": ref["pr"], "payment_term": ref.get("_term"),
        } for ref in refs]

        groups.append({
            "purchase_order": po.name, "po_date": po.transaction_date, "po_status": po.status,
            "supplier": po.supplier, "supplier_name": po.supplier_name, "currency": po.currency,
            "ordered": po.rounded_total or po.grand_total, "paid": paid_total, "invoiced": invoiced_total,
            "invoices": invoices, "payments": payments,
            "schedule": rows, "extra": extra,
        })

    # supplier payments not shown against any PO (references to other docs, or unallocated)
    unmatched = []
    if suppliers:
        pe_filters = {"payment_type": "Pay", "party_type": "Supplier",
                      "party": ["in", list(suppliers)], "company": company, "docstatus": 1}
        if from_date and to_date:
            pe_filters["posting_date"] = ["between", [from_date, to_date]]
        pays = frappe.get_all("Payment Entry", filters=pe_filters,
            fields=["name", "party", "party_name", "posting_date", "paid_to_account_currency", "unallocated_amount"],
            order_by="posting_date, name")
        refs_by_pe = {}
        pay_names = [p.name for p in pays]
        if pay_names:
            for r in frappe.get_all("Payment Entry Reference", filters={"parent": ["in", pay_names]},
                    fields=["name", "parent", "reference_doctype", "reference_name", "allocated_amount", "account"]):
                refs_by_pe.setdefault(r.parent, []).append(r)
        for pe in pays:
            prs = refs_by_pe.get(pe.name, [])
            if not prs:
                unmatched.append({"purchase_order": None, "row": None, "payment_entry": pe.name,
                                  "supplier": pe.party, "supplier_name": pe.party_name, "pe_date": pe.posting_date,
                                  "no_ref": 1,
                                  "pe_amount": pe.unallocated_amount, "currency": pe.paid_to_account_currency})
                continue
            for r in prs:
                if r.name in used_refs:
                    continue
                pinv = r.reference_name if r.reference_doctype == "Purchase Invoice" else None
                unmatched.append({
                    "purchase_order": r.reference_name if r.reference_doctype == "Purchase Order" else None,
                    "row": None, "invoice_doctype": r.reference_doctype, "invoice_name": r.reference_name,
                    "purchase_invoice": pinv, "pinv_amount": pinv_amount(pinv), "pinv_date": pinv_date(pinv),
                    "supplier": pe.party, "supplier_name": pe.party_name, "pe_date": pe.posting_date,
                    "payment_entry": pe.name, "pe_amount": r.allocated_amount, "currency": acct_ccy(r.account),
                })

    return {"groups": groups, "unmatched": unmatched}
