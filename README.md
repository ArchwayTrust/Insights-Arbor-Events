# Arbor Events

This repository contains a set of code to interact with the Arbor Education API to facilitate room booking and event management.

## Installation

To use this project, you need to install the required dependencies. You can install them using pip:

```sh
pip install azure-identity azure-keyvault-secrets polars requests
```
## Configuration
1. Azure Key Vault: This project uses Azure Key Vault to securely store and retrieve secrets. Make sure you have an Azure Key Vault set up and the necessary secrets stored.

2. Arbor API: Replace the academy_url with the URL of your Arbor instance.

3. Key Vault URL: Replace the key_vault_url with the URL of your Azure Key Vault.

## Usage
### Initialize ArborEvents
The ArborEvents class is used to interact with the Arbor API. It requires the REST URL, GraphQL URL, and authentication credentials.
The main.py demonstrates how to use the class by looping through a CSV containing events data.

## Methods in ArborEvents
- get_room_id(room_name): Get the room ID based on the room name.
- create_room_unavailability(room_id, start_str, end_str, reason_str): Create room unavailability.
- get_staff_email_owner_id(email_address, email_address_type="WORK"): Get the staff email owner ID using GraphQL query.
- delete_school_event(event_id): Delete a school event.
- create_school_event(start_datetime, end_datetime, event_type_href, location_href, event_name, narrative): Create a school event.
- add_event_participant(event_id, participant_id, participant_type="Staff"): Add a participant to an event.
- list_repeating_school_events(event_type_code=None): List repeating school events, optionally by event type.
- list_timetable_slots(timetabled_object_href): List the timetable slots that schedule a repeating school event.
- get_timetable_slot(slot_id) / update_timetable_slot(slot_id, **fields): Read or change a timetable slot.
- end_timetable_slot(slot_id, end_date): Set a timetable slot's end date.
- create_timetable_slot(timetabled_object, start_time, end_time, effective_date, ...): Create a timetable slot.
- list_timetable_slot_locations / create_timetable_slot_location: Rooms attached to a timetable slot.
- list_timetable_slot_staff / create_timetable_slot_staff: Staff attached to a timetable slot.
- list_timetable_slot_student_exceptions / create_timetable_slot_student_exception: Students excluded from a timetable slot.
- list_registration_forms(): Registration forms (tutor groups).
- list_academic_units(registration_form_href=None) / list_clubs(): Classes and clubs, which are also scheduled by
  timetable slots. Pass a registration form href to get just that form's registration classes.

## Changing times of timetable slots from a date
Repeating school events, classes (academic units) and clubs are scheduled by timetable slots (one per day of the
week or cycle day), each with an `effectiveDate`, `endDate`, `startTime` and `endTime`. `retime_slots.py` ends each
slot the day before an effective date and creates a new slot with the new times from that date, copying the slot's
rooms, staff and student exceptions across. Slots that haven't started yet have their times changed in place.

```sh
python retime_slots.py export                          # repeating school events, all event types
python retime_slots.py export --event-type MEETING     # only one event type
python retime_slots.py export --object-type AcademicUnit   # classes; also Club or all
python retime_slots.py export --object-type AcademicUnit --registration-only   # registration groups only
# fill in Effective Date, New Start Time, New End Time for the slots to move (blank rows are ignored)
python retime_slots.py apply --dry-run                 # check timetable_slots_results.csv
python retime_slots.py apply
```

`apply` only changes repeating school event slots unless `--allow-all-object-types` is passed. Class slots drive
lessons and attendance registers, and Arbor normally manages them through timetable imports, so check Arbor's
timetable guidance in the developer portal before changing them this way.

Endpoint and field names come from Arbor's public PHP SDK (https://github.com/arbor-education/sis-sdk-php,
`src/Arbor/Model/TimetableSlot.php`). Test in the sandbox before running against a live school.
