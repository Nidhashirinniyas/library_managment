import frappe
from frappe.model.document import Document

class LibraryTransaction(Document):
    def before_submit(self):
        if self.type == "Issue":
            self.validate_issue()
            self.validate_maximum_limit()
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Issued"
                article.save()

        elif self.type == "Return":
            self.validate_return()
            article = frappe.get_doc("Article", self.article)
            article.status = "Available"
            article.save()

    def validate_issue(self):
        self.validate_membership()
        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)
            if article.status == "Issued":
                frappe.throw(f"Article {article.name} is already issued by another member")

    def validate_return(self):
        article = frappe.get_doc("Article", self.article)
        if article.status == "Available":
            frappe.throw("Article cannot be returned without being issued first")

    def validate_maximum_limit(self):
        max_articles = frappe.db.get_single_value("Library Settings", "max_articles")
        count = frappe.db.count(
            "Library Transaction",
            {"library_member": self.library_member, "type": "Issue", "docstatus": 1},
        )
        cur_article_count = len(self.get('articles'))
        total_count = count + cur_article_count
        if total_count > max_articles:
            frappe.throw("The total count of issued articles exceeds the maximum limit")


    def validate_membership(self):
        valid_membership = frappe.db.exists(
            "Library Membership",
            {
                "library_member": self.library_member,
                "docstatus": 1,
                "from_date": ("<", self.date),
                "to_date": (">", self.date),
            },
        )
        if not valid_membership:
            frappe.throw("The member does not have a valid membership")

    def before_save(self):
        for row in self.finee:
            if self.type == "Return":
                self.validate_return()
                damage_fine = int(row.fine_amount) if row.fine_amount else 0
                if self.total_fine:
                    self.total_fine = self.total_fine + damage_fine
                else:
                    self.total_fine = damage_fine

    def calc_delay_fine(self):
        valid_delayfine = frappe.db.exists(
            "Library Transaction",
            {
                "library_member": self.library_member,
                "article": self.article,
                "docstatus": 1,
                "type": "Issue",
            },
        )

        if valid_delayfine:
            issued_doc = frappe.get_last_doc("Library Transaction", filters={
                "library_member": self.library_member,
                "article": self.article,
                "docstatus": 1,
                "type": "Issue"
            })
            issued_date = issued_doc.date

            loan_period = frappe.db.get_single_value('Library Settings', 'loan_period')

            actual_duration = frappe.utils.date_diff(self.date, issued_date)

            if actual_duration > loan_period:
                single_day_fine = frappe.db.get_single_value('Library Settings', 'single_day_fine')
                self.delay_fine = single_day_fine * (actual_duration - loan_period)
            else:
                self.delay_fine = 0
