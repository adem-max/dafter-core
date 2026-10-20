frappe.query_reports["Valeur du stock"] = {
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
			fieldname: "date",
			label: __("Au"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		// warehouses and the total in bold, their item groups under them
		if (data && !data.indent) {
			value = `<b>${value}</b>`;
		}
		return value;
	},
};
