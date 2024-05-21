# Copyright (c) 2024, nidha and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class LibraryMember(Document):
    #this method will run every time a document is saved
    def before_save(self):
        self.full_name = f'{self.first_name} {self.last_name or ""}'

    # create a new document
    @frappe.whitelist()
    def create_membership(self,values):
        doc = frappe.new_doc('Library Membership')
        doc.library_member = self.name
        doc.from_date = values["from_date"]
        doc.to_date = values["to_date"]
        doc.paid = values["paid"]
        doc.insert()
        return doc.name

    @frappe.whitelist()
    def create_transaction(self,values):
        doc = frappe.new_doc('Library Transaction')
        doc.article = values["article"]
        doc.article_name = values["article_name"]
        doc.library_member = self.name
        doc.type = values["type"]
        doc.date_of_transaction = values["date_of_transaction"]
        doc.insert()
        return doc.name
