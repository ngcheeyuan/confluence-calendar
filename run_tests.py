import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from confluence_calendar import ConfluenceCalendar
from models import CalendarEvent

# --- CONFIGURATION ---
load_dotenv()
CAL_NAME = os.getenv("CONFLUENCE_CAL_NAME")

# Define comprehensive test window
TEST_START = "2026-01-01T00:00:00Z"
TEST_END = "2026-12-31T23:59:59Z"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("comprehensive_test.log"), logging.StreamHandler()]
)

def verify_action(cal: ConfluenceCalendar, cid: str, uid: str, expected_exists: bool):
    """Checks the calendar state to confirm if an action was successful."""
    events = cal.get_events(cid, start=TEST_START, end=TEST_END).get('events', [])
    found = any(e['id'] == uid or e['id'].endswith(uid) for e in events)
    status = "PASS" if found == expected_exists else "FAIL"
    logging.info(f"[VERIFY] {status}: Event {uid} | Expected: {expected_exists} | Found: {found}")
    return found == expected_exists

def main():
    api = ConfluenceCalendar()
    pid, cid = api.get_calendar_ids(CAL_NAME)

    if not pid or not cid:
        logging.error(f"Aborting: Could not resolve IDs for {CAL_NAME}")
        return

    logging.info(f"=== STARTING COMPREHENSIVE TEST SUITE ON {CAL_NAME} ===")

    # --- SCENARIO 1: STANDALONE TIMED EVENT (CREATE -> EDIT -> DELETE) ---
    logging.info("SCENARIO 1: Timed Event Lifecycle")
    t_event = CalendarEvent(
        subCalendarId=pid, what="Timed Regression Task", 
        startDate="2026-01-15", startTime="09:00", endTime="10:00"
    )
    t_uid = api.create_event(t_event)
    if t_uid:
        verify_action(api, cid, t_uid, True)
        # Edit time and title
        api.edit_event(CalendarEvent(
            subCalendarId=pid, uid=t_uid, what="Timed Regression Task - MOVED", 
            startDate="2026-01-15", startTime="13:00", endTime="14:00",
            childSubCalendarId=cid, originalSubCalendarId=pid, originalEventSubCalendarId=cid
        ))
        logging.info("[ACTION] Event modified")
        api.delete_event(cid, t_uid, mode="SERIES")
        verify_action(api, cid, t_uid, False)

    # --- SCENARIO 2: ALL-DAY EVENT ---
    logging.info("SCENARIO 2: All-Day Event")
    ad_uid = api.create_event(CalendarEvent(
        subCalendarId=pid, what="Company Holiday", startDate="2026-01-20", allDayEvent=True
    ))
    verify_action(api, cid, ad_uid, True)

    # --- SCENARIO 3: RECURRING SERIES (SINGLE INSTANCE DELETION) ---
    logging.info("SCENARIO 3: Recurring Series Instance Deletion")
    m_uid = api.create_event(CalendarEvent(
        subCalendarId=pid, what="Daily Standup", startDate="2026-02-01", 
        startTime="08:30", endTime="09:00", rruleStr="FREQ=DAILY;INTERVAL=1"
    ))
    if m_uid:
        # Delete Feb 5th instance
        inst_ts = "2026-02-05T08:30:00.000Z"
        api.delete_event(cid, f"{inst_ts}/{m_uid}", mode="SINGLE", original_start=inst_ts)
        logging.info(f"[ACTION] Deleted single instance: {inst_ts}")

    # --- SCENARIO 4: ALL FUTURE INSTANCE DELETION ---
    logging.info("SCENARIO 4: Truncate Series")
    if m_uid:
        future_date = "2026-02-15"
        future_uid = f"{future_date}T08:30:00.000Z/{m_uid}"
        api.delete_event(cid, future_uid, mode="FUTURE", recur_until=future_date)
        logging.info(f"[ACTION] Series truncated from {future_date}")

    # --- SCENARIO 5: SMART GLOBAL CLEANUP ---
    logging.info("SCENARIO 5: Final Smart Cleanup")
    events = api.get_events(cid, start=TEST_START, end=TEST_END).get('events', [])
    unique_masters = {e['id'].split('/')[-1] for e in events}
    
    for uid in unique_masters:
        api.delete_event(cid, uid, mode="SERIES")
    
    final_count = len(api.get_events(cid, start=TEST_START, end=TEST_END).get('events', []))
    logging.info(f"Cleanup finished. Remaining events: {final_count}")

if __name__ == "__main__":
    main()
