// Aide G12: IFU or auto-entrepreneur turnover and tax (dz_core/books/ifu.py).
frappe.query_reports["Aide G12"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "fiscal_year",
			label: __("Exercice"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: frappe.defaults.get_user_default("fiscal_year"),
			reqd: 1,
		},
	],

	onload(report) {
		report.page.add_inner_button(__("Comptabiliser l'IFU"), () => {
			const filters = report.get_values();
			frappe.confirm(__("Comptabiliser l'IFU de l'exercice (6428 / 4477) ?"), () =>
				frappe
					.xcall("dz_core.books.ifu.book_ifu", {
						company: filters.company,
						fiscal_year: filters.fiscal_year,
					})
					.then((entry) => {
						frappe.show_alert({ message: entry, indicator: "green" });
						report.refresh();
					})
			);
		});
	},
};
