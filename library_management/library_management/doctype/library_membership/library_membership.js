frappe.ui.form.on("Library Membership", {
    from_date: function(frm) {
        updateToDate(frm);
    },
    duration: function(frm) {
        updateToDate(frm);
    }
});

// Function to calculate and update the to_date based on the selected duration
function updateToDate(frm) {
    var fromDate = frm.doc.from_date;
    var duration = frm.doc.duration;

    // Extract the number of days from the duration
    var durationDays = parseInt(duration.split(' ')[0]);

    // Calculate the to_date by adding durationDays to the from_date
    var toDate = new Date(fromDate);
    toDate.setDate(toDate.getDate() + durationDays);

    // Update the value of the to_date field in the form
    frm.set_value("to_date", toDate.toISOString().split('T')[0]);
}
