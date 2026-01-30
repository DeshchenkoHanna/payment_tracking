"""
Override Payment Entry to fix update_payment_schedule bug.

ERPNext uses (payment_term, parent) as key to update Payment Schedule rows,
which causes paid_amount to be written to ALL rows sharing the same payment_term.

Fix: include idx in the key so each row is updated individually.
"""

import frappe
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.utils import flt
from frappe.utils.data import fmt_money

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class CustomPaymentEntry(PaymentEntry):

    def validate_duplicate_entry(self):
        """
        Override to allow multiple references to the same invoice
        when they have different custom_payment_schedule_idx values.

        Original key: (reference_doctype, reference_name, payment_term, payment_request)
        New key adds: custom_payment_schedule_idx
        """
        reference_names = set()
        for d in self.get("references"):
            # Include custom_payment_schedule_idx in the key to allow
            # multiple rows for same invoice with different payment schedule rows
            key = (
                d.reference_doctype,
                d.reference_name,
                d.payment_term,
                d.payment_request,
                d.get("custom_payment_schedule_idx") or 0
            )
            if key in reference_names:
                frappe.throw(
                    _("Row #{0}: Duplicate entry in References {1} {2}").format(
                        d.idx, d.reference_doctype, d.reference_name
                    )
                )

            reference_names.add(key)

    def update_payment_schedule(self, cancel=0):
        invoice_payment_amount_map = {}
        invoice_paid_amount_map = {}

        for ref in self.get("references"):
            if not ref.payment_term or not ref.reference_name:
                continue

            # Use idx from custom field to uniquely identify the Payment Schedule row
            schedule_idx = ref.get("custom_payment_schedule_idx") or 0
            key = (ref.payment_term, ref.reference_name, ref.reference_doctype, schedule_idx)
            invoice_payment_amount_map.setdefault(key, 0.0)
            invoice_payment_amount_map[key] += ref.allocated_amount

            if not invoice_paid_amount_map.get(key):
                payment_schedule = frappe.get_all(
                    "Payment Schedule",
                    filters={"parent": ref.reference_name},
                    fields=[
                        "idx",
                        "paid_amount",
                        "payment_amount",
                        "payment_term",
                        "discount",
                        "outstanding",
                        "discount_type",
                    ],
                )
                for term in payment_schedule:
                    invoice_key = (term.payment_term, ref.reference_name, ref.reference_doctype, term.idx)
                    invoice_paid_amount_map.setdefault(invoice_key, {})
                    invoice_paid_amount_map[invoice_key]["outstanding"] = term.outstanding
                    if not (term.discount_type and term.discount):
                        continue

                    if term.discount_type == "Percentage":
                        invoice_paid_amount_map[invoice_key]["discounted_amt"] = ref.total_amount * (
                            term.discount / 100
                        )
                    else:
                        invoice_paid_amount_map[invoice_key]["discounted_amt"] = term.discount

        for idx, (key, allocated_amount) in enumerate(invoice_payment_amount_map.items(), 1):
            if not invoice_paid_amount_map.get(key):
                frappe.throw(_("Payment term {0} not used in {1}").format(key[0], key[1]))

            allocated_amount = self.get_allocated_amount_in_transaction_currency(
                allocated_amount, key[2], key[1]
            )

            outstanding = flt(invoice_paid_amount_map.get(key, {}).get("outstanding"))
            discounted_amt = flt(invoice_paid_amount_map.get(key, {}).get("discounted_amt"))

            conversion_rate = frappe.db.get_value(key[2], {"name": key[1]}, "conversion_rate")
            base_paid_amount_precision = get_field_precision(
                frappe.get_meta("Payment Schedule").get_field("base_paid_amount")
            )
            base_outstanding_precision = get_field_precision(
                frappe.get_meta("Payment Schedule").get_field("base_outstanding")
            )

            base_paid_amount = flt(
                (allocated_amount - discounted_amt) * conversion_rate, base_paid_amount_precision
            )
            base_outstanding = flt(allocated_amount * conversion_rate, base_outstanding_precision)

            schedule_idx = key[3]

            if schedule_idx:
                # Use idx to target the exact row
                where_clause = "WHERE parent = %s and payment_term = %s and idx = %s"
                where_params_cancel = (
                    allocated_amount - discounted_amt,
                    base_paid_amount,
                    discounted_amt,
                    allocated_amount,
                    base_outstanding,
                    key[1],
                    key[0],
                    schedule_idx,
                )
                where_params_submit = where_params_cancel
            else:
                # Fallback to original behavior when idx is not available
                where_clause = "WHERE parent = %s and payment_term = %s"
                where_params_cancel = (
                    allocated_amount - discounted_amt,
                    base_paid_amount,
                    discounted_amt,
                    allocated_amount,
                    base_outstanding,
                    key[1],
                    key[0],
                )
                where_params_submit = where_params_cancel

            if cancel:
                frappe.db.sql(
                    f"""
                    UPDATE `tabPayment Schedule`
                    SET
                        paid_amount = `paid_amount` - %s,
                        base_paid_amount = `base_paid_amount` - %s,
                        discounted_amount = `discounted_amount` - %s,
                        outstanding = `outstanding` + %s,
                        base_outstanding = `base_outstanding` - %s
                    {where_clause}""",
                    where_params_cancel,
                )
            else:
                if allocated_amount > outstanding:
                    frappe.throw(
                        _("Row #{0}: Cannot allocate more than {1} against payment term {2}").format(
                            idx, fmt_money(outstanding), key[0]
                        )
                    )

                if allocated_amount and outstanding:
                    frappe.db.sql(
                        f"""
                        UPDATE `tabPayment Schedule`
                        SET
                            paid_amount = `paid_amount` + %s,
                            base_paid_amount = `base_paid_amount` + %s,
                            discounted_amount = `discounted_amount` + %s,
                            outstanding = `outstanding` - %s,
                            base_outstanding = `base_outstanding` - %s
                        {where_clause}""",
                        where_params_submit,
                    )
