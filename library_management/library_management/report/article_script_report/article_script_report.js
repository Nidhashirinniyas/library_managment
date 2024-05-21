// Copyright (c) 2024, nidha and contributors
// For license information, please see license.txt

frappe.query_reports["Article Script Report"] = {
	"filters": [
		{
        "fieldname":"name",
        "label": __("ID"),
        "fieldtype": "Link",
        "options": "Article"
    },
		{
        "fieldname":"author",
        "label": __("Author"),
        "fieldtype": "Data"
    },
		{
			"fieldname":"publisher",
			"label": __("Publisher"),
			"fieldtype": "Data"
		},
		{
			"fieldname":"isbn",
			"label": __("ISBN"),
			"fieldtype": "Data"
		}
	]
};
