import logging
import os
from typing import Optional, Set, Tuple
from atlassian import Confluence
from requests.exceptions import HTTPError
from dotenv import load_dotenv

from models import CalendarEvent
from constants import CAL_EVENT_PATH, SUB_CAL_LIST_PATH, USER_TIMEZONE, HEADERS

load_dotenv()

class ConfluenceCalendar:
    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.token = os.getenv("CONFLUENCE_TOKEN")
        self.confluence = Confluence(url=self.url, token=self.token)
        self.headers = HEADERS
        self.timezone = USER_TIMEZONE
        self.cal_path = CAL_EVENT_PATH

    def get_calendar_ids(self, target_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Finds parent and child IDs for the given name."""
        data = self.confluence.request(method='GET', path=SUB_CAL_LIST_PATH, headers=self.headers).json()
        for item in data.get('payload', []):
            parent_info = item.get('subCalendar', {})
            if parent_info.get('name', '').strip().lower() == target_name.strip().lower():
                parent_id = parent_info.get('id')
                children = item.get('childSubCalendars', [])
                child_id = children[0].get('subCalendar', {}).get('id') if children else parent_id
                return parent_id, child_id
        return None, None

    def get_events(self, sub_cal_id: str, start: str, end: str):
        """
        Retrieves events for the specified ID within a given timeframe.
        """
        params = {
            "subCalendarId": sub_cal_id, 
            "start": start, 
            "end": end, 
            "userTimeZoneId": self.timezone
        }
        response = self.confluence.request(
            method='GET', 
            path=self.cal_path, 
            params=params, 
            headers=self.headers
        )
        return response.json()


    def create_event(self, event: CalendarEvent):
        params = event.to_confluence_params(self.timezone)
        response = self.confluence.request(method='PUT', path=self.cal_path, params=params, headers=self.headers).json()
        return response['event']['id'] if response and 'event' in response else None

    def edit_event(self, event: CalendarEvent):
        params = event.to_confluence_params(self.timezone)
        return self.confluence.request(method='PUT', path=self.cal_path, params=params, headers=self.headers)

    def delete_event(self, sub_cal_id: str, uid: str, mode: str = "SERIES", recur_until: str = None, original_start: str = None):
        params = {"subCalendarId": sub_cal_id, "uid": uid}
        if mode == "SINGLE":
            params.update({"originalStart": original_start, "singleInstance": "true", "recurrenceId": ""})
        elif mode == "FUTURE":
            params.update({"recurUntil": recur_until})
        else:
            params.update({"editAllInRecurrenceSeries": "true"})
        
        try:
            return self.confluence.request(method='DELETE', path=self.cal_path, params=params, headers=self.headers)
        except HTTPError as e:
            if e.response.status_code in [404, 500]: return None
            raise e
