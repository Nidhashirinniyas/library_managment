# Copyright (c) 2024, nidha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class Article(Document):
    def update_status(self):
        if self.noofcopies <= 0:
            self.status = "Issued"
        else:
            self.status = "Available"
