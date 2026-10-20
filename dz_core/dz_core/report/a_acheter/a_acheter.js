frappe.query_reports["A acheter"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "only_to_order",
			label: __("Seulement ce qui reste à commander"),
			fieldtype: "Check",
			default: 0,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const colour = data.status === "Commandé" ? "blue" : "red";
			value = `<span class="indicator-pill ${colour}">${value}</span>`;
		}
		return value;
	},
};
