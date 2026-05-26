import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests requiring Postgres with full XLSX rules import")
