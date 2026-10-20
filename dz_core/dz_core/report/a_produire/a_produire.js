frappe.query_reports["A produire"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "only_missing",
			label: __("Seulement ce qui manque"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
