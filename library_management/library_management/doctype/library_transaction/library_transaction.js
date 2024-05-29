frappe.ui.form.on("Library Transaction", {
    refresh(frm) {
        if (frm.doc.type == 'Issued') {
            frm.set_query('article', () => {
                return {
                    filters: {
                        status: 'Available'
                    }
                }
            })
        }

        set_member_query(frm);

    },

});



function set_member_query(frm) {
  frm.set_query("library_member", () => {
    return {
      query: "library_management.library_management.doctype.library_transaction.library_transaction.library_member_query"
    }
  })
}
