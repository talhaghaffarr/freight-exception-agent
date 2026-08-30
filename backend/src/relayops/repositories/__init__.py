"""Persistence access.

Every tenant-owned read or write takes an explicit ``tenant_id``. There is no
ambient tenant and no repository method that infers one.
"""
