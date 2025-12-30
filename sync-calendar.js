#!/usr/bin/env node

/**
 * Main sync script
 * Scrapes events from Un Poco de Planning and syncs to Google Calendar
 */

require('dotenv').config();
const { scrapeEvents } = require('./scraper');
const { GoogleCalendarSync } = require('./calendar-sync');

async function main() {
  console.log('═══════════════════════════════════════════════════');
  console.log('  Un Poco de Planning → Google Calendar Sync');
  console.log('═══════════════════════════════════════════════════\n');

  try {
    // Step 1: Scrape events from the web app
    console.log('📥 Step 1: Scraping events from planning app...\n');
    const scrapedData = await scrapeEvents();

    if (!scrapedData || scrapedData.length === 0) {
      console.log('\n⚠️  No events found on the planning app.');
      console.log('Check the screenshot and page-content.html for debugging.\n');
      return;
    }

    console.log(`\n✓ Scraped ${scrapedData.length} items from planning app\n`);

    // Step 2: Initialize Google Calendar sync
    console.log('📅 Step 2: Initializing Google Calendar...\n');
    const calendarSync = new GoogleCalendarSync();
    await calendarSync.authorize();

    // Step 3: Parse and convert events
    console.log('\n🔄 Step 3: Parsing events...\n');
    const parsedEvents = calendarSync.parseEventData(scrapedData);

    if (parsedEvents.length === 0) {
      console.log('⚠️  Could not parse any events from scraped data.');
      console.log('The page structure might need custom parsing.');
      console.log('Check extracted-events.json to see the raw data.\n');

      // Still try to save raw data
      const fs = require('fs').promises;
      await fs.writeFile('scraped-data.json', JSON.stringify(scrapedData, null, 2));
      console.log('Raw scraped data saved to scraped-data.json\n');
      return;
    }

    console.log(`✓ Parsed ${parsedEvents.length} events\n`);

    // Step 4: Sync to Google Calendar
    console.log('☁️  Step 4: Syncing to Google Calendar...\n');
    const results = await calendarSync.syncEvents(
      parsedEvents,
      process.env.GOOGLE_CALENDAR_ID || 'primary'
    );

    // Summary
    console.log('\n═══════════════════════════════════════════════════');
    console.log('  Sync Summary');
    console.log('═══════════════════════════════════════════════════');
    console.log(`📊 Items scraped: ${scrapedData.length}`);
    console.log(`📅 Events parsed: ${parsedEvents.length}`);
    console.log(`✓ Successfully synced: ${results.synced || results.saved || 0}`);
    if (results.failed) {
      console.log(`✗ Failed: ${results.failed}`);
    }
    console.log('═══════════════════════════════════════════════════\n');

    if (!calendarSync.calendar) {
      console.log('💡 Tip: Set up Google Calendar API to automatically sync events.');
      console.log('See README.md for instructions.\n');
    }

  } catch (error) {
    console.error('\n❌ Error during sync:', error.message);
    console.error('\nStack trace:', error.stack);
    process.exit(1);
  }
}

// Run the sync
if (require.main === module) {
  main();
}

module.exports = { main };
