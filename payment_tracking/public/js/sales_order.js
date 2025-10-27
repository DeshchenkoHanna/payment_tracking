frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        add_create_buttons_to_payment_schedule(frm);
    }
});

function add_create_buttons_to_payment_schedule(frm) {
    // Use Frappe's official grid-row-render event
    $(frm.wrapper).on('grid-row-render', function(_e, grid_row) {
        // Only process payment_schedule grid
        if (grid_row.grid && grid_row.grid.df.fieldname === 'payment_schedule') {
            if (!grid_row.doc) return;

            // Check if button already exists to avoid duplicates
            if ($(grid_row.row).find('.custom-create-btn').length) return;

            // Find the last column (which contains btn-open-row / Edit button)
            let $last_col = $(grid_row.row).find('.col:last');

            // Check if this column has btn-open-row (Edit button)
            if ($last_col.find('.btn-open-row').length) {
                // Replace the entire column content with both buttons
                $last_col
                    .css({
                        'display': 'flex',
                        'justify-content': 'center',
                        'align-items': 'center'
                    })
                    .html(`
                        <div class="custom-create-btn" data-toggle="tooltip" data-placement="right" title="Create Payment Request or Invoice" style="cursor: pointer; padding: 0 5px 0 5px;">
                            <a><svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="16"></line>
                                <line x1="8" y1="12" x2="16" y2="12"></line>
                            </svg></a>
                        </div>
                        <div class="btn-open-row" data-toggle="tooltip" data-placement="right" title="" data-original-title="Edit">
                            <a><svg class="icon icon-xs" style="" aria-hidden="true">
                                <use class="" href="#icon-edit"></use>
                            </svg></a>
                        </div>
                    `);

                // Attach click handler to custom button
                $last_col.find('.custom-create-btn').on('click', function(e) {
                    e.stopPropagation();
                    e.preventDefault();

                    // Get the current row data
                    let row_doc = grid_row.doc;
                    let row_index = grid_row.doc.idx;

                    // Check if document is cancelled
                    if (frm.doc.docstatus === 2) {
                        frappe.show_alert({
                            message: __('You can\'t create invoice against cancelled document'),
                            indicator: 'orange'
                        });
                        return;
                    }

                    // Check if document has unsaved changes
                    if (frm.is_dirty()) {
                        frappe.show_alert({
                            message: __('You should save document\'s changes before creating invoice'),
                            indicator: 'orange'
                        });
                        return;
                    }

                    // Check if invoice already exists for this row
                    if (row_doc.custom_invoice_name) {
                        frappe.show_alert({
                            message: __('Invoice for this advance payment already exists: {0}', [row_doc.custom_invoice_name]),
                            indicator: 'orange'
                        });
                        return;
                    }

                    // Check if this is the last row in payment schedule
                    let is_last_row = row_index === frm.doc.payment_schedule.length;

                    if (is_last_row) {
                        // Check if Sales Order is submitted before creating Sales Invoice
                        if (frm.doc.docstatus !== 1) {
                            frappe.show_alert({
                                message: __('Sales Order must be submitted before creating Sales Invoice'),
                                indicator: 'orange'
                            });
                            return;
                        }
                        // Create Sales Invoice for the last payment schedule row
                        create_sales_invoice_from_schedule(frm, row_doc);
                    } else {
                        // Validate Payment Request can be created (ERPNext standard logic)
                        validate_payment_request_creation(frm, row_doc, row_index);
                    }
                });
            }
        }
    });
}

function validate_payment_request_creation(frm, schedule_row, row_index) {
    // Call server to validate if Payment Request can be created (ERPNext standard logic)
    frappe.call({
        method: 'payment_tracking.api.sales_order_utils.can_create_payment_request',
        args: {
            sales_order: frm.doc.name,
            payment_amount: schedule_row.payment_amount
        },
        callback: function(r) {
            if (r.message && r.message.can_create) {
                // Validation passed - create Payment Request
                create_payment_request_from_schedule(frm, schedule_row, row_index);
            } else if (r.message && r.message.error_message) {
                // Validation failed - show error
                frappe.show_alert({
                    message: r.message.error_message,
                    indicator: 'red'
                });
            } else {
                // Unexpected error
                frappe.show_alert({
                    message: __('Error validating Payment Request creation'),
                    indicator: 'red'
                });
            }
        },
        error: function() {
            frappe.show_alert({
                message: __('Error validating Payment Request creation'),
                indicator: 'red'
            });
        }
    });
}

function create_payment_request_from_schedule(frm, schedule_row, row_index) {
    // Create a new Payment Request based on the Payment Schedule row
    frappe.model.with_doctype('Payment Request', function() {
        let payment_request = frappe.model.get_new_doc('Payment Request');

        // Set basic fields from Sales Order
        payment_request.payment_request_type = 'Inward';
        payment_request.party_type = 'Customer';
        payment_request.party = frm.doc.customer;
        payment_request.currency = frm.doc.currency;
        payment_request.company = frm.doc.company;

        // Set reference to Sales Order
        payment_request.reference_doctype = 'Sales Order';
        payment_request.reference_name = frm.doc.name;

        // Set amount from payment schedule row (grand_total = payment_amount)
        payment_request.grand_total = schedule_row.payment_amount;

        // Set custom field: payment_term_pos = index of current row
        payment_request.payment_term_pos = row_index;

        // Set payment term if available
        if (schedule_row.payment_term) {
            payment_request.payment_term = schedule_row.payment_term;
        }

        // Set due date from schedule
        if (schedule_row.due_date) {
            payment_request.due_date = schedule_row.due_date;
        }

        // Note: Linking back to Payment Schedule is handled by server-side hook (after_insert)
        // No need to set custom_invoice_doctype and custom_invoice_name here

        // Open the new Payment Request form
        frappe.set_route('Form', 'Payment Request', payment_request.name);
    });
}

function create_sales_invoice_from_schedule(frm, schedule_row) {
    // Use Frappe's standard method to create Sales Invoice from Sales Order
    frappe.model.open_mapped_doc({
        method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
        frm: frm,
        args: {
            ignore_pricing_rule: 1
        },
        callback: function(new_doc) {
            // Set due date from schedule if available
            if (schedule_row.due_date) {
                frappe.model.set_value(new_doc.doctype, new_doc.name, 'due_date', schedule_row.due_date);
            }

            // Note: Linking back to Payment Schedule (last row) is handled by server-side hook (after_insert)
            // Sales Invoice is automatically linked to the last row of Payment Schedule
        }
    });
}
