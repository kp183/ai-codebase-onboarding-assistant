"""Service modules.

Keep package initialization side-effect free: importing ``app.services.foo``
must not construct Azure clients or replace a submodule with a service object.
"""
