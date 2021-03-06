""""
    ./notion_sync.py

    This python script aims to synchronize a Notion database with the Google Calendar API, in both directions.
"""
from notion_client import *
import datetime
from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import List
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar


@dataclass
class SyncEvent:
    icon_emoji: str
    title: str
    date_start: datetime.datetime
    date_end: datetime.datetime
    done: bool
    tags: List[str]


def notion_event_to_sync_event(notion_event: dict) -> SyncEvent:
    """Transforms a Notion event to a SyncEvent

    Args:
        notion_events (dict): A Notion event dictionary ("results" key of the response))

    Returns:
        SyncEvent: A SyncEvent object
    """
    x = SyncEvent(
        icon_emoji=notion_event["icon"]["emoji"],
        title=notion_event["properties"]["Calendar"]["title"][0]["plain_text"],
        date_start=notion_event["properties"]["Date"]["date"]["start"],
        date_end=notion_event["properties"]["Date"]["date"]["end"]
        if notion_event["properties"]["Date"]["date"]["end"]
        else notion_event["properties"]["Date"]["date"]["start"],
        done=notion_event["properties"]["Done"]["checkbox"],
        tags=[x["plain_text"] for x in notion_event["properties"]["Tags"]["multi_select"] if "plain_text" in x.keys()],
    )
    if x.tags == []:
        x.tags = ["Unknown"]
    return x


def calendar_event_to_sync_event(calendar_event: Event) -> SyncEvent:
    """Transforms a Google Calendar event to a SyncEvent

    Args:
        calendar_event (Event): A Google Calendar event

    Returns:
        SyncEvent: A SyncEvent object
    """
    return SyncEvent(
        icon_emoji="",
        title=calendar_event.summary,
        date_start=calendar_event.start.isoformat(),
        date_end=calendar_event.end.isoformat(),
        done=False,
        tags=["Unknown"],
    )


def fetch_notion_events(cli: NotionAPIClient, database_id: str) -> List[SyncEvent]:
    """Fetches all events in the Notion database and turns them in SyncEvents
    ready to be synchronized

    Args:
        cli (NotionAPIClient): A NotionAPIClient object
        database_id (str): The Notion database ID

    Returns:
        List[SyncEvent]: A list of SyncEvents
    """

    # Creating query
    query = {
        "filter": {
            "and": [
                {"property": "Done", "checkbox": {"equals": False}},
            ]
        }
    }

    return [notion_event_to_sync_event(x) for x in cli.query_database(query, database_id)["results"]]


def fetch_calendar_events(calendar: GoogleCalendar) -> List[SyncEvent]:
    """Fetches all events in the Google Calendar and turns them in SyncEvents
    ready to be synchronized

    Args:
        calendar (GoogleCalendar): GoogleCalendar instance from gcsa.google_calendar

    Returns:
        List[SyncEvent]: A list of SyncEvents
    """

    # Fetching events from today, more or yesterday
    return [
        calendar_event_to_sync_event(x)
        for x in calendar[(datetime.datetime.today() - datetime.timedelta(days=1)) :: "updated"]
    ]


def push_events_to_notion(
    cli: NotionAPIClient, database_id: str, pushed_events: List[SyncEvent], ignored_events: List[str]
) -> None:
    """Pushes the Google calendar events to the Notion database

    Args:
        cli (NotionAPIClient): the Notion client
        database_id (str): the database id
        pushed_events (List[SyncEvent]): the list of events to push
        ignored_events (List[str]): the list of events to ignore
    """

    for e in pushed_events:
        # We are ignoring events already in the database
        # In Notion emojis are not in the title but when I push back to
        # Google Agenda, they are in the title which means I have to test
        # the title and the title without emojis to check
        if not any([e.title in x for x in ignored_events]) and not any(
            [e.title.split(" ")[1] in x for x in ignored_events]
        ):

            # Creating the page
            notion_page = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Calendar": {"title": [{"text": {"content": e.title}}]},
                    "Done": {"checkbox": e.done},
                    "Date": {"date": {"start": e.date_start, "end": e.date_end}},
                    "Tags": {"multi_select": [{"name": x} for x in e.tags]},
                },
                "icon": {"type": "emoji", "emoji": "???"},
            }

            # Pushing the page
            cli.create_page(notion_page)
            print("--> push: {}".format(e.title))
        else:
            print(f"--> ignore: {e.title}")


def push_events_to_calendar(
    calendar: GoogleCalendar, pushed_events: List[SyncEvent], ignored_events: List[str]
) -> None:
    """Pushes the Notion events to the Google Calendar

    Args:
        calendar (GoogleCalendar): GoogleCalendar instance from gcsa.google_calendar
        pushed_events (List[SyncEvent]): the list of events to push
        ignored_events (List[str]): the list of events to ignore
    """

    for e in pushed_events:
        # We are ignoring events already in the calendar
        if not any([e.title in x for x in ignored_events]) and not any(
            [e.title in x.split(" ") for x in ignored_events]
        ):
            # Creating the event
            calendar_event = Event(
                start=datetime.datetime.fromisoformat(e.date_start),
                end=datetime.datetime.fromisoformat(e.date_end),
                summary=str(e.icon_emoji + " " + e.title),
                description=",".join(e.tags),
            )
            calendar.add_event(calendar_event)
            print("--> push: {}".format(e.title))
        else:
            print(f"--> ignore: {e.title}")


def main():

    # Loading the .env file
    load_dotenv()
    token = os.getenv("TOKEN")
    database_id = os.getenv("DATABASE_ID")

    # Getting Notion events from the database
    print("[Fetching Notion events...]")
    client = NotionAPIClient(token)
    notion_events = fetch_notion_events(client, database_id)
    print("--> {} events found".format(len(notion_events)))

    # Getting Google Calendar events
    print("[Fetching Google Calendar events...]")
    calendar = GoogleCalendar(credentials_path="./.credentials/credentials.json", calendar="primary")
    calendar_events = fetch_calendar_events(calendar)
    print("--> {} events found".format(len(calendar_events)))

    # Synchronizing events
    print("[Pushing events to Notion...]")
    push_events_to_notion(client, database_id, calendar_events, [e.title for e in notion_events])
    print("[Pushing events to Google Calendar...]")
    push_events_to_calendar(calendar, notion_events, [e.title for e in calendar_events])

    print("[Synchronization completed.]")


if __name__ == "__main__":
    main()
