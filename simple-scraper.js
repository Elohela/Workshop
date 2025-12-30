const cheerio = require('cheerio');
const https = require('https');
const fs = require('fs').promises;

/**
 * Simple scraper using cheerio (no browser required)
 * For password-protected sites, you may need to manually copy the HTML
 */
async function fetchPage(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (response) => {
      let data = '';

      response.on('data', (chunk) => {
        data += chunk;
      });

      response.on('end', () => {
        resolve(data);
      });
    }).on('error', (error) => {
      reject(error);
    });
  });
}

async function scrapeEventsSimple(htmlContent) {
  const $ = cheerio.load(htmlContent);
  const events = [];

  console.log('Analyzing HTML content...');

  // Strategy 1: Look for event-like elements
  $('.event, .calendar-event, [class*="event"]').each((i, elem) => {
    const $elem = $(elem);
    events.push({
      type: 'event-element',
      title: $elem.find('.title, .event-title, h3, h4').text().trim(),
      date: $elem.find('.date, .event-date, time').text().trim(),
      time: $elem.find('.time, .event-time').text().trim(),
      description: $elem.find('.description, .event-description, p').text().trim(),
      location: $elem.find('.location, .event-location').text().trim(),
      html: $elem.html()
    });
  });

  // Strategy 2: Look for tables
  $('table tr').each((i, elem) => {
    const $elem = $(elem);
    const cells = [];
    $elem.find('td, th').each((j, cell) => {
      cells.push($(cell).text().trim());
    });
    if (cells.length >= 2 && cells.some(c => c.length > 0)) {
      events.push({
        type: 'table-row',
        cells: cells,
        html: $elem.html()
      });
    }
  });

  // Strategy 3: Look for lists
  $('ul li, ol li').each((i, elem) => {
    const $elem = $(elem);
    const text = $elem.text().trim();
    if (text.length > 5 && !text.includes('©')) {
      events.push({
        type: 'list-item',
        text: text,
        html: $elem.html()
      });
    }
  });

  // Strategy 4: Look for divs with date patterns
  $('div, section, article').each((i, elem) => {
    const $elem = $(elem);
    const text = $elem.text().trim();

    // Look for date patterns like "2026-01-15" or "Jan 15" or "15/01/2026"
    const datePatterns = [
      /\d{4}-\d{2}-\d{2}/,
      /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}/i,
      /\d{1,2}\/\d{1,2}\/\d{4}/
    ];

    for (const pattern of datePatterns) {
      if (pattern.test(text)) {
        // Extract heading if available
        const heading = $elem.find('h1, h2, h3, h4, h5, h6').first().text().trim();
        if (heading && heading.length > 0) {
          events.push({
            type: 'date-container',
            title: heading,
            content: text,
            html: $elem.html()
          });
          break;
        }
      }
    }
  });

  return events;
}

async function main() {
  try {
    console.log('Simple Scraper - Un Poco de Planning');
    console.log('=====================================\n');

    // Try to fetch the page directly
    console.log('Attempting to fetch page...');
    try {
      const html = await fetchPage('https://unpocodeplanning.base44.app');
      await fs.writeFile('page-content.html', html);
      console.log('✓ Page content saved to page-content.html\n');

      // Parse events
      const events = await scrapeEventsSimple(html);
      await fs.writeFile('extracted-events.json', JSON.stringify(events, null, 2));

      console.log(`✓ Extracted ${events.length} potential events`);
      console.log('✓ Saved to extracted-events.json\n');

      if (events.length > 0) {
        console.log('First few items:');
        console.log(JSON.stringify(events.slice(0, 3), null, 2));
      }

    } catch (error) {
      console.log('⚠️  Could not fetch directly (password protection or CORS)');
      console.log('\nManual option:');
      console.log('1. Open https://unpocodeplanning.base44.app in your browser');
      console.log('2. Enter password: poco');
      console.log('3. Right-click → "View Page Source" or press Ctrl+U');
      console.log('4. Copy all the HTML and save it as "manual-page.html"');
      console.log('5. Run: node simple-scraper.js manual-page.html\n');
    }

  } catch (error) {
    console.error('Error:', error.message);
  }
}

// If HTML file provided as argument
if (process.argv[2]) {
  const htmlFile = process.argv[2];
  console.log(`Reading from ${htmlFile}...`);

  fs.readFile(htmlFile, 'utf-8')
    .then(async (html) => {
      const events = await scrapeEventsSimple(html);
      await fs.writeFile('extracted-events.json', JSON.stringify(events, null, 2));
      console.log(`✓ Extracted ${events.length} events from ${htmlFile}`);
      console.log('✓ Saved to extracted-events.json\n');

      if (events.length > 0) {
        console.log('First few items:');
        console.log(JSON.stringify(events.slice(0, 3), null, 2));
      }
    })
    .catch(err => {
      console.error('Error reading file:', err.message);
    });
} else if (require.main === module) {
  main();
}

module.exports = { scrapeEventsSimple };
