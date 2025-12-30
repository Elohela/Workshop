# Un Poco de Planning → Google Calendar Sync

Automatically scrape events from the Un Poco de Planning 2026 web app and sync them to your Google Calendar.

> **🚀 New to this tool? Check out the [QUICKSTART.md](./QUICKSTART.md) guide!**

## Features

- 🔐 Handles password-protected authentication
- 📥 Scrapes events from the planning web app
- 📅 Syncs events to Google Calendar
- 🔄 Smart event parsing with multiple strategies
- 📸 Debug screenshots and raw data export
- ⚡ Works without Google Calendar (saves to JSON)

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Run the Sync (Without Google Calendar)

The scraper works even without Google Calendar setup. Events will be saved to JSON files:

```bash
npm run sync
```

This will:
- Scrape events from https://unpocodeplanning.base44.app
- Save screenshots to `planning-app-screenshot.png`
- Save raw HTML to `page-content.html`
- Save extracted events to `extracted-events.json`
- Save parsed events to `events-to-sync.json`

### 3. Set Up Google Calendar (Optional)

To automatically sync to Google Calendar:

#### Option A: Service Account (Recommended for automation)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**
4. Create a **Service Account**:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Download the JSON key file
   - Save it as `credentials.json` in this directory
5. Share your calendar with the service account email
   - Open Google Calendar
   - Settings → Your calendar → Share with specific people
   - Add the service account email (found in credentials.json)
   - Give "Make changes to events" permission

#### Option B: OAuth 2.0 (For personal use)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create credentials → OAuth 2.0 Client ID
3. Download the credentials and save as `credentials.json`
4. You'll need to run an authorization flow (see below)

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed
```

### 5. Run Sync with Google Calendar

```bash
npm run sync
```

## Scripts

- `npm run sync` - Full sync: scrape events and sync to Google Calendar
- `npm run test-scrape` - Test scraper only (saves to JSON files)

## File Outputs

When you run the sync, these files are generated:

| File | Description |
|------|-------------|
| `planning-app-screenshot.png` | Screenshot of the planning app (for debugging) |
| `page-content.html` | Raw HTML content of the page |
| `extracted-events.json` | Raw events extracted from the page |
| `events-to-sync.json` | Parsed events ready for calendar (if no Google Calendar auth) |
| `scraped-data.json` | Backup of all scraped data |

## Customizing Event Parsing

The scraper uses multiple strategies to extract events from the page:

1. **Structured event elements** - Looks for elements with classes like `.event`, `.calendar-event`
2. **Table rows** - Parses table data as events
3. **List items** - Extracts events from list structures
4. **Raw content** - Falls back to extracting all page text

If the default parsing doesn't work for your page structure, you can customize the parsing logic in:
- `scraper.js` - Modify the `page.evaluate()` section
- `calendar-sync.js` - Modify the `parseEventData()` method

### Example: Custom Date Format

If your events use a specific date format, update the `parseDateTime()` method in `calendar-sync.js`:

```javascript
parseDateTime(dateStr, timeStr) {
  // Custom parsing for format like "15/01/2026"
  const [day, month, year] = dateStr.split('/');
  const date = new Date(year, month - 1, day);
  // ... rest of the logic
}
```

## Troubleshooting

### No events found?

1. Check `planning-app-screenshot.png` to see what the scraper sees
2. Look at `page-content.html` to examine the page structure
3. Review `extracted-events.json` to see what was extracted
4. Modify the scraper's extraction logic in `scraper.js` based on the actual HTML structure

### Authentication issues?

- Make sure the password "poco" is still correct
- Check if the login form structure has changed
- Look at the screenshot to see if the password was entered correctly

### Google Calendar sync failing?

- Verify your `credentials.json` is valid
- If using Service Account, ensure the calendar is shared with the service account email
- Check that Google Calendar API is enabled in your Google Cloud project
- Verify the calendar ID in `.env` is correct

### Running in headless mode issues?

If Puppeteer fails in headless mode, you can run with a visible browser:

```javascript
// In scraper.js, change:
headless: 'new'
// to:
headless: false
```

## Advanced Usage

### Sync to a specific calendar

```bash
# Set in .env
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
```

### Change timezone

```bash
# Set in .env
TIMEZONE=Europe/London
```

### Schedule automatic syncs

Use cron (Linux/Mac) or Task Scheduler (Windows):

```bash
# Run every day at 9 AM
0 9 * * * cd /path/to/project && npm run sync
```

## Project Structure

```
.
├── scraper.js           # Web scraper for the planning app
├── calendar-sync.js     # Google Calendar integration
├── sync-calendar.js     # Main sync script
├── package.json         # Dependencies
├── .env.example         # Environment variables template
├── README.md           # This file
└── credentials.json    # Google API credentials (not in git)
```

## Security Notes

- Never commit `credentials.json` or `.env` to version control
- The `.gitignore` file is configured to exclude these files
- Password is currently hardcoded as "poco" - consider moving to environment variable for production

## Development

### Testing the scraper

```bash
node scraper.js
```

### Testing calendar sync with sample data

```javascript
const { GoogleCalendarSync } = require('./calendar-sync');

const sampleEvents = [
  {
    title: "Test Event",
    date: "2026-01-15",
    time: "14:00",
    description: "Test description",
    location: "Test location"
  }
];

const sync = new GoogleCalendarSync();
await sync.authorize();
const parsed = sync.parseEventData(sampleEvents);
await sync.syncEvents(parsed);
```

## Contributing

Feel free to submit issues or pull requests!

## License

MIT
