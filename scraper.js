const puppeteer = require('puppeteer');
const fs = require('fs').promises;

/**
 * Scrapes events from the Un Poco de Planning web app
 * @returns {Promise<Array>} Array of event objects
 */
async function scrapeEvents() {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();

    // Set viewport and user agent
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');

    console.log('Navigating to planning app...');
    await page.goto('https://unpocodeplanning.base44.app', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    // Wait a bit for the page to fully load
    await page.waitForTimeout(2000);

    // Check if there's a password field
    const passwordField = await page.$('input[type="password"]');

    if (passwordField) {
      console.log('Password protection detected, entering password...');
      await page.type('input[type="password"]', 'poco');

      // Look for submit button (try various selectors)
      const submitButton = await page.$('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Enter")');
      if (submitButton) {
        await submitButton.click();
      } else {
        // If no button found, try pressing Enter
        await page.keyboard.press('Enter');
      }

      // Wait for navigation after password submission
      await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }).catch(() => {
        console.log('No navigation detected, continuing...');
      });

      await page.waitForTimeout(2000);
    }

    // Take a screenshot for debugging
    await page.screenshot({ path: 'planning-app-screenshot.png', fullPage: true });
    console.log('Screenshot saved to planning-app-screenshot.png');

    // Get the page content
    const content = await page.content();
    await fs.writeFile('page-content.html', content);
    console.log('Page content saved to page-content.html');

    // Try to extract events from the page
    const events = await page.evaluate(() => {
      const extractedEvents = [];

      // Try multiple strategies to find events

      // Strategy 1: Look for calendar-like structures
      const calendarEvents = document.querySelectorAll('.event, .calendar-event, [class*="event"], [data-event]');
      calendarEvents.forEach(eventEl => {
        const eventData = {
          title: eventEl.querySelector('.title, .event-title, h3, h4')?.textContent?.trim() || '',
          date: eventEl.querySelector('.date, .event-date, time')?.textContent?.trim() || '',
          time: eventEl.querySelector('.time, .event-time')?.textContent?.trim() || '',
          description: eventEl.querySelector('.description, .event-description, p')?.textContent?.trim() || '',
          location: eventEl.querySelector('.location, .event-location')?.textContent?.trim() || '',
          rawHTML: eventEl.outerHTML
        };
        if (eventData.title || eventData.date) {
          extractedEvents.push(eventData);
        }
      });

      // Strategy 2: Look for table rows that might contain events
      const tableRows = document.querySelectorAll('table tr, tbody tr');
      tableRows.forEach(row => {
        const cells = row.querySelectorAll('td, th');
        if (cells.length >= 2) {
          const rowText = Array.from(cells).map(cell => cell.textContent.trim());
          if (rowText.some(text => text && text.length > 0)) {
            extractedEvents.push({
              type: 'table-row',
              cells: rowText,
              rawHTML: row.outerHTML
            });
          }
        }
      });

      // Strategy 3: Look for list items
      const listItems = document.querySelectorAll('li, .list-item, [class*="item"]');
      listItems.forEach(item => {
        const text = item.textContent.trim();
        if (text.length > 5 && !text.includes('©') && !text.includes('2024')) {
          extractedEvents.push({
            type: 'list-item',
            text: text,
            rawHTML: item.outerHTML
          });
        }
      });

      // Get all text content if no events found
      if (extractedEvents.length === 0) {
        const bodyText = document.body.innerText;
        return [{
          type: 'raw-content',
          content: bodyText,
          note: 'No structured events found, returning page text'
        }];
      }

      return extractedEvents;
    });

    console.log(`\nExtracted ${events.length} potential events`);

    // Save raw extracted data
    await fs.writeFile('extracted-events.json', JSON.stringify(events, null, 2));
    console.log('Raw event data saved to extracted-events.json');

    return events;

  } catch (error) {
    console.error('Error during scraping:', error);
    throw error;
  } finally {
    await browser.close();
    console.log('Browser closed');
  }
}

// Run if executed directly
if (require.main === module) {
  scrapeEvents()
    .then(events => {
      console.log('\n=== SCRAPING COMPLETE ===');
      console.log(`Total items extracted: ${events.length}`);
      console.log('\nFirst few items:');
      console.log(JSON.stringify(events.slice(0, 3), null, 2));
    })
    .catch(error => {
      console.error('Failed to scrape events:', error);
      process.exit(1);
    });
}

module.exports = { scrapeEvents };
