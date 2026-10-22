// Export des écritures: the lines, then the files with their SHA-256 (dz_core/books/export.py).
frappe.query_reports["Export des ecritures"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("Du"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("Au"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],

	onload(report) {
		report.page.add_inner_button(__("Fichier des écritures"), () => {
			const filters = report.get_values();
			frappe
				.xcall("dz_core.books.export.export_entries", {
					company: filters.company,
					from_date: filters.from_date,
					to_date: filters.to_date,
				})
				.then((result) => {
					const files = result.files
						.map(
							([name, hash]) =>
								`<li>${frappe.utils.escape_html(
									name
								)}<br><code>${hash}</code></li>`
						)
						.join("");
					frappe.msgprint({
						title: __("Fichiers conservés"),
						message: `<p>${__("Archive")} <a href="/desk/dz-archive/${
							result.archive
						}">${result.archive}</a></p><ul>${files}</ul>`,
					});
				});
		});
	},
};
