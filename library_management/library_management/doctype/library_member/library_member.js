frappe.ui.form.on('Library Member', {
    refresh: function(frm) {
        frm.add_custom_button('Create Membership', () => {
            let d = new frappe.ui.Dialog({
                title: 'Enter Membership Details',
                fields: [
                    {
                        label: 'From Date',
                        fieldname: 'from_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: 'To Date',
                        fieldname: 'to_date',
                        fieldtype: 'Date'
                    },
                    {
                        label: 'Paid',
                        fieldname: 'paid',
                        fieldtype: 'Check'
                    }
                ],
                primary_action(values) {
                    frm.call('create_membership', { values: values }).then(r => {
                        d.hide();
                        frappe.msgprint(`Membership ${r.message} has been created`);
                    });
                }
            });

            d.show();
        });

        frm.add_custom_button('Create Transaction', () => {
            let d = new frappe.ui.Dialog({
                title: 'Enter Transaction Details',
                fields: [
                    {
                        label: 'Article',
                        fieldname: 'article',
                        fieldtype: 'Link',
                        options: 'Article'
                    },
                    // {
                    //     label: 'Article Name',
                    //     fieldname: 'article_name',
                    //     fieldtype: 'Link',
                    //     options: 'Article'
                    // },
                    // {
                    //     label: 'Library Member',
                    //     fieldname: 'library_member',
                    //     fieldtype: 'Link',
                    //     options: 'Library Member'
                    // },
                    {
                        label: 'Type',
                        fieldname: 'type',
                        fieldtype: 'Select',
                        options: 'Issue\nReturn'
                    },
                    {
                        label : 'Delay Fine',
                        fieldname:'delay_fine',
                        fieldtype:'Currency',
                        depends_on: "eval:doc.type=='Return'"
                    },
                    {
                        label : 'Damage',
                        fieldname:'damage_fine',
                        fieldtype:'Currency',
                        depends_on: "eval:doc.type=='Return'"
                    },
                    {
                        label: 'Date Of Transaction',
                        fieldname: 'date_of_transaction',
                        fieldtype: 'Date'
                    }
                ],
                primary_action(values) {
                    frm.call('create_transaction', { values: values }).then(r => {
                        d.hide();
                        frappe.msgprint(`Transaction ${r.message} has been done`);
                    });
                }
            });

            d.show();
        });
    }
});
