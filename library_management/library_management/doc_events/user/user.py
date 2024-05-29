import frappe

def new_user_document(doc,method=None):
    fn=doc.get("first_name")
    frappe.msgprint(f"new {fn} in user")



def validate_single_librarian_role(doc, method=None):
    # Check if the user has the "Librarian" role
    if "Librarian" in [d.role for d in doc.get("roles")]:
        # Query to check if any other user has the "Librarian" role
        librarian_roles = frappe.db.exists("Has Role", {
            "role": "Librarian",
            "parenttype": "User",
            "parent": ["!=", doc.name]
        })

        if librarian_roles:
            frappe.throw("Another user already has the 'Librarian' role. Only one user can have this role at a time.")
