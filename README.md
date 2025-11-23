# Arbor Events

This repository contains a set of code to interact with the Arbor Education API to facilitate room booking and event management.

## Installation

To use this project, you need to install the required dependencies. You can install them using pip:

```sh
pip install azure-identity azure-keyvault-secrets polars request
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
