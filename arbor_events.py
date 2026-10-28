import requests
import re

class ArborEvents:
    """Class to interact with Arbor Events API
    Attributes:
        base_url (str): Base URL of Arbor instance
        rest_url (str): Base URL for REST endpoints
        graphql_url (str): GraphQL endpoint
        auth (tuple): Arbor API username and password
    Methods:
        list_event_types: List all event types
        get_event_type: Get event type by code  
        create_event_type: Create a new event type
        disable_event_type: Disable an event type
        enable_event_type: Enable an event type
        delete_event_type: Delete an event type
        lookup_room_id: Based on room name lookup it's id
        create_room_unavailability: Create room unavailability
        lookup_email_owner_id: Lookup the owner of an email address
        list_school_events: List all school events
        create_school_event: Create a new school event
        delete_school_event: Delete a school event
        list_repeating_school_events: List repeating school events
        list_timetable_slots: List timetable slots for a timetabled object
        get_timetable_slot: Get a timetable slot by id
        create_timetable_slot: Create a new timetable slot
        update_timetable_slot: Update fields on a timetable slot
        end_timetable_slot: End a timetable slot on a date
        list_timetable_slot_locations: List locations for a timetable slot
        create_timetable_slot_location: Add a location to a timetable slot
        list_timetable_slot_staff: List staff for a timetable slot
        create_timetable_slot_staff: Add a staff member to a timetable slot
        list_timetable_slot_student_exceptions: List students excluded from a timetable slot
        create_timetable_slot_student_exception: Exclude a student from a timetable slot
        list_registration_forms: List registration forms
        list_academic_units: List academic units (classes)
        list_clubs: List clubs"""
    
    def __init__(self, base_url, username, password):
        """Initialize ArborEvents class
        Args:
            base_url (str): Base URL of Arbor instance
            username (str): Arbor API username
            password (str): Arbor API password
        Returns:
            None"""
        
        self.base_url = base_url
        self.rest_url = f"{base_url}/rest-v2"  # Base URL for REST endpoints
        self.graphql_url = f"{base_url}/graphql/query"  # GraphQL endpoint
        self.auth = (username, password)

    def _post_request(self, url, payload):
        response = requests.post(url, json=payload, auth=self.auth)
        if response.status_code == 201:
            return response.json()
        else:
            raise RuntimeError(f"Request failed. status_code: {response.status_code}, text: {response.text}")

    def _get_request(self, url, params=None):
        response = requests.get(url, params=params, auth=self.auth)
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"Request failed. status_code: {response.status_code}, text: {response.text}")

    def _put_request(self, url, payload):
        response = requests.put(url, json=payload, auth=self.auth)
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"Request failed. status_code: {response.status_code}, text: {response.text}")

    def _list_request(self, resource, root_key, filters=None, page_size=100):
        """GET every page of a REST listing.
        Args:
            resource (str): Resource path segment (e.g. "timetable-slots")
            root_key (str): Key holding the results in the response (e.g. "timetableSlots")
            filters (dict): Property filters as {"propertyName.operator": value}
            page_size (int): Records per page
        Returns:
            list: Result dicts from all pages"""

        params = {f"filters.{key}": value for key, value in (filters or {}).items()}
        params["page-size"] = page_size
        results = []
        page_number = 1
        while True:
            params["page-number"] = page_number
            page = self._get_request(f"{self.rest_url}/{resource}", params).get(root_key) or []
            # Stop if the page is short, or the server ignored paging and sent the same page again
            if not page or (results and page[0].get("href") == results[0].get("href")):
                break
            results.extend(page)
            if len(page) < page_size:
                break
            page_number += 1
        return results

    def _get_href(self, href):
        """GET a resource by its href (e.g. "/rest-v2/timetable-slots/12")."""
        return self._get_request(f"{self.base_url}{href}")

    def get_full_record(self, record, root_key, field):
        """Return a listed record in full, only fetching it if the listing left out field.
        Args:
            record (dict): Record from a listing (at least entityType and href)
            root_key (str): Key holding the record in a GET response (e.g. "timetableSlot")
            field (str): A field the full record always has (e.g. "startTime")
        Returns:
            dict: Full record"""

        if field in record:
            return record
        return self._get_href(record["href"])[root_key]

    def _delete_request(self, url):
        response = requests.delete(url, auth=self.auth)
        if response.status_code == 204:
            return True
        else:
            raise RuntimeError(f"Request failed. status_code: {response.status_code}, text: {response.text}")

    def list_event_types(self):
        """List all event types
        Returns:
            response: Response object"""
        api_url = f"{self.rest_url}/school-event-types/"
        response = requests.get(api_url, auth=self.auth)
        return response.json()

    def get_event_type(self, event_code):
        """Get event type by code
        Args:
            event_code (str): Event code
        Returns:
            response: Response object"""
        api_url = f"{self.rest_url}/school-event-types/{event_code}"
        response = requests.get(api_url, auth=self.auth)
        return response

    def create_event_type(self, event_code, event_name):
        """Create a new event type
        Args:
            event_code (str): Event code
            event_name (str): Event name
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-event-types/"
        payload = {
            "request": {
                "schoolEventType": {
                    "active": True,
                    "entityType": "SchoolEventType",
                    "code": event_code,
                    "schoolEventTypeName": event_name
                }
            }
        }
        response = requests.post(api_url, json=payload, auth=self.auth)
        return response

    def disable_event_type(self, event_code):
        """Disable an event type
        Args:
            event_code (str): Event code
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-event-types/{event_code}"
        payload = {
            "request": {
                "schoolEventType": {
                    "active": False,
                    "href": f"/rest-v2/school-event-types/{event_code}",
                    "entityType": "SchoolEventType"
                }
            }
        }
        response = requests.put(api_url, json=payload, auth=self.auth)
        return response
    
    def enable_event_type(self, event_code):
        """Enable an event type
        Args:
            event_code (str): Event code
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-event-types/{event_code}"
        payload = {
            "request": {
                "schoolEventType": {
                    "active": True,
                    "href": f"/rest-v2/school-event-types/{event_code}",
                    "entityType": "SchoolEventType"
                }
            }
        }
        response = requests.put(api_url, json=payload, auth=self.auth)
        return response

    def delete_event_type(self, event_code):
        """Delete an event type
        Args:
            event_code (str): Event code
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-event-types/{event_code}"
        response = requests.delete(api_url, auth=self.auth)
        return response
    
    def lookup_room_id(self, room_to_find):
        """Based on room name lookup it's id
        Args:
            room_to_find (str): Room name to search for
        Returns:
            room_id (str): Room id"""
        
        # Create the GraphQL query
        query = f"""
        {{
            Room(roomName: "{room_to_find}"){{
                id
            }}
        }}
        """
        # Send the request
        response = requests.post(self.graphql_url, json={"query": query}, auth=self.auth)

        # Check response
        if response.status_code == 200:
            try:
                room_id = response.json()["data"]["Room"][0]["id"]
                return room_id
            except:
                raise RuntimeError("Room not found.")
        else:
            raise RuntimeError(f"Request failed with status code: {response.status_code}")
        
    def create_room_unavailability(self, room_id, start_str, end_str, reason_str):
        """Create room unavailability.
        Args:
            room_id (str): Room id
            start_str (str): Start datetime in string format (e.g. "2024-12-21 16:00:00")
            end_str (str): End datetime in string format (e.g. "2024-12-21 17:00:00")
            reason_str (str): Reason for unavailability
        Returns:
            response: Response json"""

        api_url = f"{self.rest_url}/roomUnavailability"
        payload = {
            "request":
            {
                "roomUnavailability": 
                    {
                        "room":
                            {
                                "entityType": 'Room',
                                "id": room_id,
                                "href": f"/rest-v2/rooms/{room_id}",
                            },
                        "startDatetime": start_str,
                        "endDatetime": end_str,
                        'reason': reason_str
                    }
            }
        }

        return self._post_request(api_url, payload)

    def lookup_email_owner_id(self, email_address, email_address_type="WORK"):
        """
        Lookup the owner of an email address
        Args:
            email_address (str): Email address to search for
            email_address_type (str): Email address type (default: "WORK")
        Returns:
            owner_id (str): Owner ID of the email address"""
        
        query = f"""
        {{
            EmailAddress(emailAddress: "{email_address}", emailAddressType: "{email_address_type}"){{
                id
                emailAddress
                emailAddressType
                emailAddressOwner{{
                    id
                    entityType
                }}
            }}
        }}
        """
        response = requests.post(self.graphql_url, json={"query": query}, auth=self.auth)
        data = response.json()

        email_addresses = data["data"]["EmailAddress"]
        for entry in email_addresses:
            if entry["emailAddressOwner"]["entityType"] == "Staff":
                return entry["emailAddressOwner"]["id"]
        
        raise RuntimeError(f"User with email address {email_address} not found.")

    def list_school_events(self):
        """
        List all school events
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-events/"
        response = requests.get(api_url, auth=self.auth)
        return response.json()

    def create_school_event(self, event_name, start_datetime, end_datetime, event_type_code, room_id, narrative):
        """Create a new school event
        Args:
            event_name (str): Event name
            start_datetime (str): Start datetime in string format (e.g. "2024-12-21 16:00:00")
            end_datetime (str): End datetime in string format (e.g. "2024-12-21 17:00:00")
            event_type_code (str): Event type code (e.g. "MEETING")
            room_id (int): Room Id code
            narrative (str): Event narrative
        Returns:
            href (str): Event href"""
        
        api_url = f"{self.rest_url}/school-events/"
        payload = {
            "request": {
                "schoolEvent": {
                    "entityType": "SchoolEvent",
                    "startDatetime": start_datetime,
                    "endDatetime": end_datetime,
                    "schoolEventType": {
                        "entityType": "SchoolEventType",
                        "href": f"/rest-v2/school-event-types/{event_type_code}"
                    },
                    "location": {
                        "entityType": "Room",
                        "href": f"/rest-v2/rooms/{room_id}"
                    },
                    "schoolEventName": event_name,
                    "narrative": narrative
                }
            }
        }
        data = self._post_request(api_url, payload)
        return data['schoolEvent']['href']

    def add_event_participant(self, event_href, participant_id, participant_type="Staff"):
        """Add a participant to an event.
        Args:
            event_href (str): Event href (returned when even created)
            participant_id (str): Participant ID
            participant_type (str): Type of participant (default is "Staff")
        Returns:
            bool: True if participant was added successfully, False otherwise
        """
        api_url = f"{self.rest_url}/eventParticipants"
        payload = {
            "request": {
                "eventParticipant": {
                    "entityType": "eventParticipant",
                    "event": {
                        "entityType": "SchoolEvent",
                        "href": event_href
                    },
                    "participant": {
                        "entityType": participant_type,
                        "href": f"/rest-v2/{participant_type}/{participant_id}"
                    }
                }
            }
        }
        self._post_request(api_url, payload)
        return True

    def delete_school_event(self, event_id):
        """Delete a school event
        Args:
            event_id (str): Event ID
        Returns:
            response: Response object"""
        
        api_url = f"{self.rest_url}/school-events/{event_id}"
        return self._delete_request(api_url)

    def list_repeating_school_events(self, event_type_code=None):
        """List repeating school events
        Args:
            event_type_code (str): Only return events of this type (e.g. "MEETING")
        Returns:
            list: Repeating school event dicts (entityType, href, ...)"""

        filters = {}
        if event_type_code:
            filters["schoolEventType.equals"] = f"/rest-v2/school-event-types/{event_type_code}"
        return self._list_request("repeating-school-events", "repeatingSchoolEvents", filters)

    def get_repeating_school_event(self, event_id):
        """Get a repeating school event by id
        Args:
            event_id (str): Repeating school event id
        Returns:
            dict: Repeating school event"""

        api_url = f"{self.rest_url}/repeating-school-events/{event_id}"
        return self._get_request(api_url)["repeatingSchoolEvent"]

    def list_timetable_slots(self, timetabled_object_href):
        """List timetable slots for a timetabled object (e.g. a repeating school event)
        Args:
            timetabled_object_href (str): Href of the object (e.g. "/rest-v2/repeating-school-events/4")
        Returns:
            list: Timetable slot dicts, fetched in full"""

        slots = self._list_request("timetable-slots", "timetableSlots",
                                   {"timetabledObject.equals": timetabled_object_href})
        return [self.get_full_record(slot, "timetableSlot", "startTime") for slot in slots]

    def get_timetable_slot(self, slot_id):
        """Get a timetable slot by id
        Args:
            slot_id (str): Timetable slot id
        Returns:
            dict: Timetable slot"""

        api_url = f"{self.rest_url}/timetable-slots/{slot_id}"
        return self._get_request(api_url)["timetableSlot"]

    def create_timetable_slot(self, timetabled_object, start_time, end_time, effective_date, end_date=None,
                              day_of_week=None, day_of_cycle=None, term_time_only=True, frequency=None,
                              academic_year=None):
        """Create a new timetable slot
        Args:
            timetabled_object (dict): {"entityType": ..., "href": ...} of the object being timetabled
            start_time (str): Start time (e.g. "09:00:00")
            end_time (str): End time (e.g. "10:00:00")
            effective_date (str): First date the slot applies (e.g. "2026-11-02")
            end_date (str): Last date the slot applies, None for open ended
            day_of_week (int): Day of week, as returned by Arbor on an existing slot
            day_of_cycle (int): Day of timetable cycle, as returned by Arbor on an existing slot
            term_time_only (bool): Only schedule in term time
            frequency (str): Frequency, as returned by Arbor on an existing slot
            academic_year (dict): {"entityType": "AcademicYear", "href": ...}
        Returns:
            href (str): Timetable slot href"""

        api_url = f"{self.rest_url}/timetable-slots"
        timetable_slot = {
            "entityType": "TimetableSlot",
            "timetabledObject": {
                "entityType": timetabled_object["entityType"],
                "href": timetabled_object["href"]
            },
            "startTime": start_time,
            "endTime": end_time,
            "effectiveDate": effective_date,
            "endDate": end_date,
            "termTimeOnly": term_time_only
        }
        # Only send the optional fields that have a value
        optional = {"dayOfWeek": day_of_week, "dayOfCycle": day_of_cycle, "frequency": frequency}
        timetable_slot.update({key: value for key, value in optional.items() if value is not None})
        if academic_year:
            timetable_slot["academicYear"] = {"entityType": "AcademicYear", "href": academic_year["href"]}

        data = self._post_request(api_url, {"request": {"timetableSlot": timetable_slot}})
        return data["timetableSlot"]["href"]

    def update_timetable_slot(self, slot_id, **fields):
        """Update fields on a timetable slot
        Args:
            slot_id (str): Timetable slot id
            **fields: Fields to change (e.g. startTime="09:15:00", endTime="10:15:00")
        Returns:
            response: Response json"""

        api_url = f"{self.rest_url}/timetable-slots/{slot_id}"
        payload = {
            "request": {
                "timetableSlot": {
                    "entityType": "TimetableSlot",
                    "href": f"/rest-v2/timetable-slots/{slot_id}",
                    **fields
                }
            }
        }
        return self._put_request(api_url, payload)

    def end_timetable_slot(self, slot_id, end_date):
        """End a timetable slot. Arbor removes the slot's scheduled events after the end date.
        Args:
            slot_id (str): Timetable slot id
            end_date (str): Last date the slot applies (e.g. "2026-11-01")
        Returns:
            response: Response json"""

        return self.update_timetable_slot(slot_id, endDate=end_date)

    def list_timetable_slot_locations(self, slot_href):
        """List locations for a timetable slot
        Args:
            slot_href (str): Timetable slot href
        Returns:
            list: Timetable slot location dicts, fetched in full"""

        records = self._list_request("timetable-slot-locations", "timetableSlotLocations",
                                     {"timetableSlot.equals": slot_href})
        return [self.get_full_record(record, "timetableSlotLocation", "effectiveDate") for record in records]

    def create_timetable_slot_location(self, slot_href, location, effective_date, end_date=None):
        """Add a location to a timetable slot
        Args:
            slot_href (str): Timetable slot href
            location (dict): {"entityType": "Room", "href": ...}
            effective_date (str): First date the location applies
            end_date (str): Last date the location applies, None for open ended
        Returns:
            href (str): Timetable slot location href"""

        api_url = f"{self.rest_url}/timetable-slot-locations"
        payload = {
            "request": {
                "timetableSlotLocation": {
                    "entityType": "TimetableSlotLocation",
                    "timetableSlot": {"entityType": "TimetableSlot", "href": slot_href},
                    "location": {"entityType": location["entityType"], "href": location["href"]},
                    "effectiveDate": effective_date,
                    "endDate": end_date
                }
            }
        }
        data = self._post_request(api_url, payload)
        return data["timetableSlotLocation"]["href"]

    def list_timetable_slot_staff(self, slot_href):
        """List staff for a timetable slot
        Args:
            slot_href (str): Timetable slot href
        Returns:
            list: Timetable slot staff dicts, fetched in full"""

        records = self._list_request("timetable-slot-staffs", "timetableSlotStaffs",
                                     {"timetableSlot.equals": slot_href})
        return [self.get_full_record(record, "timetableSlotStaff", "effectiveDate") for record in records]

    def create_timetable_slot_staff(self, slot_href, staff, effective_date, end_date=None):
        """Add a staff member to a timetable slot
        Args:
            slot_href (str): Timetable slot href
            staff (dict): {"entityType": "Staff", "href": ...}
            effective_date (str): First date the staff member attends
            end_date (str): Last date the staff member attends, None for open ended
        Returns:
            href (str): Timetable slot staff href"""

        api_url = f"{self.rest_url}/timetable-slot-staffs"
        payload = {
            "request": {
                "timetableSlotStaff": {
                    "entityType": "TimetableSlotStaff",
                    "timetableSlot": {"entityType": "TimetableSlot", "href": slot_href},
                    "staff": {"entityType": "Staff", "href": staff["href"]},
                    "effectiveDate": effective_date,
                    "endDate": end_date
                }
            }
        }
        data = self._post_request(api_url, payload)
        return data["timetableSlotStaff"]["href"]

    def list_timetable_slot_student_exceptions(self, slot_href):
        """List students excluded from a timetable slot
        Args:
            slot_href (str): Timetable slot href
        Returns:
            list: Timetable slot student exception dicts, fetched in full"""

        records = self._list_request("timetable-slot-student-exceptions", "timetableSlotStudentExceptions",
                                     {"timetableSlot.equals": slot_href})
        return [self.get_full_record(record, "timetableSlotStudentException", "effectiveDate") for record in records]

    def create_timetable_slot_student_exception(self, slot_href, student, effective_date, end_date=None):
        """Exclude a student from a timetable slot
        Args:
            slot_href (str): Timetable slot href
            student (dict): {"entityType": "Student", "href": ...}
            effective_date (str): First date the student is excluded
            end_date (str): Last date the student is excluded, None for open ended
        Returns:
            href (str): Timetable slot student exception href"""

        api_url = f"{self.rest_url}/timetable-slot-student-exceptions"
        payload = {
            "request": {
                "timetableSlotStudentException": {
                    "entityType": "TimetableSlotStudentException",
                    "timetableSlot": {"entityType": "TimetableSlot", "href": slot_href},
                    "student": {"entityType": "Student", "href": student["href"]},
                    "effectiveDate": effective_date,
                    "endDate": end_date
                }
            }
        }
        data = self._post_request(api_url, payload)
        return data["timetableSlotStudentException"]["href"]

    def list_registration_forms(self):
        """List registration forms
        Returns:
            list: Registration form dicts (entityType, href, ...)"""

        return self._list_request("registration-forms", "registrationForms")

    def list_academic_units(self, registration_form_href=None):
        """List academic units (classes and teaching groups)
        Args:
            registration_form_href (str): Only return units linked to this registration form
        Returns:
            list: Academic unit dicts (entityType, href, ...)"""

        filters = {}
        if registration_form_href:
            filters["registrationForm.equals"] = registration_form_href
        return self._list_request("academic-units", "academicUnits", filters)

    def list_clubs(self):
        """List clubs
        Returns:
            list: Club dicts (entityType, href, ...)"""

        return self._list_request("clubs", "clubs")
