// Exercice comptable: year-end checks, then close, freeze, closing file, archive (dz_core/books/).
frappe.query_reports["Exercice comptable"] = {
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

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const color = data.status === "OK" ? "green" : "orange";
			value = `<span style="color: var(--${color}-600)">${value}</span>`;
		}
		return value;
	},

	onload(report) {
		const call = (method, label, args = {}) =>
			report.page.add_inner_button(
				label,
				() => {
					const filters = report.get_values();
					frappe.confirm(__("Confirmer : {0} ?", [label]), () =>
						frappe
							.xcall(method, {
								company: filters.company,
								fiscal_year: filters.fiscal_year,
								...args,
							})
							.then((result) => {
								if (result && result.message) {
									frappe.msgprint(result.message);
								} else if (typeof result === "string") {
									frappe.msgprint(
										`<a href="/desk/dz-archive/${result}">${result}</a>`,
										__("Fichiers conservés")
									);
								}
								report.refresh();
							})
					);
				},
				__("Clôture")
			);
		call("dz_core.books.year_end.close_year", __("Clôturer l'exercice"));
		call("dz_core.books.year_end.freeze_year", __("Geler l'exercice"));
		call("dz_core.books.closing_file.make_closing_file", __("Dossier de clôture"));
		call(
			"dz_core.books.closing_file.make_closing_file",
			__("Dossier de clôture (brouillon)"),
			{
				draft: 1,
			}
		);
		call("dz_core.books.archive.make_archive", __("Archive annuelle"));
	},
};
