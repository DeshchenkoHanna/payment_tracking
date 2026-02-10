frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // Intercept cancel: confirm first, then unlink SI from SO Payment Schedule,
        // then proceed with server-side cancel (skipping duplicate confirm)
        if (frm.doc.docstatus === 1 && !frm._savecancel_patched) {
            frm.savecancel = function(btn, callback, on_error) {
                frappe.confirm(
                    __("Permanently Cancel {0}?", [frm.doc.name]),
                    function() {
                        frappe.call({
                            method: "payment_tracking.api.sales_order_utils.unlink_sales_invoice_before_cancel",
                            args: { invoice_name: frm.doc.name },
                            callback: function() {
                                // skip_confirm=true to avoid duplicate confirm dialog
                                frm._cancel(btn, callback, on_error, true);
                            }
                        });
                    },
                    function() {
                        frm.handle_save_fail(btn, on_error);
                    }
                );
            };
            frm._savecancel_patched = true;
        }
    }
});
