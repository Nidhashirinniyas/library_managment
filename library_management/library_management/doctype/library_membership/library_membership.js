frappe.ui.form.on("Library Membership", {
  from_date: function(frm) {
      if(frm.doc.from_date>frm.doc.to_date){
        frappe.msgprint({
          title: __('Alert'),
          indicator: 'red',
          message: __('Enter the valid from date')
        });
      }

  },
  to_date: function(frm) {
      if(frm.doc.from_date>frm.doc.to_date){
        frappe.msgprint({
          title: __('Alert'),
          indicator: 'red',
          message: __('Enter the valid to dates')
        });
      }
  }
});
