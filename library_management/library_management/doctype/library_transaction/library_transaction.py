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

                # Update article copies
                article.noofcopies = int(article.noofcopies) - 1
                article.status = "Issued" if article.noofcopies == 0 else "Available"
                article.save()

        elif self.type == "Return":
            self.validate_return()
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)

                # Update article copies
                article.noofcopies += 1
                article.status = "Available"
                article.save()

    def validate_issue(self):
        self.validate_membership()
        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)

            if int(article.noofcopies) <= 0:
                frappe.throw(f"No available copies of article {article.name}")

    def validate_return(self):
        for row in self.get('articles'):
            if not row.article:
                frappe.throw("No article specified for return")

            article = frappe.get_doc("Article", row.article)
            if not article:
                frappe.throw("Article not found")

            # Get all transactions (issues and returns) for the member
            transactions = frappe.get_all(
                "Library Transaction",
                filters={
                    "library_member": self.library_member,
                    "docstatus": 1
                },
                fields=["name", "type", "article_name"]
            )

            article_issued = False
            article_returned = False

            for transaction in transactions:
                if transaction.get('article_name') == row.article:
                    if transaction.get('type') == "Issue":
                        article_issued = True
                        # Check if the article has been returned in any subsequent transaction
                        subsequent_transactions = frappe.get_all(
                            "Library Transaction",
                            filters={
                                "library_member": self.library_member,
                                "docstatus": 1,
                                "name": [">", transaction.get('name')],
                                "article_name": row.article,
                                "type": "Return"
                            },
                            fields=["name"]
                        )
                        if subsequent_transactions:
                            article_returned = True

            if article_issued:
                if article_returned:
                    frappe.throw(f"Article {article.name} has already been returned by member {self.library_member}")
                else:
                    # Allow the article to be returned
                    return
            else:
                frappe.throw(f"Article {article.name} is not issued to member {self.library_member}")

    def on_cancel(self):
        if self.type == "Issue":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)

                # Update article copies
                article.noofcopies = int(article.noofcopies) + 1
                article.status = "Available" if article.noofcopies > 0 else "Issued"
                article.save()

        elif self.type == "Return":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)

                # Update article copies
                article.noofcopies -= 1
                article.status = "Issued"
                article.save()

    def validate_maximum_limit(self):
        max_articles = frappe.db.get_single_value("Library Settings", "max_articles")

        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)

            # Get all transactions (issues) for the member for this specific article
            transactions = frappe.get_all(
                "Library Transaction",
                filters={
                    "library_member": self.library_member,
                    "type": "Issue",
                    "docstatus": 1,
                    "articles.article": row.article
                },
                fields=["name"]
            )

            total_articles_issued = len(transactions)

            # Check if issuing this article will exceed the maximum limit
            if total_articles_issued >= max_articles:
                self.popup_message(f"Cannot issue article {article.name}. Maximum limit of {max_articles} reached.")
                frappe.throw(f"Cannot issue article {article.name}. Maximum limit of {max_articles} reached.")

    def popup_message(self, message):
        frappe.msgprint(message, alert=True)

    def validate_membership(self):
        valid_membership = frappe.db.exists(
            "Library Membership",
            {
                "library_member": self.library_member,
                "docstatus": 1,
                "from_date": ("<=", self.date),
                "to_date": (">=", self.date),
            },
        )
        if not valid_membership:
            frappe.throw("The member does not have a valid membership")

    def before_save(self):
        total_damage_fine = 0

        for row in self.finee:
            if row.fine_type == 'Damage':
                damage_fine = int(row.fine_amount) if row.fine_amount else 0
                total_damage_fine += damage_fine

        total_delay_fine = self.calculate_return_delay_fine()

        self.total_fine = total_damage_fine + total_delay_fine

    def calculate_return_delay_fine(self):
        total_delay_fine = 0
        loan_period = frappe.db.get_single_value('Library Settings', 'loan_period')
        single_day_fine = frappe.db.get_single_value('Library Settings', 'single_day_fine')

        for row in self.get('articles'):
            article = frappe.get_doc("Article", row.article)

            issue_transaction = frappe.get_all("Library Transaction",
                                               filters={
                                                   "library_member": self.library_member,
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
