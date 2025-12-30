#!/usr/bin/env node

/**
 * Setup and Sync Helper
 * Provides multiple methods to scrape and sync events
 */

const fs = require('fs').promises;
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function ask(question) {
  return new Promise(resolve => {
    rl.question(question, resolve);
  });
}

async function main() {
  console.log('\n═══════════════════════════════════════════════════');
  console.log('  Un Poco de Planning → Google Calendar Sync');
  console.log('  Setup & Sync Helper');
  console.log('═══════════════════════════════════════════════════\n');

  console.log('This tool helps you sync events from the planning app to Google Calendar.\n');
  console.log('Choose your method:\n');
  console.log('1. Automatic (using Puppeteer - requires Chrome/Chromium)');
  console.log('2. Manual (copy HTML from browser)');
  console.log('3. Direct input (paste events as JSON)');
  console.log('4. Exit\n');

  const choice = await ask('Enter your choice (1-4): ');

  switch (choice.trim()) {
    case '1':
      await automaticMethod();
      break;
    case '2':
      await manualMethod();
      break;
    case '3':
      await directInputMethod();
      break;
    case '4':
      console.log('\nExiting...\n');
      rl.close();
      return;
    default:
      console.log('\nInvalid choice. Exiting...\n');
      rl.close();
      return;
  }

  // Ask if they want to sync to Google Calendar
  const shouldSync = await ask('\nDo you want to sync these events to Google Calendar? (y/n): ');

  if (shouldSync.toLowerCase() === 'y' || shouldSync.toLowerCase() === 'yes') {
    await syncToCalendar();
  } else {
    console.log('\nEvents saved to events-to-sync.json');
    console.log('You can manually review and sync them later.\n');
  }

  rl.close();
}

async function automaticMethod() {
  console.log('\n📦 Automatic Method\n');
  console.log('This requires:');
  console.log('- Chrome or Chromium browser installed');
  console.log('- Puppeteer Chrome binary downloaded\n');

  const proceed = await ask('Do you want to proceed? (y/n): ');

  if (proceed.toLowerCase() !== 'y' && proceed.toLowerCase() !== 'yes') {
    console.log('\nReturning to menu...');
    return await main();
  }

  try {
    console.log('\nRunning automated scraper...\n');
    const { scrapeEvents } = require('./scraper');
    const events = await scrapeEvents();

    console.log(`✓ Scraped ${events.length} items`);
    console.log('✓ Check planning-app-screenshot.png to verify\n');

    return events;
  } catch (error) {
    console.error('\n❌ Automatic method failed:', error.message);
    console.log('\nTry the manual method instead.\n');

    const tryManual = await ask('Switch to manual method? (y/n): ');
    if (tryManual.toLowerCase() === 'y' || tryManual.toLowerCase() === 'yes') {
      return await manualMethod();
    }
  }
}

async function manualMethod() {
  console.log('\n📋 Manual Method\n');
  console.log('Follow these steps:\n');
  console.log('1. Open https://unpocodeplanning.base44.app in your browser');
  console.log('2. Enter password: poco');
  console.log('3. Once logged in, right-click anywhere on the page');
  console.log('4. Select "View Page Source" (or press Ctrl+U / Cmd+Option+U)');
  console.log('5. Copy ALL the HTML content');
  console.log('6. Save it to a file named "manual-page.html" in this directory\n');

  console.log('Press Enter when you have saved the file...');
  await ask('');

  try {
    const html = await fs.readFile('manual-page.html', 'utf-8');
    console.log('\n✓ Found manual-page.html');

    const { scrapeEventsSimple } = require('./simple-scraper');
    const events = await scrapeEventsSimple(html);

    console.log(`✓ Extracted ${events.length} items\n`);
    await fs.writeFile('extracted-events.json', JSON.stringify(events, null, 2));

    return events;
  } catch (error) {
    console.error('\n❌ Could not read manual-page.html:', error.message);
    console.log('\nMake sure the file is saved in the current directory.\n');
  }
}

async function directInputMethod() {
  console.log('\n⌨️  Direct Input Method\n');
  console.log('Paste your events in this format (one per line):\n');
  console.log('Date | Event Name | Time | Location | Description');
  console.log('Example: 2026-01-15 | Team Meeting | 14:00 | Office | Quarterly review\n');

  console.log('Paste your events below (press Ctrl+D or type "DONE" when finished):\n');

  const events = [];
  const lines = [];

  // Read multiple lines
  rl.on('line', (line) => {
    if (line.trim() === 'DONE') {
      rl.close();
    } else {
      lines.push(line);
    }
  });

  await new Promise(resolve => {
    rl.on('close', resolve);
  });

  // Parse the lines
  for (const line of lines) {
    if (line.trim().length === 0) continue;

    const parts = line.split('|').map(p => p.trim());
    if (parts.length >= 2) {
      events.push({
        date: parts[0] || '',
        title: parts[1] || '',
        time: parts[2] || '',
        location: parts[3] || '',
        description: parts[4] || ''
      });
    }
  }

  if (events.length > 0) {
    console.log(`\n✓ Parsed ${events.length} events\n`);
    await fs.writeFile('extracted-events.json', JSON.stringify(events, null, 2));
  }

  return events;
}

async function syncToCalendar() {
  console.log('\n☁️  Syncing to Google Calendar...\n');

  try {
    const { GoogleCalendarSync } = require('./calendar-sync');
    const sync = new GoogleCalendarSync();

    await sync.authorize();

    // Read extracted events
    const eventsData = await fs.readFile('extracted-events.json', 'utf-8');
    const events = JSON.parse(eventsData);

    const parsed = sync.parseEventData(events);
    const results = await sync.syncEvents(parsed);

    console.log('\n✓ Sync complete!');
    console.log(`  Synced: ${results.synced || results.saved || 0} events\n`);

  } catch (error) {
    console.error('\n❌ Sync failed:', error.message);
    console.log('\nEvents are saved in events-to-sync.json');
    console.log('You can set up Google Calendar later and re-run the sync.\n');
  }
}

if (require.main === module) {
  main().catch(error => {
    console.error('Error:', error);
    rl.close();
    process.exit(1);
  });
}
