import os
import sys
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("GoogleWorkspace")

def get_credentials():
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.json')
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Auth token not found at {token_path}. Please run setup_google_auth.py first.")
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    return Credentials.from_authorized_user_file(token_path, SCOPES)


# ─── CALENDAR TOOLS ─────────────────────────────────────────────────────────

@mcp.tool()
def get_upcoming_events(max_results: int = 10) -> str:
    """Fetch upcoming events from the user's Google Calendar."""
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."

        result = "Upcoming events:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            result += f"- {start}: {event['summary']}\n"
            if 'description' in event:
                result += f"  Description: {event['description']}\n"
        return result
    except Exception as e:
        return f"Error fetching calendar events: {str(e)}"

@mcp.tool()
def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Create a new event in Google Calendar.
    start_time and end_time must be ISO formatted strings like '2026-06-02T10:00:00-07:00'.
    """
    try:
        creds = get_credentials()
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time},
            'end': {'dateTime': end_time},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created successfully: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {str(e)}"


# ─── DRIVE TOOLS ────────────────────────────────────────────────────────────

@mcp.tool()
def search_drive(query: str, max_results: int = 10) -> str:
    """
    Search for files in Google Drive. 
    query should be a keyword. Example: 'Project Plan'
    """
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)

        # Standard keyword search over name and fullText
        q = f"name contains '{query}' or fullText contains '{query}'"
        results = service.files().list(
            q=q, pageSize=max_results, fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])

        if not items:
            return f"No files found matching '{query}'."
            
        result = "Found files:\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Type: {item['mimeType']})\n"
        return result
    except Exception as e:
        return f"Error searching drive: {str(e)}"

@mcp.tool()
def read_google_doc(document_id: str) -> str:
    """
    Read the content of a specific Google Doc using its document_id.
    You can get the document_id from search_drive.
    """
    try:
        creds = get_credentials()
        service = build('docs', 'v1', credentials=creds)

        doc = service.documents().get(documentId=document_id).execute()
        content = doc.get('body').get('content')
        
        text_parts = []
        for element in content:
            if 'paragraph' in element:
                elements = element.get('paragraph').get('elements')
                for elem in elements:
                    text_parts.append(elem.get('textRun', {}).get('content', ''))

        return "".join(text_parts)
    except Exception as e:
        return f"Error reading document: {str(e)}"

# ─── GMAIL TOOLS ────────────────────────────────────────────────────────────

@mcp.tool()
def read_unread_emails(max_results: int = 5) -> str:
    """Fetch the latest unread emails from the user's Gmail inbox."""
    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)

        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return "You have no unread emails."

        output = "Unread Emails:\n"
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            output += f"- From: {sender}\n  Subject: {subject}\n  Date: {date}\n\n"
            
        return output
    except Exception as e:
        return f"Error fetching emails: {str(e)}"

if __name__ == "__main__":
    # Start the FastMCP stdio server
    mcp.run()
