const { google } = require('googleapis');
const fs = require('fs').promises;
const path = require('path');

/**
 * Google Calendar Sync Module
 * Handles authentication and syncing events to Google Calendar
 */
class GoogleCalendarSync {
  constructor() {
    this.calendar = null;
    this.auth = null;
  }

  /**
   * Authorize with Google Calendar API
   * Supports both OAuth2 and Service Account authentication
   */
  async authorize() {
    try {
      // Check if credentials file exists
      const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH || './credentials.json';

      let credentials;
      try {
        const credContent = await fs.readFile(credentialsPath, 'utf-8');
        credentials = JSON.parse(credContent);
      } catch (error) {
        console.error('\n❌ Error: credentials.json not found!');
        console.log('\nTo use Google Calendar API, you need to:');
        console.log('1. Go to https://console.cloud.google.com/');
        console.log('2. Create a new project or select existing one');
        console.log('3. Enable Google Calendar API');
        console.log('4. Create credentials (OAuth 2.0 Client ID or Service Account)');
        console.log('5. Download the credentials and save as credentials.json');
        console.log('\nFor now, events will be saved to events-to-sync.json instead.\n');
        return null;
      }

      // Check if it's a service account
      if (credentials.type === 'service_account') {
        this.auth = new google.auth.GoogleAuth({
          credentials,
          scopes: ['https://www.googleapis.com/auth/calendar']
        });
      } else {
        // OAuth2 flow
        const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
        const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

        // Check for token
        const tokenPath = './token.json';
        try {
          const token = await fs.readFile(tokenPath, 'utf-8');
          oAuth2Client.setCredentials(JSON.parse(token));
          this.auth = oAuth2Client;
        } catch (error) {
          console.log('\n⚠️  No saved token found. You need to authorize this app.');
          console.log('Run: node authorize.js to complete OAuth flow\n');
          return null;
        }
      }

      this.calendar = google.calendar({ version: 'v3', auth: this.auth });
      console.log('✓ Google Calendar API authorized successfully');
      return this.calendar;

    } catch (error) {
      console.error('Authorization error:', error.message);
      return null;
    }
  }

  /**
   * Parse event data and convert to Google Calendar format
   */
  parseEventData(eventData) {
    const events = [];

    for (const item of eventData) {
      try {
        if (item.type === 'raw-content') {
          // Try to parse the raw content for dates and events
          const lines = item.content.split('\n').filter(line => line.trim());
          // This is a fallback - actual parsing logic depends on the page structure
          continue;
        }

        let calendarEvent = null;

        if (item.title || item.date) {
          // Structured event data
          calendarEvent = this.createCalendarEvent(
            item.title || 'Untitled Event',
            item.date,
            item.time,
            item.description,
            item.location
          );
        } else if (item.type === 'table-row' && item.cells) {
          // Try to parse table row as event
          calendarEvent = this.parseTableRow(item.cells);
        } else if (item.type === 'list-item' && item.text) {
          // Try to parse list item as event
          calendarEvent = this.parseListItem(item.text);
        }

        if (calendarEvent) {
          events.push(calendarEvent);
        }
      } catch (error) {
        console.error('Error parsing event:', error.message);
      }
    }

    return events;
  }

  /**
   * Create a Google Calendar event object
   */
  createCalendarEvent(title, dateStr, timeStr, description, location) {
    // Parse date and time
    const dateTime = this.parseDateTime(dateStr, timeStr);

    if (!dateTime) {
      console.warn(`Could not parse date/time for event: ${title}`);
      return null;
    }

    const event = {
      summary: title,
      description: description || '',
      location: location || '',
      start: dateTime.start,
      end: dateTime.end,
      reminders: {
        useDefault: true
      }
    };

    return event;
  }

  /**
   * Parse date and time strings into Google Calendar format
   */
  parseDateTime(dateStr, timeStr) {
    try {
      // This is a basic parser - you may need to customize based on actual date format
      const date = new Date(dateStr);

      if (isNaN(date.getTime())) {
        return null;
      }

      let startDateTime, endDateTime;

      if (timeStr) {
        // Has specific time
        const [hours, minutes] = timeStr.split(':').map(s => parseInt(s));
        date.setHours(hours, minutes || 0);
        startDateTime = date.toISOString();

        // Default 1 hour duration
        const endDate = new Date(date);
        endDate.setHours(date.getHours() + 1);
        endDateTime = endDate.toISOString();

        return {
          start: { dateTime: startDateTime, timeZone: 'America/New_York' },
          end: { dateTime: endDateTime, timeZone: 'America/New_York' }
        };
      } else {
        // All-day event
        const dateOnly = date.toISOString().split('T')[0];
        return {
          start: { date: dateOnly },
          end: { date: dateOnly }
        };
      }
    } catch (error) {
      console.error('Date parsing error:', error.message);
      return null;
    }
  }

  /**
   * Parse a table row into an event
   */
  parseTableRow(cells) {
    // Assume format: [Date, Event, Time, Location, Description]
    // Adjust based on actual table structure
    if (cells.length >= 2) {
      return this.createCalendarEvent(
        cells[1] || 'Event',
        cells[0],
        cells[2] || '',
        cells[4] || '',
        cells[3] || ''
      );
    }
    return null;
  }

  /**
   * Parse a list item into an event
   */
  parseListItem(text) {
    // Try to extract date and event name from text
    // Format examples: "Jan 15 - Meeting", "2026-01-15: Conference"
    const datePattern = /(\d{4}-\d{2}-\d{2}|\w+ \d{1,2})/;
    const match = text.match(datePattern);

    if (match) {
      const dateStr = match[1];
      const title = text.replace(dateStr, '').replace(/^[\s:\-]+/, '').trim();
      return this.createCalendarEvent(title, dateStr, '', '', '');
    }

    return null;
  }

  /**
   * Sync events to Google Calendar
   */
  async syncEvents(events, calendarId = 'primary') {
    if (!this.calendar) {
      console.log('\n📝 Google Calendar not authorized. Saving events to file instead...');
      await fs.writeFile('events-to-sync.json', JSON.stringify(events, null, 2));
      console.log('✓ Events saved to events-to-sync.json');
      console.log('\nTo sync to Google Calendar:');
      console.log('1. Set up Google Calendar API credentials');
      console.log('2. Run the sync again\n');
      return { saved: events.length, synced: 0 };
    }

    console.log(`\nSyncing ${events.length} events to Google Calendar...`);

    let successCount = 0;
    let errorCount = 0;

    for (const event of events) {
      try {
        const result = await this.calendar.events.insert({
          calendarId: calendarId,
          requestBody: event
        });

        console.log(`✓ Added: ${event.summary}`);
        successCount++;
      } catch (error) {
        console.error(`✗ Failed to add "${event.summary}":`, error.message);
        errorCount++;
      }
    }

    console.log(`\n=== Sync Complete ===`);
    console.log(`✓ Successfully synced: ${successCount}`);
    console.log(`✗ Failed: ${errorCount}`);

    return { synced: successCount, failed: errorCount };
  }

  /**
   * List upcoming events from calendar
   */
  async listEvents(calendarId = 'primary', maxResults = 10) {
    if (!this.calendar) {
      console.error('Calendar not authorized');
      return [];
    }

    try {
      const response = await this.calendar.events.list({
        calendarId: calendarId,
        timeMin: new Date().toISOString(),
        maxResults: maxResults,
        singleEvents: true,
        orderBy: 'startTime'
      });

      return response.data.items || [];
    } catch (error) {
      console.error('Error listing events:', error.message);
      return [];
    }
  }
}

module.exports = { GoogleCalendarSync };
