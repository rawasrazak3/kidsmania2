# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.query_builder.functions import Sum
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.period_closing_voucher.period_closing_voucher import PeriodClosingVoucher
from erpnext.accounts.utils import get_account_currency, get_fiscal_year, validate_fiscal_year

def get_pl_balances_based_on_dimensions(self, group_by_account=False):
	"""Get balance for dimension-wise pl accounts"""

	dimension_fields = ["t1.cost_center", "t1.finance_book"]

	self.accounting_dimensions = get_accounting_dimensions()
	for dimension in self.accounting_dimensions:
		dimension_fields.append("t1.{0}".format(dimension))

	if group_by_account:
		dimension_fields.append("t1.account")

	return frappe.db.sql(
		"""
		select
			t2.account_currency,
			{dimension_fields},
			sum(t1.debit_in_account_currency) - sum(t1.credit_in_account_currency) as bal_in_account_currency,
			sum(t1.debit) - sum(t1.credit) as bal_in_company_currency
		from `tabGL Entry` t1, `tabAccount` t2
		where
			t1.is_cancelled = 0
			and t1.account = t2.name
			and t2.report_type = 'Profit and Loss'
			and t2.docstatus < 2
			and t2.company = %s
			and t1.cost_center = %s
			and t1.posting_date between %s and %s
		group by {dimension_fields}
	""".format(
			dimension_fields=", ".join(dimension_fields)
		),
		(self.company, self.cost_center, self.get("year_start_date"), self.posting_date),
		as_dict=1,
	)

def get_balances_based_on_dimensions(
		self, group_by_account=False, report_type=None, for_aggregation=False, get_opening_entries=False
	):
		"""Get balance for dimension-wise pl accounts"""

		qb_dimension_fields = ["cost_center", "finance_book", "project"]

		self.accounting_dimensions = get_accounting_dimensions()
		for dimension in self.accounting_dimensions:
			qb_dimension_fields.append(dimension)

		if group_by_account:
			qb_dimension_fields.append("account")

		account_filters = {
			"company": self.company,
			"is_group": 0,
		}

		if report_type:
			account_filters.update({"report_type": report_type})

		accounts = frappe.get_all("Account", filters=account_filters, pluck="name")

		gl_entry = frappe.qb.DocType("GL Entry")
		query = frappe.qb.from_(gl_entry).select(gl_entry.account, gl_entry.account_currency)

		if not for_aggregation:
			query = query.select(
				(Sum(gl_entry.debit_in_account_currency) - Sum(gl_entry.credit_in_account_currency)).as_(
					"bal_in_account_currency"
				),
				(Sum(gl_entry.debit) - Sum(gl_entry.credit)).as_("bal_in_company_currency"),
			)
		else:
			query = query.select(
				(Sum(gl_entry.debit_in_account_currency)).as_("debit_in_account_currency"),
				(Sum(gl_entry.credit_in_account_currency)).as_("credit_in_account_currency"),
				(Sum(gl_entry.debit)).as_("debit"),
				(Sum(gl_entry.credit)).as_("credit"),
			)

		for dimension in qb_dimension_fields:
			query = query.select(gl_entry[dimension])

		query = query.where(
			(gl_entry.company == self.company)
			& (gl_entry.cost_center == self.cost_center)
			& (gl_entry.is_cancelled == 0)
			& (gl_entry.account.isin(accounts))
		)

		if get_opening_entries:
			query = query.where(
				gl_entry.posting_date.between(self.get("year_start_date"), self.posting_date)
				| gl_entry.is_opening
				== "Yes"
			)
		else:
			query = query.where(
				gl_entry.posting_date.between(self.get("year_start_date"), self.posting_date)
				& gl_entry.is_opening
				== "No"
			)

		if for_aggregation:
			query = query.where(gl_entry.voucher_type != "Period Closing Voucher")

		for dimension in qb_dimension_fields:
			query = query.groupby(gl_entry[dimension])

		return query.run(as_dict=1)

def validate_posting_date(self):
	# frappe.msgprint("tehre")
	validate_fiscal_year(
		self.posting_date, self.fiscal_year, self.company, label=_("Posting Date"), doc=self
	)
	# frappe.msgprint("tehre2")

	self.year_start_date = get_fiscal_year(
		self.posting_date, self.fiscal_year, company=self.company
	)[1]

	self.check_if_previous_year_closed()

	# frappe.msgprint("tehre3")

	pcv = frappe.qb.DocType("Period Closing Voucher")
	existing_entry = (
		frappe.qb.from_(pcv)
		.select(pcv.name)
		.where(
			(pcv.posting_date >= self.posting_date)
			& (pcv.fiscal_year == self.fiscal_year)
			& (pcv.docstatus == 1)
			& (pcv.company == self.company)
			& (pcv.cost_center == self.cost_center)
		)
		.run()
	)

	if existing_entry and existing_entry[0][0]:
		frappe.throw(
			_("Another Period Closing Entry {0} has been made after {1}").format(
				existing_entry[0][0], self.posting_date
			)
		)

	# frappe.msgprint("tehre4")

PeriodClosingVoucher.get_balances_based_on_dimensions=get_balances_based_on_dimensions
PeriodClosingVoucher.validate_posting_date=validate_posting_date