app_name = "payment_tracking"
app_title = "SC Payment"
app_publisher = "SwissCluster"
app_description = "Added extended capabilities for payment module, including logic rules and UI modifications."
app_email = "hanna.deshchenko@swisscluster.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "payment_tracking",
# 		"logo": "/assets/payment_tracking/logo.png",
# 		"title": "SC Payment",
# 		"route": "/payment_tracking",
# 		"has_permission": "payment_tracking.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/payment_tracking/css/payment_tracking.css"
# app_include_js = "/assets/payment_tracking/js/payment_tracking.js"

# include js, css files in header of web template
# web_include_css = "/assets/payment_tracking/css/payment_tracking.css"
# web_include_js = "/assets/payment_tracking/js/payment_tracking.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "payment_tracking/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Sales Order": "public/js/sales_order.js",
    "Purchase Order": "public/js/purchase_order.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "payment_tracking/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "payment_tracking.utils.jinja_methods",
# 	"filters": "payment_tracking.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "payment_tracking.install.before_install"
after_install = "payment_tracking.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "payment_tracking.uninstall.before_uninstall"
# after_uninstall = "payment_tracking.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "payment_tracking.utils.before_app_install"
# after_app_install = "payment_tracking.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "payment_tracking.utils.before_app_uninstall"
# after_app_uninstall = "payment_tracking.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "payment_tracking.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Payment Entry": "payment_tracking.sc_payment.overrides.payment_entry.CustomPaymentEntry"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Payment Entry": {
        "before_submit": "payment_tracking.sc_payment.doctype_events.payment_entry.populate_payment_schedule_idx",
        "on_submit": "payment_tracking.sc_payment.doctype_events.payment_entry.update_total_payments",
        "on_update_after_submit": "payment_tracking.sc_payment.doctype_events.payment_entry.update_total_payments",
        "on_cancel": "payment_tracking.sc_payment.doctype_events.payment_entry.update_total_payments",
        "on_trash": "payment_tracking.sc_payment.doctype_events.payment_entry.update_total_payments"
    },
    "Payment Request": {
        "after_insert": [
            "payment_tracking.api.sales_order_utils.link_payment_request_to_schedule",
            "payment_tracking.api.purchase_order_utils.link_payment_request_to_schedule"
        ],
        "on_cancel": [
            "payment_tracking.api.sales_order_utils.unlink_payment_request_from_schedule",
            "payment_tracking.api.purchase_order_utils.unlink_payment_request_from_schedule"
        ]
    },
    "Sales Invoice": {
        "after_insert": "payment_tracking.api.sales_order_utils.link_sales_invoice_to_schedule"
    },
    "Purchase Invoice": {
        "after_insert": "payment_tracking.api.purchase_order_utils.link_purchase_invoice_to_schedule",
        "before_save": "payment_tracking.sc_payment.doctype_events.purchase_invoice.before_save",
        "before_submit": "payment_tracking.sc_payment.doctype_events.purchase_invoice.before_submit"
    },
    "Purchase Order": {
        "before_validate": "payment_tracking.sc_payment.doctype_events.purchase_order.before_validate",
        "validate": "payment_tracking.sc_payment.doctype_events.purchase_order.validate"
    }
}

# Custom Fields
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name", "in", [
                    "Purchase Order-custom_total_payment",
                    "Sales Order-custom_total_payment",
                    "Purchase Invoice-custom_total_payment",
                    "Purchase Invoice-custom_document_links_details",
                    "Sales Invoice-custom_total_payment",
                    "Payment Entry-custom_document_links_details",
                    "Payment Schedule-custom_invoice_doctype",
                    "Payment Schedule-custom_invoice_name",
                    "Purchase Order-custom_manual_payment_schedule",
                    "Payment Request-custom_due_date",
                    "Payment Entry Reference-custom_payment_schedule_idx"
                ]
            ]
        ]
    }
]
# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"payment_tracking.tasks.all"
# 	],
# 	"daily": [
# 		"payment_tracking.tasks.daily"
# 	],
# 	"hourly": [
# 		"payment_tracking.tasks.hourly"
# 	],
# 	"weekly": [
# 		"payment_tracking.tasks.weekly"
# 	],
# 	"monthly": [
# 		"payment_tracking.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "payment_tracking.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "payment_tracking.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "payment_tracking.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["payment_tracking.utils.before_request"]
# after_request = ["payment_tracking.utils.after_request"]

# Job Events
# ----------
# before_job = ["payment_tracking.utils.before_job"]
# after_job = ["payment_tracking.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"payment_tracking.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

