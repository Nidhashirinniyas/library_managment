import frappe
from frappe.model.document import Document

class LibraryTransaction(Document):
    def before_submit(self):
        if self.type == "Issue":
            self.validate_issue()
            self.validate_maximum_limit()
            self.update_issued_books(add=True)
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Issued"
                article.save()

        elif self.type == "Return":
            self.validate_return()
            self.update_issued_books(add=False)
            article = frappe.get_doc("Article", self.articles)
            article.status = "Available"
            article.save()

    def validate_issue(self):
        print("Validating issue...")
        for row in self.get('articles'):
            print("Inside loop")
            article = frappe.get_doc("Article", row.article)
            article.noofcopies = int(article.noofcopies)
            print(f"Initial noofcopies for {article.name}: {article.noofcopies}")

            if article.noofcopies <= 0:
                frappe.throw(f"No available copies of {article.name} to issue")


    def validate_return(self):
        library_member = frappe.get_doc("Library Member", self.library_member)
        current_books = library_member.get("current_book", [])

        for row in self.get('articles'):
            returned_article = row.article

            # Check if the article is in the current_books list
            book_found = False
            for book in current_books:
                if book.issued_article == returned_article:
                    book_found = True
                    break

            if book_found:
                # Remove the returned book from the current_books list
                updated_current_books = [book for book in current_books if book.issued_article != returned_article or book.get('return_date') != self.date]

                library_member.set("current_book", updated_current_books)
                library_member.current_books_count = len(updated_current_books)
                library_member.save()
            else:
                frappe.throw(f"Article {returned_article} cannot be returned as it was not issued.")



    def on_cancel(self):
        library_member = frappe.get_doc("Library Member", self.library_member)
        current_books = library_member.get("current_book", [])

        if self.type == "Issue":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.noofcopies = int(article.noofcopies) + 1
                article.save()

                # Remove the book from the current_books list
                for i, book in enumerate(current_books):
                    if book.issued_article == row.article and not book.get('return_date'):
                        library_member.get("current_book").pop(i)
                        break

        elif self.type == "Return":
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.noofcopies = int(article.noofcopies) - 1
                article.status = "Issued"
                article.save()

                # Restore the book to the current_books list
                book_found = False
                for book in current_books:
                    if book.issued_article == row.article and book.get('return_date') == self.date:
                        book.return_date = None
                        book_found = True
                        break

                if not book_found:
                    library_member.append("current_book", {
                        "issued_article": row.article,
                    })

        # Update the current_books_count based on the number of rows in current_book child table
        library_member.current_books_count = len(library_member.get("current_book"))
        library_member.save()



    def validate_maximum_limit(self):
        max_articles = frappe.db.get_single_value("Library Settings", "max_articles")
        library_member = frappe.get_doc("Library Member", self.library_member)

        # Ensure current_book is initialized as an empty list if it's None
        current_book = library_member.get("current_book") or []

        current_books_count = len([book for book in current_book if not book.get('return_date')])
        new_issues_count = len(self.get('articles'))
        total_count = current_books_count + new_issues_count
        if total_count > max_articles:
            frappe.throw("The total count of issued articles exceeds the maximum limit")

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


    def update_issued_books(self, add):
        library_member = frappe.get_doc("Library Member", self.library_member)

        if add:
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                try:
                    noofcopies = int(article.noofcopies)
                except ValueError:
                    frappe.throw(f"Invalid number of copies for {article.name}")

                if noofcopies <= 0:
                    frappe.throw(f"No available copies of {article.name} to issue")

                # Decrement available copies
                article.noofcopies -= 1
                article.save()

                # Add to current_book
                library_member.append("current_book", {
                    "issued_article": article.name,
                })
        else:
            for row in self.get('articles'):
                for i, book in enumerate(library_member.get("current_book", [])):
                    if book.issued_article == row.article and not book.get('return_date'):
                        # Increment available copies when returned
                        article = frappe.get_doc("Article", book.issued_article)
                        try:
                            noofcopies = int(article.noofcopies)
                        except ValueError:
                            frappe.throw(f"Invalid number of copies for {article.name}")

                        article.noofcopies = int(article.noofcopies) + 1
                        article.save()
                        # Remove book from current_book
                        library_member.get("current_book").pop(i)
                        break

        # Update the current_books_count based on the number of rows in current_book child table
        library_member.current_books_count = len(library_member.get("current_book"))
        library_member.save()


    def before_save(self):
        for row in self.finee:
            if self.type == "Return":
                self.validate_return()
                damage_fine = int(row.fine_amount) if row.fine_amount else 0
                if self.total_fine:
                    self.total_fine += damage_fine
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
