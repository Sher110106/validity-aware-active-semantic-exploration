"""Glue between the four independently-hardened prospective packages.

Nothing here re-implements accounting, credential handling, or receipt
verification -- it only adapts one package's interface to another's, so the
audited implementation in each package stays the single source of truth.
"""
