
frappe.ui.form.on('Purchase Invoice', {
    onload: function(frm) {
        update_supplier_po_details(frm);
    },

    refresh: function(frm) {

        // Define the copy function globally
        if (!window.copyDocumentLinksDetails) {
            window.copyDocumentLinksDetails = function(textToCopy) {
                if (!textToCopy) return;

                // Copy to clipboard with fallback
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(textToCopy).then(() => {
                        frappe.show_alert({
                            message: 'Document Links Details copied to clipboard',
                            indicator: 'green'
                        });
                    }).catch(() => {
                        fallbackCopyText(textToCopy);
                    });
                } else {
                    fallbackCopyText(textToCopy);
                }

                function fallbackCopyText(text) {
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-999999px';
                    textArea.style.top = '-999999px';
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();

                    try {
                        document.execCommand('copy');
                        frappe.show_alert({
                            message: 'Document Links Details copied to clipboard',
                            indicator: 'green'
                        });
                    } catch (err) {
                        frappe.show_alert({
                            message: 'Failed to copy to clipboard',
                            indicator: 'red'
                        });
                    }

                    document.body.removeChild(textArea);
                }
            };
        }

        update_supplier_po_details(frm);
    },

    supplier: function(frm) {
        update_supplier_po_details(frm);
    },

    items_on_form_rendered: function(frm) {
        update_supplier_po_details(frm);
    }
});

function update_supplier_po_details(frm) {

    if (!frm.doc.supplier) {
        frm.set_value('custom_document_links_details', '');
        return;
    }

    // Get supplier name
    frappe.db.get_value('Supplier', frm.doc.supplier, 'supplier_name')
        .then(r => {
            if (r.message) {
                const supplier_name = r.message.supplier_name;
                build_po_details_html(frm, frm.doc.supplier, supplier_name);
            }
        })
        .catch(err => {
            console.error('Error fetching supplier:', err);
        });
}

function build_po_details_html(frm, supplier_id, supplier_name) {

    // Get unique purchase orders from items
    const purchase_orders = [...new Set(
        frm.doc.items
            ?.filter(item => item.purchase_order)
            ?.map(item => item.purchase_order) || []
    )];

    // Get Payment Requests first, then build complete HTML
    get_payment_requests(frm.doc.name, function(payment_requests) {
        if (purchase_orders.length === 0) {
            // No PO, just show supplier info
            build_complete_supplier_html(supplier_id, supplier_name, frm.doc.name, [], payment_requests, frm);
            return;
        }

        // Build complete HTML with PO and PR
        build_complete_supplier_html(supplier_id, supplier_name, frm.doc.name, purchase_orders, payment_requests, frm);
    });
}

function build_complete_supplier_html(supplier_id, supplier_name, invoice_name, purchase_orders, payment_requests, frm) {
    const supplier_text = supplier_id;
    const invoice_text = invoice_name;

    // Build PO links
    let po_html = '';
    if (purchase_orders && purchase_orders.length > 0) {
        const po_links = purchase_orders.map(po =>
            `<a href="/app/purchase-order/${po}" target="_blank" class="badge-link">${po}</a>`
        ).join(', ');
        po_html = ` / ${po_links}`;
    }

    // Build Payment Request links
    let pr_html = '';
    if (payment_requests && payment_requests.length > 0) {
        const pr_links = payment_requests.map(pr =>
            `<a href="/app/payment-request/${pr.name}" target="_blank" style="text-decoration: underline;">${pr.name}</a>`
        ).join(', ');
        pr_html = ` / ${pr_links}`;
    }

    // Create plain text for copying
    let copyText = `${supplier_text} ${supplier_name}`;
    if (purchase_orders && purchase_orders.length > 0) {
        copyText += ` / ${purchase_orders.join(', ')}`;
    }
    copyText += ` / ${invoice_text}`;
    if (payment_requests && payment_requests.length > 0) {
        copyText += ` / ${payment_requests.map(pr => pr.name).join(', ')}`;
    }

    const html = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 8px; background: #f8f9fa; border-radius: 8px; position: relative;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <button class="btn icon-btn" onclick="copyDocumentLinksDetails('${copyText}')" onmouseover="this.classList.add('btn-default')" onmouseout="this.classList.remove('btn-default')">
                    <svg class="es-icon es-line  icon-sm" style="" aria-hidden="true">
                        <use class="" href="#es-line-copy-light"></use>
                    </svg>
                </button>
                <span style="font-weight: 500;">${supplier_text}</span>
                <span>${supplier_name}</span>
                <span>${po_html} /</span>
                <span>${invoice_text}</span>
                <span>${pr_html}</span>
            </div>
        </div>
    `;

    frm.set_df_property("custom_document_links_details", "options", html);
}

function get_payment_requests(invoice_name, callback) {
    // Get Payment Requests that reference this Purchase Invoice
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Payment Request",
            filters: {
                reference_doctype: "Purchase Invoice",
                reference_name: invoice_name,
                docstatus: ["=", 1] // Not cancelled
            },
            fields: ["name", "status", "grand_total"]
        },
        callback: function(r) {
            if (r.message) {
                callback(r.message);
            } else {
                callback([]);
            }
        }
    });
}

