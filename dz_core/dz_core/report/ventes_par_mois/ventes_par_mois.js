frappe.query_reports["Ventes par mois"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			description: __("Vide = société des Paramètres DZ Core"),
		},
		{
			fieldname: "from_month",
			label: __("Du mois de"),
			fieldtype: "Date",
			// the last 3 full months plus the current one
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -3),
			reqd: 1,
		},
		{
			fieldname: "to_month",
			label: __("Au mois de"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "by",
			label: __("Par"),
			fieldtype: "Select",
			options: [
				{ value: "Produit", label: __("Produit") },
				{ value: "Client", label: __("Client") },
				{ value: "Groupe de clients", label: __("Groupe de clients") },
			],
			default: "Produit",
			reqd: 1,
		},
		{
			fieldname: "show_variants",
			label: __("Voir les variantes"),
			fieldtype: "Check",
			default: 0,
			depends_on: "eval:doc.by == 'Produit'",
			description: __(
				"Sinon, les variantes (taille, couleur) sont additionnées sous leur modèle"
			),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.is_total_row) {
			value = `<b>${value}</b>`;
		} else if (column.fieldname === "evolution" && data && data.evolution != null) {
			const colour = data.evolution < 0 ? "red" : "green";
			value = `<span style="color: var(--${colour}-600)">${value}</span>`;
		}
		return value;
	},
};
