# Payment Tracking App - Features Documentation

## Overview
The Payment Tracking app extends ERPNext's payment functionality with enhanced tracking, document linking, and automated payment schedule management.

## Features

### 1. Automatic Payment Totals Tracking

**Custom Field**: `custom_total_payment`
**Applies to**: Purchase Order, Sales Order, Purchase Invoice, Sales Invoice

- Automatically calculates and displays total payments made against each document
- Updates in real-time when Payment Entries are submitted, updated, or cancelled
- Read-only currency field with precision control
- Available in list views and standard filters

**How it works**:
- Payment Entry events trigger automatic calculation
- Sums all allocated amounts from Payment Entry references
- Handles multi-currency conversions
- Updates on submit, cancel, and update after submit

### 2. Document Links Display

**Custom Field**: `custom_document_links_details`
**Applies to**: Payment Entry, Purchase Invoice

#### Payment Entry Links
Displays comprehensive document chain:
- Party name (Customer/Supplier) with clickable link
- Connected Purchase Orders or Sales Orders
- Referenced Purchase Invoices or Sales Invoices
- One-click copy functionality for all links

**Smart Detection**:
- Direct references from Payment Entry
- Indirect connections through invoices (e.g., PO linked via PI)
- Automatic party name resolution

#### Purchase Invoice Links
Shows complete procurement chain:
- Supplier ID and name
- Source Purchase Orders
- Purchase Invoice number
- Related Payment Requests
- Copy button for easy reference sharing

### 3. Payment Schedule Invoice Tracking

**Custom Fields**: `custom_invoice_doctype`, `custom_invoice_name`
**Applies to**: Payment Schedule (Sales Order and Purchase Order child tables)

Tracks which invoices were created from each payment schedule row:
- **Payment Request**: For advance payments (non-final rows)
- **Sales Invoice/Purchase Invoice**: For final delivery payment (last row)

**Automatic Linking**:
- Payment Request creation links back to originating schedule row
- Sales Invoice/Purchase Invoice automatically links to last payment schedule row
- Prevents duplicate invoice creation with validation
- Fields are editable to allow manual corrections if needed

### 4. Enhanced Sales Order Payment Workflow

**UI Enhancement**: Custom action buttons in Payment Schedule grid

#### Button Functionality
Each Payment Schedule row gets a custom "+" button:

**For advance payments** (non-last rows):
- Creates Payment Request (Inward) for the scheduled amount
- Validates against ERPNext rules (no overpayment)
- Auto-populates: customer, currency, amount, due date, payment term
- Links back to Payment Schedule row via `custom_invoice_name`
- Prevents duplicate Payment Requests

**For final payment** (last row):
- Creates Sales Invoice using ERPNext standard mapper
- Sets due date from schedule
- Auto-links to Payment Schedule last row
- Requires submitted Sales Order

**Validations**:
- Document must be saved before creating invoices
- Cannot create against cancelled documents
- Checks for existing invoices to prevent duplicates
- Validates payment amounts don't exceed available balance

### 5. Enhanced Purchase Order Payment Workflow

**UI Enhancement**: Custom action buttons in Payment Schedule grid

#### Button Functionality
Each Payment Schedule row gets a custom "+" button (same UI as Sales Order):

**For advance payments** (non-last rows):
- Creates Payment Request (Outward) for the scheduled amount
- Validates against ERPNext rules (no overpayment)
- Auto-populates: supplier, currency, amount, due date, payment term
- Links back to Payment Schedule row via `custom_invoice_name`
- Prevents duplicate Payment Requests

**For final payment** (last row):
- Creates Purchase Invoice using ERPNext standard mapper
- Sets due date from schedule
- Auto-links to Payment Schedule last row
- Requires submitted Purchase Order

**Validations**:
- Document must be saved before creating invoices
- Cannot create against cancelled documents
- Checks for existing invoices to prevent duplicates
- Validates payment amounts don't exceed available balance

### 6. Payment Request Validation

Server-side validation for Payment Request creation from both Sales Order and Purchase Order:
- Checks total available amount (grand_total - advance_paid)
- Accounts for existing submitted Payment Requests
- Prevents overpayment scenarios
- Clear error messages with amounts
- Works for both Inward (Sales) and Outward (Purchase) payment types

### 7. Connected Documents API

**Python APIs**:

#### `get_connected_orders_for_payment_entry(payment_entry_name)`
- Returns all Purchase Orders and Sales Orders connected to a Payment Entry
- Traverses through invoices to find indirect connections
- Removes duplicates
- Used by document links display

#### `get_party_name(party_type, party_id)`
- Safely retrieves Customer or Supplier display name
- Handles errors gracefully
- Fallback to ID if name not found

### 8. New Document Handling

- Payment Entry and Purchase Invoice skip document links display for unsaved documents
- Prevents "document not found" errors and temporary name display
- Links populate automatically after first save

## Installation

The app automatically creates all custom fields during installation via the `after_install` hook.

```bash
bench --site <site_name> install-app payment_tracking
```

## Technical Details

### Event Hooks

**Payment Entry Events**:
- `on_submit`: Update payment totals
- `on_update_after_submit`: Update payment totals
- `on_cancel`: Update payment totals
- `on_trash`: Update payment totals

**Payment Request Events**:
- `after_insert`: Link to Payment Schedule row (Sales Order and Purchase Order)

**Sales Invoice Events**:
- `after_insert`: Link to Payment Schedule last row

**Purchase Invoice Events**:
- `after_insert`: Link to Payment Schedule last row

### Client-Side Scripts

- **purchase_invoice.js**: Document links display and copy functionality
- **payment_entry.js**: Document links display with party and order tracking
- **sales_order.js**: Payment Schedule grid buttons and invoice creation
- **purchase_order.js**: Payment Schedule grid buttons and invoice creation

### Server-Side Logic

- **payment_entry.py**: Payment totals calculation and update
- **sales_order_utils.py**: Payment Request validation and linking for Sales Orders
- **purchase_order_utils.py**: Payment Request validation and linking for Purchase Orders
- **payment_entry_utils.py**: Connected documents API

## Use Cases

1. **Track payment progress** across Purchase/Sales Orders and Invoices
2. **Quick reference** to all related documents in payment workflow
3. **Prevent duplicate invoices** with automatic tracking
4. **Streamline advance payments** with one-click Payment Request creation
5. **Maintain payment schedule integrity** with automatic linking
6. **Copy document references** for communication (emails, notes)

## Dependencies

- ERPNext (core accounting module)
- Frappe Framework