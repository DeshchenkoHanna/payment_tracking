// Copyright (c) 2026, SwissCluster and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Order Payment Tracking"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company"),
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{
			"fieldname": "purchase_order",
			"label": __("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
	],
};
