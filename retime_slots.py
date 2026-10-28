# pip install azure-identity azure-keyvault-secrets polars requests
#
# Move timetable slots to new times from an effective date.
#
# Repeating school events, classes (academic units) and clubs in Arbor are scheduled by
# one or more timetable slots (one per day of week / cycle day). Changing times from a
# date means ending the current slot the day before and creating a new slot with the new
# times from that date, copying the slot's locations, staff and student exceptions across.
#
# Only repeating school event slots are changed unless --allow-all-object-types is passed.
# Class slots drive lessons and attendance registers, so check Arbor's timetable guidance
# before changing them this way.
#
# 1. Export the current slots to a CSV:
#        python retime_slots.py export [--object-type RepeatingSchoolEvent] [--event-type MEETING]
#        python retime_slots.py export --object-type AcademicUnit --registration-only
# 2. Fill in Effective Date, New Start Time and New End Time for the slots to move.
#    Rows left blank are ignored.
# 3. Check what will happen, then apply:
#        python retime_slots.py apply --dry-run
#        python retime_slots.py apply [--allow-all-object-types]

import argparse
from datetime import date, datetime, timedelta

from azure.identity import InteractiveBrowserCredential
from azure.keyvault.secrets import SecretClient
from arbor_events import ArborEvents
import polars as pl

# Replace with url of Arbor instance
academy_url = "https://api-sandbox.uk.arbor.sc"

# Replace with your Key Vault URL
key_vault_url = "https://altakv01.vault.azure.net/"

# Objects that own timetable slots: listing method, response root key for a single record, name field
OBJECT_TYPES = {
    "RepeatingSchoolEvent": ("list_repeating_school_events", "repeatingSchoolEvent", "schoolEventName"),
    "AcademicUnit": ("list_academic_units", "academicUnit", "academicUnitName"),
    "Club": ("list_clubs", "club", "name"),
}

EXPORT_COLUMNS = [
    "Object Type", "Timetabled Object Href", "Name", "Event Type", "Registration Form", "Timetable Slot ID", "Day Of Week", "Day Of Cycle",
    "Term Time Only", "Start Time", "End Time", "Slot Effective Date", "Slot End Date",
    "Effective Date", "New Start Time", "New End Time",
]


def connect():
    """Get the Arbor password from Key Vault and return an ArborEvents client."""
    credential = InteractiveBrowserCredential(additionally_allowed_tenants=["23990c89-ae67-4afc-87ce-470c97afeb37"])
    secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
    secret = secret_client.get_secret("Arbor-SchoolEvents")
    return ArborEvents(academy_url, "ALTSchoolEvents", secret.value)


def to_date(value):
    """Arbor dates come back as "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"; None means open ended."""
    if not value:
        return None
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def to_time(value):
    """Accept "9:15", "09:15" or "09:15:00" and return "09:15:00"."""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    raise ValueError(f"Invalid time: {value}")


def is_active_on(record, on_date):
    """True if an effective-dated record (slot, slot location, slot staff) applies on on_date."""
    start = to_date(record.get("effectiveDate"))
    end = to_date(record.get("endDate"))
    return (start is None or start <= on_date) and (end is None or end >= on_date)


def list_registration_units(arbor):
    """List the academic units linked to a current registration form, as (unit, registration form name) pairs."""
    today = date.today()
    forms = arbor.list_registration_forms()
    print(f"Found {len(forms)} registration forms")
    year_ends = {}
    units = {}
    for count, form in enumerate(forms, start=1):
        form = arbor.get_full_record(form, "registrationForm", "registrationFormName")
        name = form.get("registrationFormName")

        # Skip forms from academic years that have finished
        year_href = (form.get("academicYear") or {}).get("href")
        if year_href and year_href not in year_ends:
            year_ends[year_href] = to_date(arbor._get_href(year_href)["academicYear"].get("endDate"))
        if year_href and year_ends[year_href] is not None and year_ends[year_href] < today:
            print(f"  {count}/{len(forms)} {name}: past academic year, skipped")
            continue

        found = 0
        for unit in arbor.list_academic_units(form["href"]):
            unit = arbor.get_full_record(unit, "academicUnit", "academicUnitName")
            # Stop rather than read every class in the school if the server ignored the filter
            if (unit.get("registrationForm") or {}).get("href") != form["href"]:
                raise RuntimeError("Arbor returned classes not linked to the registration form, so the "
                                   "registrationForm filter isn't supported. Stopping before reading every class.")
            units[unit["href"]] = (unit, name)
            found += 1
        print(f"  {count}/{len(forms)} {name}: {found} registration class(es)")
    return list(units.values())


def export_slots(arbor, csv_path, object_types, event_type_code=None, registration_only=False):
    """Write every slot that hasn't already ended, for every object of the given types."""
    today = date.today()
    rows = []
    for object_type in object_types:
        list_method, root_key, name_field = OBJECT_TYPES[object_type]
        if object_type == "RepeatingSchoolEvent":
            objects = [(obj, None) for obj in arbor.list_repeating_school_events(event_type_code)]
        elif object_type == "AcademicUnit" and registration_only:
            objects = list_registration_units(arbor)
        else:
            objects = [(obj, None) for obj in getattr(arbor, list_method)()]
        print(f"Reading slots for {len(objects)} {object_type} records")

        for count, (obj, registration_form) in enumerate(objects, start=1):
            if count % 25 == 0:
                print(f"  {count}/{len(objects)} {object_type} records read, {len(rows)} slots so far")
            obj = arbor.get_full_record(obj, root_key, name_field)
            # Skip classes that have already finished, rather than querying their slots
            obj_end = to_date(obj.get("endDate"))
            if obj_end is not None and obj_end < today:
                continue
            event_type = (obj.get("schoolEventType") or {}).get("href", "").rsplit("/", 1)[-1] or None
            for slot in arbor.list_timetable_slots(obj["href"]):
                end = to_date(slot.get("endDate"))
                if end is not None and end < today:
                    continue
                rows.append({
                    "Object Type": object_type,
                    "Timetabled Object Href": obj["href"],
                    "Name": obj.get(name_field),
                    "Event Type": event_type,
                    "Registration Form": registration_form,
                    "Timetable Slot ID": slot["id"],
                    "Day Of Week": slot.get("dayOfWeek"),
                    "Day Of Cycle": slot.get("dayOfCycle"),
                    "Term Time Only": slot.get("termTimeOnly"),
                    "Start Time": slot.get("startTime"),
                    "End Time": slot.get("endTime"),
                    "Slot Effective Date": slot.get("effectiveDate"),
                    "Slot End Date": slot.get("endDate"),
                    "Effective Date": None,
                    "New Start Time": None,
                    "New End Time": None,
                })

    pl.DataFrame(rows, schema={column: pl.Utf8 for column in EXPORT_COLUMNS}, strict=False).write_csv(csv_path)
    print(f"Exported {len(rows)} timetable slots to {csv_path}")


def retime_slot(arbor, slot_id, effective_date, start_time, end_time, dry_run, allow_all_object_types=False):
    """End a slot the day before effective_date and recreate it with new times from effective_date.
    Returns a (status, new slot href) tuple."""
    if effective_date <= date.today():
        raise ValueError(f"Effective date {effective_date} must be in the future")

    slot = arbor.get_timetable_slot(slot_id)
    object_type = slot["timetabledObject"]["entityType"]
    blocked = object_type != "RepeatingSchoolEvent" and not allow_all_object_types
    if blocked and not dry_run:
        raise ValueError(f"Slot belongs to {object_type}, not a repeating school event; pass --allow-all-object-types to change it")
    blocked_note = " (needs --allow-all-object-types)" if blocked else ""

    slot_start = to_date(slot.get("effectiveDate"))
    original_end_date = slot.get("endDate")
    slot_end = to_date(original_end_date)
    previous_day = effective_date - timedelta(days=1)

    if slot_end is not None and slot_end < effective_date:
        if slot_end == previous_day:
            # A previous run ended this slot already; the new slot is in that run's results
            return "Skipped: slot already ends the day before the effective date", None
        raise ValueError(f"Slot ends on {slot_end}, before the effective date")

    # Slot hasn't started yet, so there's nothing to end: change its times in place
    if slot_start is not None and slot_start >= effective_date:
        if dry_run:
            return f"Dry run: would change times on future slot (starts {slot_start}){blocked_note}", None
        arbor.update_timetable_slot(slot_id, startTime=start_time, endTime=end_time)
        return f"Updated times on future slot (starts {slot_start})", slot["href"]

    # Read locations, staff and student exceptions before ending the slot,
    # keeping those still in place on the effective date
    locations = [r for r in arbor.list_timetable_slot_locations(slot["href"]) if is_active_on(r, effective_date)]
    staff = [r for r in arbor.list_timetable_slot_staff(slot["href"]) if is_active_on(r, effective_date)]
    student_exceptions = [r for r in arbor.list_timetable_slot_student_exceptions(slot["href"])
                          if is_active_on(r, effective_date)]

    if dry_run:
        return (f"Dry run: would end on {previous_day} and create {start_time}-{end_time} from {effective_date} "
                f"with {len(locations)} location(s), {len(staff)} staff and "
                f"{len(student_exceptions)} student exception(s){blocked_note}"), None

    # End the old slot first so the new slot's room booking doesn't clash with the old one
    arbor.end_timetable_slot(slot_id, previous_day.isoformat())

    try:
        new_slot_href = arbor.create_timetable_slot(
            timetabled_object=slot["timetabledObject"],
            start_time=start_time,
            end_time=end_time,
            effective_date=effective_date.isoformat(),
            end_date=original_end_date,
            day_of_week=slot.get("dayOfWeek"),
            day_of_cycle=slot.get("dayOfCycle"),
            term_time_only=slot.get("termTimeOnly", True),
            frequency=slot.get("frequency"),
            academic_year=slot.get("academicYear"),
        )
    except Exception as e:
        raise RuntimeError(f"Old slot ended on {previous_day} but new slot NOT created: {e}") from e

    try:
        for record in locations:
            arbor.create_timetable_slot_location(new_slot_href, record["location"], effective_date.isoformat(),
                                                 record.get("endDate"))
        for record in staff:
            arbor.create_timetable_slot_staff(new_slot_href, record["staff"], effective_date.isoformat(),
                                              record.get("endDate"))
        for record in student_exceptions:
            arbor.create_timetable_slot_student_exception(new_slot_href, record["student"],
                                                          effective_date.isoformat(), record.get("endDate"))
    except Exception as e:
        raise RuntimeError(f"New slot {new_slot_href} created but copying location/staff/students failed: {e}") from e

    return "Success", new_slot_href


def apply_slots(arbor, csv_path, results_path, dry_run, allow_all_object_types=False):
    df = pl.read_csv(csv_path, infer_schema_length=0)
    results = []
    for row in df.iter_rows(named=True):
        if not row["New Start Time"]:
            continue
        try:
            status, new_slot_href = retime_slot(
                arbor,
                slot_id=row["Timetable Slot ID"],
                effective_date=to_date(row["Effective Date"]),
                start_time=to_time(row["New Start Time"]),
                end_time=to_time(row["New End Time"]),
                dry_run=dry_run,
                allow_all_object_types=allow_all_object_types,
            )
            results.append({**row, "Status": status, "New Slot Href": new_slot_href})
        except Exception as e:
            results.append({**row, "Status": f"Error: {str(e)}", "New Slot Href": None})
        print(f"Slot {row['Timetable Slot ID']}: {results[-1]['Status']}")

    pl.DataFrame(results, schema={column: pl.Utf8 for column in [*df.columns, "Status", "New Slot Href"]},
                 strict=False).write_csv(results_path)
    print(f"Results written to {results_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move repeating school events to new times from an effective date.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export current timetable slots to a CSV")
    export_parser.add_argument("--csv", default="timetable_slots.csv")
    export_parser.add_argument("--object-type", choices=[*OBJECT_TYPES, "all"], default="RepeatingSchoolEvent",
                               help="Which slots to export: repeating events (default), classes, clubs or all")
    export_parser.add_argument("--event-type", help="Only export repeating events of this type code, e.g. MEETING")
    export_parser.add_argument("--registration-only", action="store_true",
                               help="Only export classes linked to a registration form (registration groups)")

    apply_parser = subparsers.add_parser("apply", help="End slots and create new ones from the filled-in CSV")
    apply_parser.add_argument("--csv", default="timetable_slots.csv")
    apply_parser.add_argument("--results", default="timetable_slots_results.csv")
    apply_parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing to Arbor")
    apply_parser.add_argument("--allow-all-object-types", action="store_true",
                              help="Also change slots for classes and clubs, not just repeating school events")

    args = parser.parse_args()
    arbor = connect()
    if args.command == "export":
        object_types = list(OBJECT_TYPES) if args.object_type == "all" else [args.object_type]
        export_slots(arbor, args.csv, object_types, args.event_type, args.registration_only)
    else:
        apply_slots(arbor, args.csv, args.results, args.dry_run, args.allow_all_object_types)
