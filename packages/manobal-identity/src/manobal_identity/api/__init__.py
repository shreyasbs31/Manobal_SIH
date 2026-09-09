"""The enclave's HTTP surface.

Four callers, three methods, and no browser. This package is deliberately
small: identify the workload, check the scope, call the vault, return a
problem detail if anything refuses. The vault remains the only object that
decrypts anything.
"""
