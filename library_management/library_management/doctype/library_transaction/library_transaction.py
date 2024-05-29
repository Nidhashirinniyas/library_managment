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
            for row in self.get('articles'):
                article = frappe.get_doc("Article", row.article)
                article.status = "Available"
                article.save()

            self.calc_delay_fine()  # Calculate delay fine during return



    def validate_issue(self):
        # You can edit the validation logic here
        print("Validating issue...")
        for row in self.get('articles'):
            print("Inside loop")
            article = frappe.get_doc("Article", row.article)
            article.noofcopies = int(article.noofcopies)
            print(f"Initial noofcopies for {article.name}: {article.noofcopies}")

            if article.noofcopies <= 0:
                frappe.throw(f"No available copies of {article.name} to issue")


    def validate_return(self):
        # You can edit the validation logic here
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
        # You can edit the cancel logic here
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
        # You can edit the maximum limit validation logic here
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
        # You can edit the membership validation logic here
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
        # You can edit the update issued books logic here
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
                article.noofcopies = int(article.noofcopies) - 1
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
        # You can edit the before save logic here
        for row in self.finee:
            if self.type == "Return":
                self.validate_return()
                damage_fine = int(row.fine_amount) if row.fine_amount else 0
                if self.total_fine:
                    self.total_fine += damage_fine
                else:
                    self.total_fine = damage_fine

    def calc_delay_fine(self):
        # You can edit the delay fine calculation logic here
        self.total_fine = 0  # Initialize total fine

        for row in self.get('finee'):
            issued_article = row.article

            # Fetch all issue transactions for this member and type
            issued_docs = frappe.get_all('Library Transaction', filters={
                'library_member': self.library_member,
                'type': 'Issue',
                'docstatus': 1
            })

            issued_date = None

            # Check each transaction's articles for the issued_article
            for doc in issued_docs:
                transaction = frappe.get_doc('Library Transaction', doc.name)
                for article_row in transaction.get('articles'):
                    if article_row.article == issued_article:
                        issued_date = transaction.date
                        break
                if issued_date:
                    break

            if issued_date:
                loan_period = frappe.db.get_single_value('Library Settings', 'loan_period')
                actual_duration = frappe.utils.date_diff(self.date, issued_date)

                if actual_duration > loan_period:
                    single_day_fine = frappe.db.get_single_value('Library Settings', 'single_day_fine')
                    delay_days = actual_duration - loan_period
                    delay_fine = single_day_fine * delay_days
                else:
                    delay_fine = 0

                row.delay_fine = delay_fine
            else:
                frappe.throw(f"No valid issue record found for article {issued_article} and member {self.library_member}")

            # Calculate the damage fine for the row if available
            damage_fine = int(row.fine_amount) if row.fine_amount else 0

            # Update the row's total fine
            row.total_fine = damage_fine + row.delay_fine

            # Sum up the fines to update the total fine for the transaction
            self.total_fine += row.total_fine
            
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def library_member_query(doctype, txt, searchfield, start, page_len, filters):

    active_member_list = frappe.db.get_all("Library Membership", {"docstatus":1}, pluck="library_member")

    return [[member] for member in active_member_list]
