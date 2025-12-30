# Quick Start Guide

Get your planning events into Google Calendar in 3 easy steps!

## Step 1: Install Dependencies

```bash
npm install
```

## Step 2: Get Your Events

### Option A: Interactive Helper (Recommended)

```bash
npm start
```

The interactive helper will guide you through:
- Choosing a scraping method
- Extracting events from the planning app
- Syncing to Google Calendar

### Option B: Manual Process

1. **Get the HTML content:**
   - Open https://unpocodeplanning.base44.app in your browser
   - Enter password: `poco`
   - Right-click → "View Page Source" (or press Ctrl+U)
   - Copy all HTML content
   - Save as `manual-page.html` in this directory

2. **Extract events:**
   ```bash
   node simple-scraper.js manual-page.html
   ```

3. **Review extracted data:**
   - Check `extracted-events.json` to see what was found
   - Check `page-content.html` to see the raw HTML

## Step 3: Sync to Google Calendar (Optional)

### Without Google Calendar Setup
Events will be saved to `events-to-sync.json` - you can manually add them to your calendar.

### With Google Calendar Setup

1. **Get Google Calendar API credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project
   - Enable "Google Calendar API"
   - Create a Service Account
   - Download `credentials.json`
   - Place it in this directory

2. **Share your calendar:**
   - Open Google Calendar
   - Settings → Your calendar → Share with specific people
   - Add the service account email (from credentials.json)
   - Give "Make changes to events" permission

3. **Run the sync:**
   ```bash
   npm run sync
   ```

## Troubleshooting

### "No events found"
- Check `planning-app-screenshot.png` (if using automatic method)
- Review `page-content.html` to see what was scraped
- Look at `extracted-events.json` to see raw extracted data
- The page structure might need custom parsing

### "Cannot find Chrome"
- Use the manual method instead: `npm start` → choose option 2
- Or install Chrome/Chromium for automatic scraping

### "Google Calendar sync failed"
- Events are still saved in `events-to-sync.json`
- Set up credentials later and re-run
- Or manually import the events from the JSON file

## File Outputs

| File | Description |
|------|-------------|
| `extracted-events.json` | Raw events extracted from the page |
| `events-to-sync.json` | Parsed events ready for calendar |
| `page-content.html` | Full HTML of the planning page |
| `planning-app-screenshot.png` | Screenshot (automatic method only) |

## Need Help?

See [README.md](./README.md) for detailed documentation and customization options.
