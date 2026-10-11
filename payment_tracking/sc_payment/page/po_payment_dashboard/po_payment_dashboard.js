// Copyright (c) 2026, SwissCluster and contributors
// For license information, please see license.txt
//
// PO Payment Tracking dashboard: PO payment schedule + connected payments, grouped by PO,
// rendered as borderless cards on a light-grey canvas, with the report's filters and
// clickable document links. Payments are placed on schedule rows by idx -> Payment
// Request -> equal amount (see payment_tracking/api/po_payment_dashboard.py).

frappe.pages["po-payment-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("PO Payment Tracking"),
		single_column: true,
	});

	const f_company = page.add_field({
		fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		reqd: 1, default: frappe.defaults.get_user_default("Company"),
	});
	const f_supplier = page.add_field({ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" });
	const f_po = page.add_field({ fieldname: "purchase_order", label: __("Purchase Order"), fieldtype: "Link", options: "Purchase Order" });
	const f_from = page.add_field({ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" });
	const f_to = page.add_field({ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" });

	$(`<style>
		.po-dash { background:#f4f5f6; padding:18px 22px; min-height:420px; }
		.po-dash .sup-head { font-size:15px; font-weight:700; color:#1a1a1a; margin:0 0 12px; }
		.po-dash .sup-head ~ .sup-head { margin-top:14px; }
		.po-dash .po-card { background:#fff; border-radius:8px; padding:10px 16px; margin-bottom:26px; box-shadow:0 1px 3px rgba(0,0,0,0.07); }
		.po-dash .po-row { display:flex; align-items:flex-start; }
		.po-dash .po-date-col { flex:0 0 84px; width:84px; color:#6c7680; white-space:nowrap; padding-top:1px; }
		.po-dash .po-main { flex:1 1 auto; min-width:0; border-left:2px solid #e3e6e9; padding-left:14px; }
		.po-dash .po-head { display:flex; align-items:center; margin-bottom:8px; }
		.po-dash .po-id { flex:0 0 320px; display:flex; align-items:center; gap:10px; font-weight:600; }
		.po-dash .po-sum { font-weight:500; color:#42474d; }
		.po-dash .po-sum .metric { margin-left:18px; white-space:nowrap; }
		.po-dash .po-sum .lbl { color:#8d95a0; font-weight:600; }
		.po-dash .pt-wrap { display:flex; gap:14px clamp(14px, 2.2vw, 46px); align-items:flex-start; align-content:flex-start; flex-wrap:wrap; }
		.po-dash .tbl-block { }
		.po-dash .pt-title { font-size:11px; font-weight:600; color:#8d95a0; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:4px; }
		.po-dash .pt-table th { font-weight:600; color:#8d95a0; border:none; border-bottom:1px solid #e3e6e9; padding:2px 11px 5px 0; text-align:left; white-space:nowrap; }
		.po-dash .pt-table th.num { text-align:right; }
		.po-dash .pt-table td { border-bottom:1px solid #f1f2f4; padding:4px 11px 4px 0; }
		.po-dash .pt-table tbody tr:last-child td { border-bottom:none; }
		.po-dash .pt-table tr.po-extra td { color:#6c7680; }
		.po-dash .pt-table { border-collapse:separate; border-spacing:0; border:1px solid #dfe2e6; border-radius:8px; }
		.po-dash .pt-table th { padding-top:8px; }
		.po-dash .pt-table tbody tr:last-child td { padding-bottom:8px; }
		.po-dash .pt-table th:first-child, .po-dash .pt-table td:first-child { padding-left:12px; }
		.po-dash .pt-table th:last-child, .po-dash .pt-table td:last-child { padding-right:14px; }
		.po-dash table { width:auto; border-collapse:collapse; font-size:12px; }
		.po-dash td { border:none; padding:2px 16px 2px 0; white-space:nowrap; vertical-align:top; }
		.po-dash td.num { text-align:right; font-variant-numeric:tabular-nums; }
		.po-dash .um-head { font-weight:600; color:#8d95a0; margin-bottom:6px; text-transform:uppercase; }
		.po-dash .um-table { font-size:13px; }
		.po-dash .um-table th { font-weight:600; color:#8d95a0; border:none; border-bottom:1px solid #e3e6e9; padding:2px 18px 5px 0; text-align:left; white-space:nowrap; }
		.po-dash .um-table th.num { text-align:right; }
		.po-dash .um-table td { border-bottom:1px solid #f1f2f4; padding-top:4px; padding-bottom:4px; }
		.po-dash .um-table .um-date { color:#6c7680; font-size:14px; }
		.po-dash .um-table th:first-child, .po-dash .um-table .um-date { border-right:2px solid #e3e6e9; padding-right:16px; }
		.po-dash .um-table th:nth-child(2), .po-dash .um-table td:nth-child(2) { padding-left:16px; }
		.po-dash .um-table tr.um-grp-start td { border-top:1px solid #e8eaed; padding-top:5px; }
		.po-dash .um-table tr.um-grp { cursor:default; }
		.po-dash .um-table tr.um-noref td, .po-dash .um-table tr.um-noref a { color:#b8860b; }
		.po-dash-page .page-form { background:#fff; margin:0; padding:8px 22px; box-shadow:0 1px 2px rgba(0,0,0,0.05); }
	</style>`).appendTo(wrapper);

	const $body = $('<div class="po-dash"></div>').appendTo(page.body);
	page.set_primary_action(__("Refresh"), () => load(), "refresh");

	// pin the page head + filter bar to the top while the PO list scrolls
	const $wrap = $(wrapper).addClass("po-dash-page");
	function stick_header() {
		const nav = (document.querySelector(".navbar") || {}).offsetHeight || 0;
		const $head = $wrap.find(".page-head").first();
		$head.css({ position: "sticky", top: nav + "px", "z-index": 7 });
		$wrap.find(".page-form").css({ position: "sticky", top: nav + ($head.outerHeight() || 0) + "px", "z-index": 6 });
	}
	stick_header();
	setTimeout(stick_header, 300);
	$(window).off("resize.podash").on("resize.podash", stick_header);

	// PO status -> indicator colour (mirrors the Purchase Order list view)
	const STATUS_COLOR = {
		"Draft": "gray", "On Hold": "gray", "To Receive and Bill": "orange", "To Bill": "orange",
		"To Receive": "orange", "Completed": "green", "Closed": "green", "Delivered": "green",
		"Cancelled": "red",
	};

	const money = (v, ccy) => (v === null || v === undefined || v === "" ? "" : format_currency(v, ccy));

	function link(dt, name) {
		if (!name) return "";
		const lbl = frappe.utils.escape_html(name);
		return dt ? `<a href="/app/${frappe.router.slug(dt)}/${encodeURIComponent(name)}" target="_blank">${lbl}</a>` : lbl;
	}
	function status_pill(s) {
		if (!s) return "";
		return `<span class="indicator-pill ${STATUS_COLOR[s] || "gray"}">${frappe.utils.escape_html(s)}</span>`;
	}
	function term_rows(r, group_ccy) {
		// one term row may carry several payments -- term info on the first line only
		const pays = (r.payments && r.payments.length) ? r.payments : [null];
		return pays.map((p, i) => {
			const first = i === 0;
			const c = (p && p.currency) || group_ccy;
			return `<tr>
				<td class="num">${first ? (r.row || "") : ""}</td>
				<td>${first ? frappe.utils.escape_html(r.payment_term || "") : ""}</td>
				<td class="num">${first ? money(r.payment_amount, group_ccy) : ""}</td>
				<td>${first ? link(r.invoice_doctype, r.invoice_name) : ""}</td>
				<td>${p ? link("Payment Entry", p.payment_entry) : ""}</td>
				<td class="num">${p ? money(p.pe_amount, c) : ""}</td>
			</tr>`;
		}).join("");
	}

	function payments_block(g) {
		const rows = (g.payments || []).map((p) => `<tr>
			<td>${p.date ? frappe.datetime.str_to_user(p.date) : ""}</td>
			<td>${link("Payment Entry", p.payment)}</td>
			<td class="num">${money(p.amount, g.currency)}</td>
			<td>${link(p.reference_doctype, p.reference_name)}</td>
			<td>${p.pr ? link("Payment Request", p.pr) : ""}</td>
			<td>${frappe.utils.escape_html(p.payment_term || "")}</td>
		</tr>`).join("");
		return `<div class="tbl-block">
			<div class="pt-title">${__("Payments")}</div>
			<table class="pt-table">
				<thead><tr>
					<th>${__("Date")}</th><th>${__("Payment")}</th><th class="num">${__("Amount")}</th>
					<th>${__("Reference")}</th><th>${__("PR")}</th><th>${__("Payment term")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>
		</div>`;
	}

	function invoices_block(g) {
		const rows = (g.invoices || []).map((iv) => `<tr>
			<td>${iv.date ? frappe.datetime.str_to_user(iv.date) : ""}</td>
			<td>${link("Purchase Invoice", iv.invoice)}</td>
			<td class="num">${money(iv.amount, g.currency)}</td>
		</tr>`).join("");
		return `<div class="tbl-block">
			<div class="pt-title">${__("Invoices")}</div>
			<table class="pt-table">
				<thead><tr><th>${__("Date")}</th><th>${__("Invoice")}</th><th class="num">${__("Amount")}</th></tr></thead>
				<tbody>${rows}</tbody>
			</table>
		</div>`;
	}

	function terms_block(g) {
		let tb = (g.schedule || []).map((r) => term_rows(r, g.currency)).join("");
		(g.extra || []).forEach((e) => {
			const c = e.currency || g.currency;
			tb += `<tr class="po-extra">
				<td></td><td></td><td class="num"></td>
				<td>${link(e.invoice_doctype, e.invoice_name)}</td>
				<td>${link("Payment Entry", e.payment_entry)}</td>
				<td class="num">${money(e.pe_amount, c)}</td>
			</tr>`;
		});
		return `<div class="tbl-block">
			<div class="pt-title">${__("Payment terms")}</div>
			<table class="pt-table">
				<thead><tr>
					<th></th><th>${__("Term")}</th><th class="num">${__("Amount")}</th>
					<th>${__("Invoice")}</th><th>${__("Payment")}</th><th class="num">${__("Paid Amount")}</th>
				</tr></thead>
				<tbody>${tb}</tbody>
			</table>
		</div>`;
	}

	function po_card(g) {
		return `<div class="po-card">
			<div class="po-row">
				<div class="po-date-col">${g.po_date ? frappe.datetime.str_to_user(g.po_date) : ""}</div>
				<div class="po-main">
					<div class="po-head">
						<div class="po-id">
							${link("Purchase Order", g.purchase_order)}
							${status_pill(g.po_status)}
						</div>
						<span class="po-sum">
							<span class="metric"><span class="lbl">${__("ORDERED")}:</span> ${money(g.ordered, g.currency)}</span>
							<span class="metric"><span class="lbl">${__("PAID")}:</span> ${money(g.paid, g.currency)}</span>
							<span class="metric"><span class="lbl">${__("INVOICED")}:</span> ${money(g.invoiced, g.currency)}</span>
						</span>
					</div>
					<div class="pt-wrap">
						${terms_block(g)}
						${invoices_block(g)}
						${payments_block(g)}
					</div>
				</div>
			</div>
		</div>`;
	}

	function other_card(unmatched) {
		// group the other payments by Purchase Invoice; payments with no invoice
		// (unallocated / PO-only refs) go to the end with blank PINV columns
		const byPinv = {}, pinvOrder = [], noPinv = [];
		unmatched.forEach((r) => {
			if (r.purchase_invoice) {
				if (!byPinv[r.purchase_invoice]) { byPinv[r.purchase_invoice] = []; pinvOrder.push(r.purchase_invoice); }
				byPinv[r.purchase_invoice].push(r);
			} else {
				noPinv.push(r);
			}
		});
		let body = "";
		pinvOrder.forEach((pinv, gi) => {
			const rs = byPinv[pinv];
			const ccy = rs[0].currency;
			const total = rs.reduce((s, r) => s + flt(r.pe_amount), 0);
			const t = ` title="${frappe.utils.escape_html(__("Total payments") + ": " + money(total, ccy))}"`;
			rs.forEach((r, i) => {
				const sep = gi > 0 && i === 0 ? " um-grp-start" : "";
				body += `<tr class="um-grp${sep}">
					<td class="um-date"${t}>${i === 0 && r.pinv_date ? frappe.datetime.str_to_user(r.pinv_date) : ""}</td>
					<td${t}>${i === 0 ? link("Purchase Invoice", pinv) : ""}</td>
					<td class="num"${t}>${i === 0 ? money(r.pinv_amount, ccy) : ""}</td>
					<td${t}>${link("Payment Entry", r.payment_entry)}</td>
					<td class="num"${t}>${money(r.pe_amount, r.currency || ccy)}</td>
				</tr>`;
			});
		});
		noPinv.forEach((r, i) => {
			const sep = pinvOrder.length && i === 0 ? " um-grp-start" : "";
			const cls = (sep + (r.no_ref ? " um-noref" : "")).trim();
			body += `<tr class="${cls}">
				<td class="um-date">${r.pe_date ? frappe.datetime.str_to_user(r.pe_date) : ""}</td><td></td><td class="num"></td>
				<td>${link("Payment Entry", r.payment_entry)}</td>
				<td class="num">${money(r.pe_amount, r.currency)}</td>
			</tr>`;
		});
		return `<div class="po-card">
			<div class="um-head">${__("Other payments")}</div>
			<table class="um-table">
				<thead><tr>
					<th></th><th>${__("Invoice")}</th><th class="num">${__("INV Amount")}</th>
					<th>${__("Payment")}</th><th class="num">${__("Paid Amount")}</th>
				</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`;
	}

	function sup_link(docname, dispname) {
		const label = frappe.utils.escape_html(dispname || docname || __("(no supplier)"));
		return docname ? `<a href="/app/supplier/${encodeURIComponent(docname)}" target="_blank">${label}</a>` : label;
	}

	function render(data) {
		const groups = (data && data.groups) || [];
		const unmatched = (data && data.unmatched) || [];
		if (!groups.length && !unmatched.length) {
			$body.html(`<div class="text-muted">${__("No data for these filters.")}</div>`);
			return;
		}
		// organise everything by supplier
		const bySup = {}, supOrder = [];
		function bucket(docname, dispname) {
			const key = docname || "__none__";
			if (!bySup[key]) { bySup[key] = { docname: docname, name: dispname || docname, groups: [], other: [] }; supOrder.push(key); }
			if (dispname && !bySup[key].name) bySup[key].name = dispname;
			return bySup[key];
		}
		groups.forEach((g) => bucket(g.supplier, g.supplier_name).groups.push(g));
		unmatched.forEach((r) => bucket(r.supplier, r.supplier_name).other.push(r));

		let html = "";
		supOrder.forEach((key) => {
			const b = bySup[key];
			html += `<div class="sup-head">${sup_link(b.docname, b.name)}</div>`;
			b.groups.forEach((g) => { html += po_card(g); });
			if (b.other.length) html += other_card(b.other);
		});
		$body.html(html);
	}

	function load() {
		const args = {
			company: f_company.get_value(), supplier: f_supplier.get_value(),
			purchase_order: f_po.get_value(), from_date: f_from.get_value(), to_date: f_to.get_value(),
		};
		if (!args.company) {
			frappe.msgprint(__("Please select a Company."));
			return;
		}
		$body.html(`<div class="text-muted">${__("Loading...")}</div>`);
		frappe.call({
			method: "payment_tracking.api.po_payment_dashboard.get_data",
			args: args,
			callback: (r) => render(r.message),
		});
	}

	if (f_company.get_value()) load();
};
