// Aide G50: the month's TVA and its settlement entry (dz_core/closing.py).
frappe.query_reports["Aide G50"] = {
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
			default: frappe.datetime.add_days(frappe.datetime.month_start(), -1),
			reqd: 1,
		},
	],

	onload(report) {
		report.page.add_inner_button(__("Passer l'écriture de liquidation"), () => {
			const filters = report.get_values();
			frappe.confirm(__("Passer l'écriture de liquidation de la TVA du mois ?"), () =>
				frappe
					.xcall("dz_core.closing.make_tva_settlement", {
						company: filters.company,
						month: filters.month,
					})
					.then((name) => {
						frappe.show_alert({
							message: __("Écriture {0} passée", [name]),
							indicator: "green",
						});
						report.refresh();
					})
			);
		});
		report.page.add_inner_button(__("Reverser la TVA sur pertes et dons"), () => {
			const filters = report.get_values();
			frappe.confirm(
				__("Reverser la TVA des sorties pour perte, vol ou don du mois ?"),
				() =>
					frappe
						.xcall("dz_core.tax_checks.make_tva_reversal", {
							company: filters.company,
							month: filters.month,
						})
						.then((name) => {
							frappe.show_alert({
								message: __("Écriture {0} passée", [name]),
								indicator: "green",
							});
							report.refresh();
						})
			);
		});
	},
};
