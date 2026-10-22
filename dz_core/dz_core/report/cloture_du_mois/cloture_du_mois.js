// Clôture du mois: checks, then the two actions (dz_core/closing.py).
frappe.query_reports["Cloture du mois"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "month",
			label: __("Mois"),
			fieldtype: "Date",
			// the month that just ended
			default: frappe.datetime.add_days(frappe.datetime.month_start(), -1),
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
		const run = (method, label) =>
			report.page.add_inner_button(label, () => {
				const filters = report.get_values();
				frappe.confirm(__("Confirmer : {0} ?", [label]), () =>
					frappe
						.xcall(`dz_core.closing.${method}`, {
							company: filters.company,
							month: filters.month,
						})
						.then(() => report.refresh())
				);
			});
		run("reclassify_srbnb", __("Reclasser le 4081 au 4097"));
		run("freeze_month", __("Geler le mois"));
	},
};
