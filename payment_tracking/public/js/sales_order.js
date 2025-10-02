frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        add_hello_buttons_to_payment_schedule(frm);
    }
});

function add_hello_buttons_to_payment_schedule(frm) {
    // Use Frappe's official grid-row-render event
    $(frm.wrapper).on('grid-row-render', function(_e, grid_row) {
        // Only process payment_schedule grid
        if (grid_row.grid && grid_row.grid.df.fieldname === 'payment_schedule') {
            if (!grid_row.doc) return;

            // Check if button already exists to avoid duplicates
            if ($(grid_row.row).find('.custom-hello-btn').length) return;

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
                        <div class="custom-hello-btn" data-toggle="tooltip" data-placement="right" title="Click to say hello" style="cursor: pointer; padding: 0 5px 0 5px;">
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
                $last_col.find('.custom-hello-btn').on('click', function(e) {
                    e.stopPropagation();
                    e.preventDefault();
                    frappe.show_alert({
                        message: 'Hello!',
                        indicator: 'green'
                    });
                });
            }
        }
    });
}
