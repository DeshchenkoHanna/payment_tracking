import frappe


def mute_auto_email(doc, method=None):
    """
    Block the automatic payment e-mail that ERPNext sends when an Inward
    Payment Request is submitted.

    Registered on the ``validate`` event, NOT ``before_submit``: Frappe runs the
    controller's own ``before_submit`` (which enqueues the e-mail and creates the
    Communication) BEFORE any ``before_submit`` handler from hooks.py, so a hook on
    that event would fire too late. On submit, ``validate`` always runs first.

    Setting the persisted field (not only ``doc.flags.mute_email``) keeps the
    "Mute Email" checkbox on the form truthful. The manual "Resend Payment Email"
    button and Menu > Email are unaffected and keep working.
    """
    if doc.payment_request_type != "Inward":
        return

    if not doc.mute_email:
        doc.mute_email = 1

    doc.flags.mute_email = True


@frappe.whitelist()
def resend_payment_email_disabled(docname=None, *args, **kwargs):
    """
    Replaces erpnext's ``resend_payment_email`` via ``override_whitelisted_methods``.

    The standard "Resend Payment Email" button calls ``PaymentRequest.send_email``
    directly and ignores the Mute Email flag. The button stays visible, but clicking
    it now shows this message instead of sending anything.
    """
    frappe.throw(
        frappe._(
            "Automatic payment e-mails are disabled for Payment Requests. "
            "Use Menu > Email to send the request manually."
        ),
        title=frappe._("Payment Email Disabled"),
    )
