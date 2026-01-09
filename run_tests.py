import logging
import os
from dotenv import load_dotenv
from confluence_calendar import ConfluenceCalendar
from models import CalendarEvent

# --- CONFIGURATION ---
load_dotenv()
CAL_NAME = os.getenv("CONFLUENCE_CAL_NAME")
SPACE_QUERY = "co"  # Target query for space discovery

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

    logging.info("=== STARTING INTEGRATED COMPREHENSIVE TEST SUITE ===")

    # --- SCENARIO 1: SPACE DISCOVERY & CALENDAR PROVISIONING ---
    logging.info("SCENARIO 1: Space Discovery and Calendar Creation")
    spaces = api.get_available_spaces(SPACE_QUERY)
    try:
        space_key = spaces['group'][0]['result'][0]['key']
        logging.info(f"[ACTION] Found Space: {space_key}")
    except (KeyError, IndexError):
        logging.error("Aborting: Could not find a valid space for testing.")
        return

    # Create a fresh calendar for testing
    temp_cal_name = f"Test_{CAL_NAME}"
    create_res = api.create_sub_calendar(temp_cal_name, space_key, color="subcalendar-green2")
    pid = create_res.get('modifiedSubCalendarId')
    
    # Resolve IDs for the newly created calendar
    _, cid = api.get_calendar_ids(temp_cal_name)

    if not pid or not cid:
        logging.error(f"Aborting: Could not resolve IDs for {temp_cal_name}")
        return

    # --- SCENARIO 2: TIMED EVENT LIFECYCLE ---
    logging.info("SCENARIO 2: Timed Event Lifecycle")
    t_event = CalendarEvent(
        subCalendarId=pid, what="Timed Regression Task", 
        startDate="2026-01-15", startTime="09:00", endTime="10:00"
    )
    t_uid = api.create_event(t_event)
    if t_uid:
        verify_action(api, cid, t_uid, True)
        api.edit_event(CalendarEvent(
            subCalendarId=pid, uid=t_uid, what="Timed Regression Task - MOVED", 
            startDate="2026-01-15", startTime="13:00", endTime="14:00",
            childSubCalendarId=cid, originalSubCalendarId=pid, originalEventSubCalendarId=cid
        ))
        logging.info("[ACTION] Event modified")
        api.delete_event(cid, t_uid, mode="SERIES")
        verify_action(api, cid, t_uid, False)

    # --- SCENARIO 3: ALL-DAY EVENT ---
    logging.info("SCENARIO 3: All-Day Event")
    ad_uid = api.create_event(CalendarEvent(
        subCalendarId=pid, what="Company Holiday", startDate="2026-01-20", allDayEvent=True
    ))
    verify_action(api, cid, ad_uid, True)

    # --- SCENARIO 4: RECURRING SERIES (SINGLE & FUTURE DELETION) ---
    logging.info("SCENARIO 4: Recurring Series Management")
    m_uid = api.create_event(CalendarEvent(
        subCalendarId=pid, what="Daily Standup", startDate="2026-02-01", 
        startTime="08:30", endTime="09:00", rruleStr="FREQ=DAILY;INTERVAL=1"
    ))
    if m_uid:
        # Delete Feb 5th instance
        inst_ts = "2026-02-05T08:30:00.000Z"
        api.delete_event(cid, f"{inst_ts}/{m_uid}", mode="SINGLE", original_start=inst_ts)
        logging.info(f"[ACTION] Deleted single instance: {inst_ts}")

        # Truncate Series
        future_date = "2026-02-15"
        future_uid = f"{future_date}T08:30:00.000Z/{m_uid}"
        api.delete_event(cid, future_uid, mode="FUTURE", recur_until=future_date)
        logging.info(f"[ACTION] Series truncated from {future_date}")

    # --- SCENARIO 5: ICS PORTABILITY (EXPORT & IMPORT) ---
    logging.info("SCENARIO 5: ICS Export and Import Migration")
    ics_content = api.export_to_ics(pid)
    if ics_content:
        logging.info(f"[ACTION] Exported ICS ({len(ics_content)} bytes)")
        import_status = api.import_ics(space_key, ics_content, name=f"Imported_{temp_cal_name}")
        logging.info(f"[VERIFY] Import Status Code: {import_status}")

    # --- SCENARIO 6: SMART GLOBAL CLEANUP ---
    logging.info("SCENARIO 6: Final Smart Cleanup")
    events = api.get_events(cid, start=TEST_START, end=TEST_END).get('events', [])
    unique_masters = {e['id'].split('/')[-1] for e in events}
    
    for uid in unique_masters:
        api.delete_event(cid, uid, mode="SERIES")
    
    final_count = len(api.get_events(cid, start=TEST_START, end=TEST_END).get('events', []))
    logging.info(f"Cleanup finished. Remaining events on {temp_cal_name}: {final_count}")

if __name__ == "__main__":
    main()
