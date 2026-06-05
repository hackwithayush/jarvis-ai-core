import os
import sys

# Define the required scopes for Calendar and Drive (Read/Write)
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def authenticate():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("Error: Missing required packages. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        sys.exit(1)

    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found in the current directory.")
                print("Please download it from the Google Cloud Console and place it here.")
                sys.exit(1)
            
            print("Starting OAuth flow. A browser window should open...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Successfully authenticated and saved token.json!")

if __name__ == '__main__':
    print("=== JARVIS Google Workspace Auth Setup ===")
    authenticate()
    print("Done. JARVIS can now access your Google Workspace.")
