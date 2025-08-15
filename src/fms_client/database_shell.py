# app/shell.py
from __future__ import annotations

import cmd2
from cmd2 import with_argparser
import argparse
from typing import Optional
from sqlalchemy import select
from io import StringIO

from fms_client.data import mfr_database_instance as mfr_database
from fms_client.data.mfr_record import MfrRecord

# --- optional color support ---
try:
    from cmd2.ansi import style, Fg
except Exception:  # fallback if cmd2.ansi not available
    def style(s: str, **_: object) -> str:  # type: ignore[override]
        return s
    class Fg:
        CYAN = GREEN = YELLOW = RED = None





class MfrShell(cmd2.Cmd):
    """Interactive shell to manage MFR records."""

    IMMUTABLE_FIELDS = {"id", "barcode", "requested", "allocated", "requested_at", "allocated_at"}

    def __init__(self):
        try:
            super().__init__(use_ipython=False)  # works on newer cmd2
        except TypeError:
            super().__init__()  # fallback for cmd2 versions without that kwarg
        self.intro = "MFR Database Shell — type 'help' for commands and 'exit' to exit"
        self.prompt = "mfr> "

    # ---- colored/plain helpers ----
    def info(self, msg: str) -> None:
        self.poutput(style(msg, fg=Fg.CYAN))

    def ok(self, msg: str) -> None:
        self.poutput(style(msg, fg=Fg.GREEN))

    def warn(self, msg: str) -> None:
        self.poutput(style(msg, fg=Fg.YELLOW))

    def err(self, msg: str) -> None:
        self.perror(style(msg, fg=Fg.RED))

    # ---- create_record ----
    # ---- create_record(s) ----
    create_parser = argparse.ArgumentParser()
    create_parser.add_argument(
        "-n", "--count", type=int, default=1,
        help="Number of unassigned records to create (default: 1)",
    )

    @with_argparser(create_parser)
    def do_create_record(self, args: argparse.Namespace) -> None:
        """Create one or more UNASSIGNED records (no barcode)."""
        # Lazy import to avoid module cycles
        from fms_client.data.passwords import passwords_instance as passwords

        created_ids: list[int] = []
        failures = 0

        for i in range(max(1, args.count)):
            ok, mfr_data = passwords.generate_all()
            if not ok or not isinstance(mfr_data, dict):
                failures += 1
                continue

            # Ensure record is UNASSIGNED
            mfr_data = dict(mfr_data)  # copy
            mfr_data["barcode"] = None
            mfr_data["requested"] = "false"
            mfr_data["allocated"] = "false"
            mfr_data["requested_at"] = None
            mfr_data["allocated_at"] = None

            ok, rec_id = mfr_database.create_mfr_record(mfr_data)
            if ok and rec_id is not None:
                created_ids.append(rec_id)
            else:
                failures += 1

        if created_ids:
            self.ok(f"Created {len(created_ids)} unassigned record(s): {created_ids}")
        if failures:
            self.warn(f"Failed to create {failures} record(s).")
            
    # ---- request_record ----------------------------------------------------------------------------------
    request_parser = argparse.ArgumentParser()
    request_parser.add_argument("barcode", help="Barcode to assign to first available record")

    @with_argparser(request_parser)
    def do_request_record(self, args: argparse.Namespace) -> None:
        """Request a record only if it's unrequested and unallocated."""
        from fms_client.data.mfr_record import MfrRecord
        from sqlalchemy import select

        with mfr_database.create_session() as session:
            rec = session.execute(
                select(MfrRecord).where(MfrRecord.barcode == args.barcode)
            ).scalar_one_or_none()

        # If record exists
        if rec:
            if rec.requested == "false" and rec.allocated == "false":
                ok, rec_id = mfr_database.request_available_record(args.barcode)
                if ok:
                    self.ok(f"Requested record {rec_id}")
                else:
                    self.err(
                        "No available record to request.\n"
                        "You will need to first create a new record."
                    )
                return

            if rec.requested == "true" and rec.allocated == "false":
                self.warn(f"Record {args.barcode} has already been requested (ID: {rec.id})")
                return

            # All other cases → error with current values
            self.err(
                f"Invalid request state for barcode {args.barcode}:\n"
                f"  requested = {rec.requested}\n"
                f"  allocated = {rec.allocated}"
            )
            return

        # If no record exists, request an available one
        ok, rec_id = mfr_database.request_available_record(args.barcode)
        if ok:
            self.ok(f"Requested record {rec_id}")
        else:
            self.err(
                "No available record to request.\n"
                "You will need to first create a new record."
            )


    # ---- allocate_record ------------------------------------------------------------------------------
    allocate_parser = argparse.ArgumentParser()
    allocate_parser.add_argument("barcode", help="Barcode of record to allocate")

    @with_argparser(allocate_parser)
    def do_allocate_record(self, args: argparse.Namespace) -> None:
        """Allocate a record only if it's requested and not yet allocated."""
        from fms_client.data.mfr_record import MfrRecord
        from sqlalchemy import select

        with mfr_database.create_session() as session:
            rec = session.execute(
                select(MfrRecord).where(MfrRecord.barcode == args.barcode)
            ).scalar_one_or_none()

        if not rec:
            self.err("No record is associated with the provided barcode.")
            return

        if rec.requested == "true" and rec.allocated == "false":
            ok, rec_id = mfr_database.allocate_requested_record(args.barcode)
            if ok:
                self.ok(f"Allocated record {rec_id}")
            else:
                self.err("Failed to allocate record.")
            return

        if rec.requested == "true" and rec.allocated == "true":
            self.warn(f"Record {args.barcode} has already been allocated")
            return

        # All other cases → error
        self.err(
            f"Invalid allocation state for barcode {args.barcode}:\n"
            f"  requested = {rec.requested}\n"
            f"  allocated = {rec.allocated}"
        )

    # ---- show_record (id or barcode) ------------------------------------------------------------------------------
    show_parser = argparse.ArgumentParser()
    group = show_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", type=int, help="Record id")
    group.add_argument("--barcode", type=str, help="Record barcode")

    @with_argparser(show_parser)
    def do_show_record(self, args: argparse.Namespace) -> None:
        """Show a record by --id or --barcode with explicit not-found messages."""
        # by barcode
        if args.barcode is not None:
            s = mfr_database.record_str_by_barcode(args.barcode)
            if s is None:
                self.err("No record is associated with the provided barcode.")
                return
            self.info(f"Showing record barcode={args.barcode}")
            self.poutput(s)
            return

        # by id
        assert args.id is not None
        with mfr_database.create_session() as session:
            exists = session.execute(
                select(MfrRecord.id).where(MfrRecord.id == args.id)
            ).scalar_one_or_none()

        if exists is None:
            self.err("No record exists with the provided id.")
            return

        self.info(f"Showing record id={args.id}")
        s = mfr_database.record_str_by_id(args.id)  # args.id is not None here
        if s is None:
            self.err("No record exists with the provided id.")
            return
        self.info(f"Showing record id={args.id}")
        self.poutput(s)


    # ---- total_records ------------------------------------------------------------------------------------------------------
    def do_total_records(self, _: argparse.Namespace = None) -> None:
        """Show the total number of records in the database."""
        from fms_client.data.mfr_record import MfrRecord
        from sqlalchemy import select, func

        with mfr_database.create_session() as session:
            count = session.execute(
                select(func.count()).select_from(MfrRecord)
            ).scalar_one()

        self.info(f"Total records in database: {count}")

    # ---- check_for_consistency -------------------------------------------------------------------------------------------
    # ---- check_for_consistency ----
    def do_check_for_consistency(self, _: argparse.Namespace = None) -> None:
        """
        Verify DB invariants and print stats:
          - Inconsistency: allocated='true' but requested!='true'
          - Pending: requested='true' and allocated!='true' (i.e., requested but not yet allocated)
          - Totals: count(requested), count(allocated)
        """
        from sqlalchemy import select, func
        from fms_client.data.mfr_record import MfrRecord

        with mfr_database.create_session() as session:
            # Inconsistency: allocated but NOT requested
            inconsistent = session.execute(
                select(MfrRecord.id, MfrRecord.barcode)
                .where(
                    MfrRecord.allocated == "true",
                    MfrRecord.requested != "true",
                )
            ).all()

            # Pending allocations: requested but NOT yet allocated
            pending = session.execute(
                select(MfrRecord.id, MfrRecord.barcode)
                .where(
                    MfrRecord.requested == "true",
                    MfrRecord.allocated != "true",  # robust vs bad values
                )
            ).all()

            requested_count = session.execute(
                select(func.count()).select_from(MfrRecord).where(MfrRecord.requested == "true")
            ).scalar_one()

            allocated_count = session.execute(
                select(func.count()).select_from(MfrRecord).where(MfrRecord.allocated == "true")
            ).scalar_one()

        # Inconsistencies
        if inconsistent:
            self.err(f"Inconsistencies (allocated='true' but requested!='true'): {len(inconsistent)}")
            for rec_id, barcode in inconsistent:
                self.poutput(f"    * id={rec_id}, barcode={barcode or '<unassigned>'}")
        else:
            self.ok("No inconsistencies: all allocated records have also been requested.")

        # Totals
        self.info(f"Requested records: {requested_count}")
        self.info(f"Allocated records:  {allocated_count}")

        # Pending allocations
        if pending:
            self.warn(f"Pending allocations (requested but not yet allocated): {len(pending)}")
            for rec_id, barcode in pending:
                self.poutput(f"    * id={rec_id}, barcode={barcode or '<unassigned>'}")
        else:
            self.ok("No pending allocations.")


    # ---- update ----
    update_parser = argparse.ArgumentParser()
    update_parser.add_argument("barcode", help="Record barcode")
    update_parser.add_argument(
        "kv",
        nargs="+",
        help="One or more key=value pairs (e.g., smart_charging=true variant_name=V1)",
    )

    @with_argparser(update_parser)
    def do_update(self, args: argparse.Namespace) -> None:
        """Update record fields by barcode using key=value pairs (protected fields are rejected)."""
        # Parse key=value pairs
        patch: dict[str, str] = {}
        for item in args.kv:
            if "=" not in item:
                self.err(f"Invalid pair (missing '='): {item!r}")
                return
            k, v = item.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k:
                self.err(f"Empty key in pair: {item!r}")
                return
            patch[k] = v

        # Reject immutable fields (easy to extend via IMMUTABLE_FIELDS)
        blocked = [k for k in patch if k in self.IMMUTABLE_FIELDS]
        if blocked:
            self.err(
                "Update rejected for protected field(s): "
                + ", ".join(blocked)
                + "\n(Hint: use dedicated commands for lifecycle fields like 'request_record' / 'allocate_record'.)"
            )
            return

        # Validate keys against the model
        from fms_client.data.mfr_record import MfrRecord
        invalid = [k for k in patch if not hasattr(MfrRecord, k)]
        if invalid:
            self.err(f"Unknown field(s): {', '.join(invalid)}")
            return

        # Perform update
        ok = mfr_database.set_data_by_barcode(args.barcode, patch)
        if ok:
            self.ok(f"Record {args.barcode} updated successfully.")
            mfr_database.print_record_by_barcode(args.barcode)
        else:
            self.err(f"Failed to update record {args.barcode}.")


    # ---- retrieve ----
    retrieve_parser = argparse.ArgumentParser()
    retrieve_parser.add_argument("barcode", help="Record barcode")
    retrieve_parser.add_argument(
        "fields",
        nargs="+",
        help="One or more field names to retrieve (e.g., root_password root_hash variant_name)",
    )

    @with_argparser(retrieve_parser)
    def do_retrieve(self, args: argparse.Namespace) -> None:
        """Retrieve specific fields for a record identified by barcode."""
        from fms_client.data.mfr_record import MfrRecord  # validate columns

        # Validate requested fields exist on the model
        cols = [c.strip() for c in args.fields if c.strip()]
        invalid = [c for c in cols if not hasattr(MfrRecord, c)]
        if invalid:
            self.err(f"Unknown field(s): {', '.join(invalid)}")
            return

        ok, data = mfr_database.retrieve_data_by_barcode(args.barcode, cols)
        if not ok or data is None:
            self.err("No record is associated with the provided barcode or retrieval failed.")
            return

        # Pretty print results
        width = max(len(k) for k in data.keys()) if data else 0
        for k in cols:  # preserve user order
            v = data.get(k)
            self.poutput(f"{k:<{width}} : {v}")


    # ---- list_records ----
    list_parser = argparse.ArgumentParser()
    list_parser.add_argument(
        "--requested", choices=("true", "false", "any"), default="any",
        help="Filter by requested flag (default: any)",
    )
    list_parser.add_argument(
        "--allocated", choices=("true", "false", "any"), default="any",
        help="Filter by allocated flag (default: any)",
    )
    list_parser.add_argument(
        "--limit", type=int, default=50,
        help="Max rows to display (default: 50)",
    )
    list_parser.add_argument(
        "--columns", nargs="+",
        default=["id", "barcode", "requested", "allocated", "root_password"],
        help="Columns to display (model attributes).",
    )

    @with_argparser(list_parser)
    def do_list_records(self, args: argparse.Namespace) -> None:
        """List records with optional filters and selected columns."""
        from fms_client.data.mfr_record import MfrRecord  # lazy import to avoid cycles
        from fms_client.data import mfr_database_instance as mfr_database

        # Validate column names once
        invalid = [c for c in args.columns if not hasattr(MfrRecord, c)]
        if invalid:
            self.err(f"Unknown column(s): {', '.join(invalid)}")
            return

        # Fetch all then filter in-memory (fine for small/medium sets)
        records = mfr_database.get_mfr_records()

        def keep(rec: MfrRecord) -> bool:
            if args.requested != "any" and rec.requested != args.requested:
                return False
            if args.allocated != "any" and rec.allocated != args.allocated:
                return False
            return True

        rows = []
        for rec in records:
            if not keep(rec):
                continue
            row = [getattr(rec, col) for col in args.columns]
            rows.append(row)
            if len(rows) >= args.limit:
                break

        if not rows:
            self.poutput("No records match.")
            return

        # Render a simple aligned table (no extra deps)
        widths = [max(len(str(v)) for v in [h] + [r[i] for r in rows]) for i, h in enumerate(args.columns)]
        header = " | ".join(f"{h:<{w}}" for h, w in zip(args.columns, widths))
        sep = "-+-".join("-" * w for w in widths)
        self.poutput(header)
        self.poutput(sep)
        for r in rows:
            self.poutput(" | ".join(f"{str(v):<{w}}" for v, w in zip(r, widths)))


    def do_help(self, arg):
        """
        Show help for only the commands we implemented.
        Usage: help [command]
        """
        custom_commands = {
            "create_record": "Create one or more empty records in the database",
            "total_records": "Show total number of records",
            "request_record": "Mark a record as requested",
            "allocate_record": "Mark a requested record as allocated",
            "retrieve": "Retrieve specific fields for a record",
            "update": "Update specific fields for a record",
            "show_record": "Display full details for a record",
            "list_records": "List records with optional filters",
            "check_for_consistency": "Check for allocation inconsistencies"
        }

        if arg:
            # Show help for a specific command
            desc = custom_commands.get(arg)
            if desc:
                print(f"{arg}: {desc}")
            else:
                print(f"No help available for '{arg}'.")
        else:
            # Show all commands
            print("Available commands:")
            for cmd_name, desc in custom_commands.items():
                print(f"  {cmd_name:<25} {desc}")
                

    # ---- quit/exit -----------------------------
    def do_exit(self, _: Optional[str]) -> bool:  # type: ignore[override]
        """Exit the shell."""
        return True
    do_quit = do_exit  # alias


def main() -> None:
    MfrShell().cmdloop()

if __name__ == "__main__":
    main()