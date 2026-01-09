import logging
import os
from typing import Optional, Tuple
from atlassian import Confluence
from requests.exceptions import HTTPError
from dotenv import load_dotenv

from models import CalendarEvent
from constants import (
    CAL_EVENT_PATH, SUB_CAL_LIST_PATH, SPACE_SEARCH_PATH, 
    ICS_IMPORT_PATH, USER_TIMEZONE, HEADERS
)

load_dotenv()

class ConfluenceCalendar:
    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.token = os.getenv("CONFLUENCE_TOKEN")
        self.confluence = Confluence(url=self.url, token=self.token)
        self.headers = HEADERS
        self.timezone = USER_TIMEZONE

    # --- SPACE & CALENDAR MANAGEMENT ---

    def get_available_spaces(self, query: str):
        """Searches for spaces matching the query string."""
        params = {
            "max-results": 5, 
            "pageSize": 5, 
            "type": "spacedesc,personalspacedesc", 
            "query": query
        }
        return self.confluence.request(method='GET', path=SPACE_SEARCH_PATH, params=params).json()

    def create_sub_calendar(self, name: str, space_key: str, description: str = "", color: str = "subcalendar-blue"):
        """Creates a new parent sub-calendar in a specific space."""
        params = {
            "type": "parent",
            "subCalendarId": "",
            "name": name,
            "description": description,
            "color": color,
            "spaceKey": space_key,
            "timeZoneId": self.timezone,
            "calendarContext": "myCalendars"
        }
        return self.confluence.request(method='PUT', path=SUB_CAL_LIST_PATH, params=params, headers=self.headers).json()

    def get_calendar_ids(self, target_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Finds parent and child IDs for the given name from the payload."""
        data = self.confluence.request(method='GET', path=SUB_CAL_LIST_PATH, headers=self.headers).json()
        for item in data.get('payload', []):
            parent_info = item.get('subCalendar', {})
            if parent_info.get('name', '').strip().lower() == target_name.strip().lower():
                parent_id = parent_info.get('id')
                children = item.get('childSubCalendars', [])
                child_id = children[0].get('subCalendar', {}).get('id') if children else parent_id
                return parent_id, child_id
        return None, None

    # --- ICS PORTABILITY ---

    def export_to_ics(self, sub_calendar_id: str) -> str:
        """Exports a sub-calendar to ICS string format using raw session."""
        path = f"rest/calendar-services/1.0/calendar/export/subcalendar/{sub_calendar_id}.ics"
        url = f"{self.url}/{path}"
        
        # Use session directly to avoid automatic 'Accept: application/json' headers
        response = self.confluence.session.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to export ICS: {response.status_code} - {response.text}")
            return ""
            
        return response.text

    def import_ics(self, space_key: str, ics_content: str, name: str = "", color: str = "subcalendar-gray"):
        """Imports ICS content to create/update a sub-calendar using multipart/form-data."""
        files = {'file_0': ('calendar.ics', ics_content, 'text/calendar')}
        data = {
            "decorator": "none",
            "color": color,
            "spaceKey": space_key,
            "name": name,
            "description": "",
            "calendarId": ""
        }
        url = f"{self.url}/{ICS_IMPORT_PATH}"
        # Use underlying session for multipart support
        response = self.confluence.session.post(
            url, data=data, files=files, headers={"X-Requested-With": "XMLHttpRequest"}
        )
        return response.status_code

    # --- EVENT OPERATIONS ---

    def get_events(self, sub_cal_id: str, start: str, end: str):
        params = {"subCalendarId": sub_cal_id, "start": start, "end": end, "userTimeZoneId": self.timezone}
        return self.confluence.request(method='GET', path=CAL_EVENT_PATH, params=params, headers=self.headers).json()

    def create_event(self, event: CalendarEvent):
        params = event.to_confluence_params(self.timezone)
        response = self.confluence.request(method='PUT', path=CAL_EVENT_PATH, params=params, headers=self.headers).json()
        return response['event']['id'] if response and 'event' in response else None

    def edit_event(self, event: CalendarEvent):
        params = event.to_confluence_params(self.timezone)
        return self.confluence.request(method='PUT', path=CAL_EVENT_PATH, params=params, headers=self.headers)

    def delete_event(self, sub_cal_id: str, uid: str, mode: str = "SERIES", recur_until: str = None, original_start: str = None):
        params = {"subCalendarId": sub_cal_id, "uid": uid}
        if mode == "SINGLE":
            params.update({"originalStart": original_start, "singleInstance": "true", "recurrenceId": ""})
        elif mode == "FUTURE":
            params.update({"recurUntil": recur_until})
        else:
            params.update({"editAllInRecurrenceSeries": "true"})
        try:
            return self.confluence.request(method='DELETE', path=CAL_EVENT_PATH, params=params, headers=self.headers)
        except HTTPError as e:
            if e.response.status_code in [404, 500]: return None
            raise e
