// Copyright (c) 2024, nidha and contributors
// For license information, please see license.txt

frappe.ui.form.on("Library Transaction", {
	refresh(frm) {
    if (doc.type == "Issued") {
			frm.set_query('article', () => {
        return {
            filters: {
                status: 'Issued'
            }
        }
    })
	}
	},
});
