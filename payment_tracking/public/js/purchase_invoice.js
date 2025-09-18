
frappe.ui.form.on('Purchase Invoice', {
    onload: function(frm) {
        update_supplier_po_details(frm);
    },

    refresh: function(frm) {

        // Define the copy function globally
        if (!window.copySupplierPoDetails) {
            window.copySupplierPoDetails = function(textToCopy) {
                if (!textToCopy) return;

                // Copy to clipboard with fallback
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(textToCopy).then(() => {
                        frappe.show_alert({
                            message: 'Supplier PO Details copied to clipboard',
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
                            message: 'Supplier PO Details copied to clipboard',
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
        frm.set_value('custom_supplier_po_details', '');
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

    console.log('Purchase orders found:', purchase_orders);

    if (purchase_orders.length === 0) {
        // No PO, just show supplier info
        const html = build_simple_supplier_html(supplier_id, supplier_name, frm.doc.name);
        frm.set_df_property("custom_supplier_po_details", "options", html);
        return;
    }

    // Build HTML with PO links
    let po_links = purchase_orders.map(po =>
        `<a href="/app/purchase-order/${po}" target="_blank" class="badge-link">${po}</a>`
    ).join(', ');

    const supplier_text = supplier_id;
    const invoice_text = frm.doc.name;

    // Create plain text for copying
    const plainTextForCopy = `${supplier_text} ${supplier_name} / ${purchase_orders.join(', ')} / ${invoice_text}`;

    const html = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 8px; background: #f8f9fa; border-radius: 8px; position: relative;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <button class="btn icon-btn" onclick="copySupplierPoDetails('${plainTextForCopy}')" onmouseover="this.classList.add('btn-default')" onmouseout="this.classList.remove('btn-default')">
                    <svg class="es-icon es-line  icon-sm" style="" aria-hidden="true">
                        <use class="" href="#es-line-copy-light"></use>
                    </svg>
                </button>             
                <span style="font-weight: 500;">${supplier_text}</span>
                <span>${supplier_name}</span>
                <span>/ ${po_links} /</span>
                <span>${invoice_text}</span>

            </div>
        </div>
    `;

    frm.set_df_property("custom_supplier_po_details", "options", html);
}

function build_simple_supplier_html(supplier_id, supplier_name, invoice_name) {
    const supplier_text = supplier_id;
    const invoice_text = invoice_name;

    // Create plain text for copying
    const plainTextForCopy = `${supplier_text} ${supplier_name} / ${invoice_text}`;

    return `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 8px; background: #f8f9fa; border-radius: 8px; position: relative;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <button class="btn icon-btn" onclick="copySupplierPoDetails('${plainTextForCopy}')" onmouseover="this.classList.add('btn-default')" onmouseout="this.classList.remove('btn-default')">
                    <svg class="es-icon es-line  icon-sm" style="" aria-hidden="true">
                        <use class="" href="#es-line-copy-light"></use>
                    </svg>
                </button>
                <span style="font-weight: 500;">${supplier_text}</span>
                <span >${supplier_name}</span>
                <span>/ ${invoice_text}</span>

            </div>
        </div>
    `;
}

