frappe.ui.form.on('Payment Entry', {
    onload: function(frm) {
        update_document_links_details(frm);
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

        update_document_links_details(frm);
    },

    party: function(frm) {
        update_document_links_details(frm);
    },

    references_on_form_rendered: function(frm) {
        update_document_links_details(frm);
    }
});

function update_document_links_details(frm) {
    if (!frm.doc.party || !frm.doc.party_type || !frm.doc.name) {
        frm.set_df_property('custom_document_links_details', 'options', '');
        return;
    }

    // First get the party name
    frappe.call({
        method: "payment_tracking.api.payment_entry_utils.get_party_name",
        args: {
            party_type: frm.doc.party_type,
            party_id: frm.doc.party
        },
        callback: function(r) {
            const party_name = r.message || frm.doc.party;

            // Then get connected orders and build complete HTML
            get_connected_orders_and_build_html(frm, frm.doc.party, party_name);
        },
        error: function(err) {
            console.warn('Error fetching party name:', err);
            // Fallback to party ID
            get_connected_orders_and_build_html(frm, frm.doc.party, frm.doc.party);
        }
    });
}

function get_connected_orders_and_build_html(frm, party_id, party_name) {
    // Get references from Payment Entry
    const references = frm.doc.references || [];

    // Separate references by type
    const direct_orders = references.filter(ref =>
        ref.reference_doctype === 'Sales Order' || ref.reference_doctype === 'Purchase Order'
    );
    const invoices = references.filter(ref =>
        ref.reference_doctype === 'Sales Invoice' || ref.reference_doctype === 'Purchase Invoice'
    );

    // Get connected orders using Python method
    frappe.call({
        method: "payment_tracking.api.payment_entry_utils.get_connected_orders_for_payment_entry",
        args: {
            payment_entry_name: frm.doc.name
        },
        callback: function(r) {
            const connected_orders = r.message || [];

            // Combine direct orders and connected orders
            const all_orders = [...direct_orders, ...connected_orders];

            // Remove duplicates
            const unique_orders = all_orders.filter((order, index, self) =>
                index === self.findIndex(o => o.reference_name === order.reference_name)
            );

            build_complete_payment_entry_html(party_id, party_name, unique_orders, invoices, frm);
        },
        error: function(err) {
            console.warn('Error fetching connected orders:', err);
            // Fallback to direct orders only
            build_complete_payment_entry_html(party_id, party_name, direct_orders, invoices, frm);
        }
    });
}



function build_complete_payment_entry_html(party_id, party_name, orders, invoices, frm) {
    const party_text = party_id;

    // Build order links
    let order_html = '';
    if (orders && orders.length > 0) {
        const order_links = orders.map(order => {
            const url = order.reference_doctype === 'Sales Order' ?
                `/app/sales-order/${order.reference_name}` :
                `/app/purchase-order/${order.reference_name}`;
            return `<a href="${url}" target="_blank" style="text-decoration: underline;">${order.reference_name}</a>`;
        }).join(', ');
        order_html = ` / ${order_links}`;
    }

    // Build invoice links
    let invoice_html = '';
    if (invoices && invoices.length > 0) {
        const invoice_links = invoices.map(invoice => {
            const url = invoice.reference_doctype === 'Sales Invoice' ?
                `/app/sales-invoice/${invoice.reference_name}` :
                `/app/purchase-invoice/${invoice.reference_name}`;
            return `<a href="${url}" target="_blank" style="text-decoration: underline;">${invoice.reference_name}</a>`;
        }).join(', ');
        invoice_html = ` / ${invoice_links}`;
    }

    // Create plain text for copying
    let copyText = `${party_text} ${party_name}`;
    if (orders && orders.length > 0) {
        copyText += ` / ${orders.map(o => o.reference_name).join(', ')}`;
    }
    if (invoices && invoices.length > 0) {
        copyText += ` / ${invoices.map(i => i.reference_name).join(', ')}`;
    }

    const html = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 8px; background: #f8f9fa; border-radius: 8px; position: relative;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <button class="btn icon-btn" onclick="copyDocumentLinksDetails('${copyText}')" onmouseover="this.classList.add('btn-default')" onmouseout="this.classList.remove('btn-default')">
                    <svg class="es-icon es-line  icon-sm" style="" aria-hidden="true">
                        <use class="" href="#es-line-copy-light"></use>
                    </svg>
                </button>
                <span style="font-weight: 500;"><a href="/app/${frm.doc.party_type.toLowerCase()}/${party_text}" target="_blank" style="text-decoration: underline;">${party_text}</a></span>
                <span>${party_name}</span>
                <span>${order_html}</span>
                <span>${invoice_html}</span>
            </div>
        </div>
    `;

    frm.set_df_property("custom_document_links_details", "options", html);
}