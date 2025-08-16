# tests/test_shell.py
from __future__ import annotations

import contextlib
import importlib
import io
import re
import random
import pytest
from cmd2.utils import StdSim
from fms_client.utils.logger import logger_base
logger = logger_base.get_logger(__name__)

from conftest import sample_record_data

SHELL_MODULE = "fms_client.database_shell"


@pytest.fixture
def shell(fake_passwords):  # fake_passwords comes from conftest.py
    """
    Import the shell after fixtures (DB + passwords) are in place,
    then return an instance with captured stdout/stderr.
    """
    shell_mod = importlib.import_module(SHELL_MODULE)
    shell_mod = importlib.reload(shell_mod)

    app = shell_mod.MfrShell()
    app.stdout = StdSim(io.StringIO())
    app.stderr = StdSim(io.StringIO())
    return app


def run(app, cmd: str) -> str:
    """Run one command and return combined stdout+stderr."""
    # Clear buffered outputs
    for stream in (app.stdout, app.stderr):
        inner = getattr(stream, "inner_stream", None)
        if inner is not None and hasattr(inner, "seek"):
            inner.seek(0)
            inner.truncate(0)

    # Capture any direct writes to sys.stderr during command execution
    sys_stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(sys_stderr_buf):
        app.onecmd_plus_hooks(cmd)

    return app.stdout.getvalue() + app.stderr.getvalue() + sys_stderr_buf.getvalue()


def test_interactive_flow(shell, sample_record_data):
    serial = random.randint(0,999)
    sample_record_data['barcode'] = f"0000{serial:04d}1020"
    sample_record_data['variant_name'] = "smart"

    # 1) Create unassigned records
    out = run(shell, "create_record -n 2")
    assert "Created 2 unassigned record(s)" in out

    # 2) Totals reflect creation
    out = run(shell, "total_records")
    assert "Total records in database: 2" in out
    logger.debug(out)

    # 3) Request one by barcode (requested=false, allocated=false -> request)
    out = run(shell, f"request_record {sample_record_data['barcode']}")
    assert "Requested record" in out
    logger.debug(out)

    # 4) Request again (requested=true, allocated=false -> already requested)
    out = run(shell, f"request_record {sample_record_data['barcode']}")
    assert "has already been requested" in out
    logger.debug(out)

    # 5) Consistency check should show pending allocation
    out = run(shell, "check_for_consistency")
    assert "Pending allocations (requested but not yet allocated):" in out
    logger.debug(out)

    # 6) Retrieve selected fields
    out = run(shell, f"retrieve {sample_record_data['barcode']} root_password root_hash")
    assert "root_password" in out and sample_record_data['root_password'] in out
    assert "root_hash" in out and sample_record_data['root_hash'] in out
    logger.debug(out)

    # 7) Update a mutable field and verify via show
    out = run(shell, f"update {sample_record_data['barcode']} variant_name={sample_record_data['variant_name']}")
    assert "updated successfully" in out
    out = run(shell, f"show_record --barcode {sample_record_data['barcode']}")
    assert sample_record_data['variant_name'] in out
    logger.debug(out)

    # 8) Allocate it (requested=true, allocated=false -> allocate)
    out = run(shell, f"allocate_record {sample_record_data['barcode']}")
    assert "Allocated record" in out
    logger.debug(out)

    # 9) Allocate again (requested=true, allocated=true -> already allocated)
    out = run(shell, f"allocate_record {sample_record_data['barcode']}")
    assert "has already been allocated" in out
    logger.debug(out)

    # 10) List records filtered by both flags and required columns
    out = run(shell, "list_records --requested true --allocated true --columns barcode requested allocated")
    assert sample_record_data['barcode'] in out
    assert len(re.findall(r"\btrue\b", out)) >= 2  # both flags should appear as true
    logger.debug(out)    

    # 11) Show non-existent barcode -> should emit error on stderr (captured here)
    out = run(shell, "show_record --barcode DOES_NOT_EXIST")
    assert "No record is associated with the provided barcode" in out
