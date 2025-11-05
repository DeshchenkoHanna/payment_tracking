# Payment Tracking Project Structure

## Overview

**Type:** Frappe/ERPNext Custom App Extension
**Language:** Python (backend) + JavaScript (frontend)
**Publisher:** SwissCluster
**Description:** Extends ERPNext's payment module with enhanced tracking, document linking, and automated payment schedule management
**Size:** ~321KB, ~20 files
**License:** MIT
**Python Version:** >=3.10
**Framework:** Frappe ~=15.0.0 + ERPNext

---

## Directory Structure

```
payment_tracking/                    # Root project directory
├── payment_tracking/                # Main package directory
│   ├── __init__.py
│   ├── hooks.py                     # Frappe configuration & event hooks
│   ├── install.py                   # Installation procedures
│   ├── modules.txt                  # Module registry
│   ├── patches.txt                  # Patch registry
│   │
│   ├── api/                         # Backend APIs & business logic
│   │   ├── __init__.py
│   │   ├── payment_entry_utils.py   # Connected documents API
│   │   ├── sales_order_utils.py     # Sales Order payment logic
│   │   └── purchase_order_utils.py  # Purchase Order payment logic
│   │
│   ├── sc_payment/                  # Main feature module
│   │   ├── __init__.py
│   │   ├── custom_fields.py         # Custom field definitions
│   │   └── doctype_events/
│   │       ├── __init__.py
│   │       └── payment_entry.py     # Payment Entry event handlers
│   │
│   ├── patches/                     # Database migrations
│   │   ├── __init__.py
│   │   ├── update_custom_fields.py
│   │   └── set_allow_on_submit_for_payment_schedule.py
│   │
│   ├── public/                      # Frontend assets
│   │   └── js/                      # Client-side scripts
│   │       ├── payment_entry.js     # (187 lines) - Document links display
│   │       ├── purchase_invoice.js  # (195 lines) - Links & copy functionality
│   │       ├── sales_order.js       # (193 lines) - Payment schedule buttons
│   │       └── purchase_order.js    # (197 lines) - Payment schedule buttons
│   │
│   ├── config/                      # Configuration files
│   ├── templates/                   # Template files
│   │   └── pages/
│   └── modules.txt                  # Defines "SC Payment" module
│
├── pyproject.toml                   # Python project configuration
├── .pre-commit-config.yaml          # Pre-commit hooks (ruff, eslint, prettier)
├── .eslintrc                        # JavaScript linting rules
├── .editorconfig                    # Editor configuration
├── README.md                        # Installation & contribution guide
├── FEATURES.md                      # Comprehensive feature documentation
└── license.txt                      # MIT license
```

---

## Key Files & Their Purposes

| File | Purpose |
|------|---------|
| **hooks.py** | Registers document event handlers, custom field fixtures, doctype JS mappings |
| **install.py** | Runs after app installation to create custom fields |
| **custom_fields.py** | Defines 8 custom fields across 6 doctypes |
| **payment_entry.py** | Handles payment total calculations on submit/cancel/update |
| **payment_entry_utils.py** | APIs for finding connected orders and party names |
| **sales_order_utils.py** | Payment Request validation & linking for Sales Orders |
| **purchase_order_utils.py** | Payment Request validation & linking for Purchase Orders |
| **\*.js files** | Client-side UI enhancements (buttons, links display, copy functionality) |

---

## Modules & Components

### A. Custom Fields Module
**File:** `sc_payment/custom_fields.py`

Defines 8 custom fields:
- `custom_total_payment` → Purchase Order, Sales Order, Purchase Invoice, Sales Invoice (Currency, read-only)
- `custom_document_links_details` → Payment Entry, Purchase Invoice (HTML, read-only)
- `custom_invoice_doctype` → Payment Schedule (Link field, allow_on_submit)
- `custom_invoice_name` → Payment Schedule (Dynamic Link, allow_on_submit)

### B. Payment Entry Logic
**File:** `sc_payment/doctype_events/payment_entry.py`

Functions:
- `update_total_payments()` - Triggered on submit/update/cancel, calculates payment totals
- `find_indirect_references()` - Finds Orders through linked Invoices
- `update_document_total_payment()` - Updates payment totals for specific documents
- `recalculate_all_payments()` - Whitelisted utility function

### C. API Module
**Directory:** `api/`

#### payment_entry_utils.py:
- `get_connected_orders_for_payment_entry()` - Traverses Payment Entry references
- `get_party_name()` - Safe party lookup

#### sales_order_utils.py:
- `can_create_payment_request()` - Validates payment amounts
- `link_payment_request_to_schedule()` - Links PR to Payment Schedule
- `link_sales_invoice_to_schedule()` - Links SI to Payment Schedule

#### purchase_order_utils.py:
- Same functions as sales_order_utils but for purchase flow

### D. Frontend Components
**Directory:** `public/js/`

- **payment_entry.js** - Document links display with copy button
- **purchase_invoice.js** - Links display & procurement chain tracking
- **sales_order.js** - Payment Schedule grid buttons for creating PRs/Invoices
- **purchase_order.js** - Same as sales_order.js for purchase flow

---

## Configuration Files & Roles

| File | Purpose |
|------|---------|
| **pyproject.toml** | Poetry-based build config, ruff linting rules, tool configurations |
| **hooks.py** | Frappe app hooks (doc_events, doctype_js mappings, fixtures, after_install) |
| **.pre-commit-config.yaml** | Code quality: ruff (Python), eslint (JS), prettier (formatting), trailing-whitespace checks |
| **.eslintrc** | JavaScript linting configuration |
| **.editorconfig** | Editor settings consistency |
| **patches.txt** | Two patches: field updates & allow_on_submit settings |

---

## Document Events & Hooks

From `hooks.py`:

```python
doc_events = {
    "Payment Entry": {
        "on_submit": update_total_payments,
        "on_update_after_submit": update_total_payments,
        "on_cancel": update_total_payments,
        "on_trash": update_total_payments
    },
    "Payment Request": {
        "after_insert": [link_payment_request_to_schedule (both SO & PO)]
    },
    "Sales Invoice": {
        "after_insert": link_sales_invoice_to_schedule
    },
    "Purchase Invoice": {
        "after_insert": link_purchase_invoice_to_schedule
    }
}

doctype_js = {
    "Purchase Invoice": purchase_invoice.js,
    "Payment Entry": payment_entry.js,
    "Sales Order": sales_order.js,
    "Purchase Order": purchase_order.js
}
```

---

## Database Patches

For migrations:
- **update_custom_fields.py** - Ensures all custom fields are created/updated
- **set_allow_on_submit_for_payment_schedule.py** - Enables field updates after parent submission

---

## Development Tools & Quality Standards

### Code Quality:
- **ruff** - Python linting & formatting (110-char line length, Python 3.10 target)
- **eslint** - JavaScript linting with quiet mode
- **prettier** - Code formatting for JS/Vue/SCSS
- **pyupgrade** - Python syntax modernization

### CI/CD:
- GitHub Actions workflows (linting, testing)
- Semgrep rules for Frappe standards
- pip-audit for security

---

## Feature Breakdown

From `FEATURES.md`:

1. **Automatic Payment Totals Tracking** - Real-time payment calculations
2. **Document Links Display** - Shows procurement chains with clickable links
3. **Payment Schedule Invoice Tracking** - Links PRs and Invoices to schedule rows
4. **Sales Order Payment Workflow** - One-click Payment Request/Invoice creation
5. **Purchase Order Payment Workflow** - Same as Sales Order for POs
6. **Payment Request Validation** - Prevents overpayment scenarios
7. **Connected Documents API** - Traverses order-invoice relationships
8. **New Document Handling** - Prevents errors on unsaved documents

---

## Installation & Dependencies

### Installation Method:
```bash
bench get-app <repo-url> --branch develop
bench install-app payment_tracking
```

### Dependencies:
- ERPNext (core accounting module)
- Frappe Framework (~=15.0.0)
- No explicit external Python dependencies

### Post-Install:
- `after_install` hook runs `create_payment_tracking_fields()` automatically

---

## Project Statistics

- **Total Size:** ~321KB
- **Python Files:** ~10 files
- **JavaScript Files:** 4 files
- **Custom Fields:** 8 fields across 6 doctypes
- **API Endpoints:** 3 main utility modules
- **Event Hooks:** 4 doctypes with event handlers
- **Database Patches:** 2 migration files

---

## Summary

This is a well-structured Frappe app extension that enhances ERPNext's payment module with tracking, automation, and UI improvements. It uses Python for backend logic and JavaScript for frontend enhancements, follows Frappe conventions, and includes comprehensive documentation and quality tooling.

The app seamlessly integrates into ERPNext's existing payment workflow, adding visibility into payment totals, document relationships, and providing convenient shortcuts for creating payment-related documents directly from payment schedules.
