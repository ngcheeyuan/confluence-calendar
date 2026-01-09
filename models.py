from typing import Optional
from pydantic import BaseModel, Field

class CalendarEvent(BaseModel):
    title: str = Field(..., alias="what")
    startDate: str
    endDate: Optional[str] = None
    startTime: str = ""
    endTime: str = ""
    allDayEvent: bool = False
    rruleStr: str = ""
    editAllInRecurrenceSeries: bool = True
    subCalendarId: str
    uid: Optional[str] = None
    childSubCalendarId: Optional[str] = None
    originalSubCalendarId: Optional[str] = None
    originalEventSubCalendarId: Optional[str] = None

    def to_confluence_params(self, user_timezone: str):
        """Maps model fields to Confluence API parameters."""
        data = {
            "confirmRemoveInvalidUsers": "false",
            "eventType": "other",
            "subCalendarId": self.subCalendarId,
            "what": self.title,
            "startDate": self.startDate,
            "endDate": self.endDate or self.startDate,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "allDayEvent": str(self.allDayEvent).lower(),
            "rruleStr": self.rruleStr,
            "editAllInRecurrenceSeries": str(self.editAllInRecurrenceSeries).lower(),
            "userTimeZoneId": user_timezone
        }
        if self.uid:
            data.update({
                "uid": self.uid,
                "childSubCalendarId": self.childSubCalendarId,
                "originalSubCalendarId": self.originalSubCalendarId,
                "originalEventSubCalendarId": self.originalEventSubCalendarId
            })
        return data
