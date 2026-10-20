frappe.query_reports["Cout de revient"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "price_list",
			label: __("Liste de prix de vente"),
			fieldtype: "Link",
			options: "Price List",
			default: "Standard Selling",
			get_query: () => ({ filters: { selling: 1 } }),
		},
		{
			fieldname: "rate_basis",
			label: __("Prix des matières"),
			fieldtype: "Select",
			options: ["Dernier prix d'achat", "Coût moyen en stock"],
			default: "Dernier prix d'achat",
		},
		{
			fieldname: "item",
			label: __("Produit"),
			fieldtype: "Link",
			options: "Item",
		},
	],
	// One row per product; open it to see its materials
	tree: true,
	name_field: "id",
	parent_field: "parent_id",
	initial_depth: 0,
};
