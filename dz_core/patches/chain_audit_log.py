"""The audit trail rows written before 0.4.1 take their place in each
company's hash chain, in the order they were made (books/audit_chain.py;
review of 27 October 2026, 4.3)."""

from dz_core.books.audit_chain import chain_existing


def execute():
	chain_existing()
