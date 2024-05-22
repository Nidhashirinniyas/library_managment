import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class LibraryTransaction(Document):
    def before_submit(self):
        if self.type == "Issue":
            self.validate_issue()
            self.validate_maximum_limit()
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Issued" if int(article.noofcopies) == 0 else "Available"
                article.save()

                # Update article copies
                article.noofcopies = int(article.noofcopies) - 1
                article.save()

        elif self.type == "Return":
            self.validate_return()
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Available"
                article.save()

                # Update article copies
                article.noofcopies = int(article.noofcopies) + 1
                article.save()

    def validate_issue(self):
        self.validate_membership()
        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)
            # Check if the member has already issued this article and hasn't returned it
            if self.check_if_article_issued_not_returned(row.article):
                frappe.throw(f"Article {article.name} has already been issued to this member and not yet returned")

            if int(article.noofcopies) <= 0:
                frappe.throw(f"No available copies of article {article.name}")

    def validate_return(self):
        for row in self.get('articles'):
            if not row.article:
                frappe.throw("No article specified for return")

            article = frappe.get_doc("Article", row.article)
            if not article:
                frappe.throw("Article not found")

            # Check if the article has been issued
            issued = self.check_if_article_issued(article.name)
            if not issued:
                frappe.throw(f"Article {article.name} has not been issued to this member")

            # Check if the article has already been returned
            returned = self.check_if_article_returned(article.name)
            if returned:
                frappe.throw(f"Article {article.name} has already been returned")

            # Check that the return date is after the issue date
            issue_transaction = frappe.get_all("Library Transaction",
                                               filters={
                                                   "library_member": self.library_member,
                                                   "article": row.article,
                                                   "type": "Issue",
                                                   "docstatus": 1
                                               },
                                               fields=["date"],
                                               order_by="date desc",
                                               limit=1)

            if issue_transaction:
                issue_date = getdate(issue_transaction[0].date)
                return_date = getdate(self.date)
                if return_date <= issue_date:
                    frappe.throw(f"Return date for article {article.name} must be after the issue date {issue_date}")

    def check_if_article_returned(self, article_name):
        # Check if the article has been returned previously
        return_transaction = frappe.get_all("Library Transaction",
                                             filters={
                                                 "library_member": self.library_member,
                                                 "article": article_name,
                                                 "type": "Return",
                                                 "docstatus": 1
                                             },
                                             fields=["name"],
                                             limit=1)
        return bool(return_transaction)

    def check_if_article_issued(self, article_name):
        # Check if the article has been issued to this member
        issue_transaction = frappe.get_all("Library Transaction",
                                           filters={
                                               "library_member": self.library_member,
                                               "article": article_name,
                                               "type": "Issue",
                                               "docstatus": 1
                                           },
                                           fields=["name"],
                                           limit=1)
        return bool(issue_transaction)

    def check_if_article_issued_not_returned(self, article_name):
        # Check if the article has been issued to this member and not yet returned
        issue_transactions = frappe.get_all("Library Transaction",
                                            filters={
                                                "library_member": self.library_member,
                                                "article": article_name,
                                                "type": "Issue",
                                                "docstatus": 1
                                            },
                                            fields=["name"])

        return_transaction = frappe.get_all("Library Transaction",
                                            filters={
                                                "library_member": self.library_member,
                                                "article": article_name,
                                                "type": "Return",
                                                "docstatus": 1
                                            },
                                            fields=["name"])

        return bool(issue_transactions and not return_transaction)

    def on_cancel(self):
        if self.type == "Issue":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Issued" if int(article.noofcopies) == 0 else "Available"
                article.save()

                # Update article copies
                article.noofcopies = int(article.noofcopies) + 1
                article.save()

        elif self.type == "Return":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Available"
                article.save()

                # Update article copies
                article.noofcopies = int(article.noofcopies) - 1
                article.save()


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
        total_damage_fine = 0

        # Calculate the total damage fine
        for row in self.finee:
            if row.fine_type == 'Damage':
                damage_fine = int(row.fine_amount) if row.fine_amount else 0
                total_damage_fine += damage_fine

        # Calculate the total delay fine
        total_delay_fine = self.calculate_return_delay_fine()

        # Calculate the total fine
        self.total_fine = total_damage_fine + total_delay_fine

    def calculate_return_delay_fine(self):
        total_delay_fine = 0
        loan_period = frappe.db.get_single_value('Library Settings', 'loan_period')
        single_day_fine = frappe.db.get_single_value('Library Settings', 'single_day_fine')

        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)

            # Find the issue transaction for this article
            issue_transaction = frappe.get_all("Library Transaction",
                                               filters={
                                                   "library_member": self.library_member,
                                                   "article": row.article,
                                                   "type": "Issue",
                                                   "docstatus": 1
                                               },
                                               fields=["date"],
                                               order_by="date desc",
                                               limit=1)

            if issue_transaction:
                issued_date = getdate(issue_transaction[0].date)
                actual_duration = frappe.utils.date_diff(self.date, issued_date)

                if actual_duration > loan_period:
                    additional_days = actual_duration - loan_period
                    delay_fine = single_day_fine * additional_days
                    total_delay_fine += delay_fine

        return total_delay_fine
