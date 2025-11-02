#!/usr/bin/env python3
"""
Script to get best times for a swimmer using SwimCloud.

Directly accesses the personal bests page which is simpler and more reliable.
"""

import time as _time
import sys
import argparse
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs

# Path to swimmers configuration file
SWIMMERS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'swimmers.json')


def load_swimmers_config():
    """Load swimmers configuration from JSON file."""
    if not os.path.exists(SWIMMERS_CONFIG_FILE):
        return {}

    try:
        with open(SWIMMERS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load swimmers config: {e}")
        return {}


def list_configured_swimmers():
    """List all configured swimmers."""
    swimmers = load_swimmers_config()

    if not swimmers:
        print("No swimmers configured.")
        print(f"\nTo configure swimmers, create a file: {SWIMMERS_CONFIG_FILE}")
        print('Example content:')
        print('{')
        print('  "Ellie": 1519225,')
        print('  "John": 123456')
        print('}')
        return

    print("=" * 60)
    print("CONFIGURED SWIMMERS")
    print("=" * 60)
    for name, swimmer_id in swimmers.items():
        print(f"  {name:<30} ID: {swimmer_id}")
    print("=" * 60)
    print(f"Total: {len(swimmers)} swimmers configured")


def lookup_swimmer_id(name_or_id):
    """
    Lookup swimmer ID by name or return the ID if already numeric.

    Args:
        name_or_id: Either a swimmer name or numeric ID

    Returns:
        tuple: (swimmer_id, swimmer_info dict or None)
               swimmer_info contains: name, id, birthday, gender, age, age_group
    """
    # If it's already a numeric ID, return it
    if name_or_id.isdigit():
        return name_or_id, None

    # Otherwise, try to look it up by name
    swimmers = load_swimmers_config()

    # Case-insensitive lookup
    for name, swimmer_data in swimmers.items():
        if name.lower() == name_or_id.lower():
            # Support both old format (just ID) and new format (dict)
            if isinstance(swimmer_data, dict):
                swimmer_info = {
                    'name': name,
                    'id': str(swimmer_data.get('id', '')),
                    'birthday': swimmer_data.get('birthday'),
                    'gender': swimmer_data.get('gender')
                }

                # Calculate age and age group if birthday provided
                if swimmer_info['birthday']:
                    swimmer_info['age'] = calculate_age(swimmer_info['birthday'])
                    swimmer_info['age_group'] = get_age_group(swimmer_info['age'])
                else:
                    swimmer_info['age'] = None
                    swimmer_info['age_group'] = None

                return swimmer_info['id'], swimmer_info
            else:
                # Old format: just the ID
                return str(swimmer_data), {'name': name, 'id': str(swimmer_data)}

    # Name not found
    return None, None


def calculate_age(birthday_str):
    """Calculate current age from birthday string (YYYY-MM-DD)."""
    from datetime import datetime

    try:
        birthday = datetime.strptime(birthday_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        return age
    except:
        return None


def get_age_group(age):
    """
    Determine age group from age for Bronze/Silver standards.

    Age groups: 8&U, 9-10, 11-12, 13-14, 15+
    """
    if age is None:
        return None
    if age <= 8:
        return "8&U"
    elif age <= 10:
        return "9-10"
    elif age <= 12:
        return "11-12"
    elif age <= 14:
        return "13-14"
    else:
        return "15+"


def get_age_group_for_standard(age, standard_level):
    """
    Get the correct age group for looking up a specific standard level.

    For Age Group championships, ages 8-10 use "10&U"
    For Bronze/Silver, use the specific age group.

    Args:
        age: Swimmer's age
        standard_level: 'bronze', 'silver', or 'age_group'

    Returns:
        str: Age group string for standards lookup
    """
    if age is None:
        return None

    # For Age Group championships, 8-10 year olds use "10&U"
    if standard_level == 'age_group' and age <= 10:
        return "10&U"

    # Otherwise use the regular age group
    return get_age_group(age)


def load_time_standards():
    """Load time standards from JSON file."""
    standards_file = os.path.join(os.path.dirname(__file__), 'time_standards.json')

    if not os.path.exists(standards_file):
        return None

    try:
        with open(standards_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load time standards: {e}")
        return None


def parse_time_to_seconds(time_str):
    """Convert time string like '1:23.45' or '23.45' to seconds."""
    if not time_str:
        return None

    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


def format_time(seconds):
    """Convert seconds to time string like '1:23.45' or '23.45'."""
    if seconds is None:
        return None

    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    else:
        return f"{seconds:.2f}"


def is_usa_swimming_meet(meet_name):
    """
    Determine if a meet is a USA Swimming sanctioned meet.

    Args:
        meet_name: Name of the meet

    Returns:
        bool: True if USA Swimming meet, False if high school meet
    """
    if not meet_name:
        return False

    meet_upper = meet_name.upper()

    # USA Swimming indicators
    usa_indicators = ['NE ', 'NHSA']

    for indicator in usa_indicators:
        if indicator in meet_upper:
            return True

    return False


def get_best_usa_swimming_time_from_progression(driver, event_name):
    """
    Click on an event to expand its progression and find the best USA Swimming time.

    Args:
        driver: Selenium WebDriver (already on the times page)
        event_name: Name of the event (e.g., "100 Breast SCY")

    Returns:
        dict: Best USA Swimming time info {'time': str, 'meet': str, 'date': str} or None
    """
    try:
        # Find and click the button for this event
        buttons = driver.find_elements(By.CSS_SELECTOR, 'button.btn-link')
        event_button = None
        for btn in buttons:
            if event_name.upper() in btn.text.upper():
                event_button = btn
                break

        if not event_button:
            return None

        # Click to expand event progression
        event_button.click()
        import time
        time.sleep(2)

        # Parse the event progression table
        soup = bs(driver.page_source, 'html.parser')

        # Find the history table (should be the only table now)
        tables = soup.find_all('table', {'class': 'c-table-clean'})
        if not tables:
            return None

        # Parse all times from the progression table
        progression_times = []
        for table in tables:
            tbody = table.find('tbody')
            if not tbody:
                continue

            rows = tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue

                # Extract time, meet, and date
                time_cell = cols[0]
                meet_cell = cols[2]
                date_cell = cols[3]

                time_link = time_cell.find('a')
                time_val = time_link.text.strip() if time_link else time_cell.text.strip()

                meet_link = meet_cell.find('a')
                meet_name = meet_link.text.strip() if meet_link else meet_cell.text.strip()

                date_val = date_cell.text.strip()

                # Check if this is a USA Swimming meet
                if is_usa_swimming_meet(meet_name):
                    progression_times.append({
                        'time': time_val,
                        'meet': meet_name,
                        'date': date_val
                    })

        # Find the fastest USA Swimming time
        if not progression_times:
            return None

        fastest = None
        fastest_seconds = None

        for entry in progression_times:
            time_seconds = parse_time_to_seconds(entry['time'])
            if time_seconds is not None:
                if fastest_seconds is None or time_seconds < fastest_seconds:
                    fastest = entry
                    fastest_seconds = time_seconds

        return fastest

    except Exception as e:
        print(f"Warning: Error getting USA Swimming time from progression: {e}")
        return None


def compare_to_standards(time_str, event, age, gender, standards):
    """
    Compare a swimmer's time to standards and return achieved level and next goal.

    Args:
        time_str: Swimmer's time as string
        event: Event name
        age: Swimmer's age (integer)
        gender: 'Girl' or 'Boy'
        standards: Standards dictionary

    Returns:
        tuple: (current_standard, next_standard, time_diff_to_next)
    """
    if not standards or age is None or not gender:
        return None, None, None

    # Parse swimmer's time to seconds
    swimmer_time = parse_time_to_seconds(time_str)
    if swimmer_time is None:
        return None, None, None

    # Get standards for each level, using correct age group for each
    bronze = None
    silver = None
    age_group_std = None

    # Bronze standards
    bronze_age_group = get_age_group_for_standard(age, 'bronze')
    try:
        bronze = standards[bronze_age_group][gender][event].get('bronze')
    except (KeyError, AttributeError):
        pass

    # Silver standards
    silver_age_group = get_age_group_for_standard(age, 'silver')
    try:
        silver = standards[silver_age_group][gender][event].get('silver')
    except (KeyError, AttributeError):
        pass

    # Age Group standards
    ag_age_group = get_age_group_for_standard(age, 'age_group')
    try:
        age_group_std = standards[ag_age_group][gender][event].get('age_group')
    except (KeyError, AttributeError):
        pass

    # Determine current standard (faster is better, so < comparison)
    current = None
    next_std = None
    next_time = None

    if age_group_std and swimmer_time <= age_group_std:
        current = "Age Group"
        next_std = None
        next_time = None
    elif silver and swimmer_time <= silver:
        current = "Silver"
        next_std = "Age Group"
        next_time = age_group_std
    elif bronze and swimmer_time <= bronze:
        current = "Bronze"
        next_std = "Silver"
        next_time = silver
    else:
        current = None
        next_std = "Bronze"
        next_time = bronze

    # Calculate time difference
    if next_time:
        time_diff = swimmer_time - next_time
    else:
        time_diff = None

    return current, next_std, time_diff


def setup_driver():
    """Setup Chrome driver with anti-detection measures."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Check if running in Streamlit Cloud environment
    # Streamlit Cloud has chromium-chromedriver installed system-wide
    import shutil
    system_chromedriver = shutil.which('chromedriver')

    if system_chromedriver and os.environ.get('STREAMLIT_SHARING_MODE'):
        # Use system chromedriver on Streamlit Cloud
        service = Service(executable_path=system_chromedriver)
        # Use chromium binary on Streamlit Cloud
        chrome_options.binary_location = '/usr/bin/chromium-browser'
    else:
        # Use webdriver-manager for local development
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=chrome_options)


def get_swimmer_best_times(swimmer_id, course_filter='SCY', swimmer_info=None, show_all_events=False, usa_only=False):
    """
    Get best times for a swimmer from their personal bests page.

    Args:
        swimmer_id: The swimmer's ID from swimcloud.com
        course_filter: Filter by course type - 'SCY', 'LCM', or 'ALL'
        swimmer_info: Swimmer information dict (for filtering eligible events)
        show_all_events: If False, filter out events without standards
        usa_only: If True, filter to only USA Swimming times (exclude high school)

    Returns:
        List of best times with event, time, date, age, and meet info
    """
    print(f"Fetching best times for swimmer ID: {swimmer_id}")
    print(f"Profile URL: https://www.swimcloud.com/swimmer/{swimmer_id}/")
    if course_filter != 'ALL':
        print(f"Filter: {course_filter} events only")
    if usa_only:
        print(f"Filter: USA Swimming meets only")
    print()

    # Direct link to times page (Personal Bests tab is active by default)
    best_times_url = f'https://www.swimcloud.com/swimmer/{swimmer_id}/times/'

    driver = setup_driver()
    best_times = []

    try:
        print(f"Loading personal bests page...")
        driver.get(best_times_url)
        _time.sleep(3)  # Wait for page to load

        if "403" in driver.title or "Forbidden" in driver.title:
            print("ERROR: Access forbidden. SwimCloud may be blocking automated access.")
            return best_times

        if "404" in driver.title or "Not Found" in driver.title:
            print(f"ERROR: Swimmer ID {swimmer_id} not found.")
            return best_times

        print(f"Page loaded: {driver.title}\n")

        # Parse the page
        soup = bs(driver.page_source, 'html.parser')

        # Find the times table
        table = soup.find('table', {'class': 'c-table-clean'})

        if not table:
            print("No times table found on personal bests page.")
            return best_times

        # Parse table rows
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else []

        print(f"Found {len(rows)} personal best times\n")

        for row in rows:
            cols = row.find_all('td')

            if len(cols) >= 2:
                # Extract event name (column 0)
                event_cell = cols[0]
                event_button = event_cell.find('button')
                event_name = event_button.text.strip() if event_button else event_cell.text.strip()

                # Extract time (column 1)
                time_cell = cols[1]
                time_link = time_cell.find('a')
                time_val = time_link.text.strip() if time_link else time_cell.text.strip()

                # Column 2 - Extracted indicator (X) or empty
                extracted = ''
                if len(cols) > 2:
                    label = cols[2].find('span', {'class': 'c-label'})
                    if label:
                        extracted = label.text.strip()

                # Column 3 - Meet name
                meet_name = ''
                if len(cols) > 3:
                    meet_link = cols[3].find('a')
                    meet_name = meet_link.text.strip() if meet_link else cols[3].text.strip()

                # Column 4 - Date
                date_val = ''
                if len(cols) > 4:
                    date_val = cols[4].text.strip()

                # Determine if this is a USA Swimming meet
                is_usa = is_usa_swimming_meet(meet_name)

                # If the best time is from a high school meet, also get the best USA Swimming time
                usa_best_time = None
                if not is_usa:
                    usa_best_time = get_best_usa_swimming_time_from_progression(driver, event_name)

                best_times.append({
                    'event': event_name,
                    'time': time_val,
                    'meet': meet_name,
                    'date': date_val,
                    'extracted': extracted,
                    'usa_swimming': is_usa,
                    'usa_best': usa_best_time  # Will be None if best time is USA Swimming
                })

    except Exception as e:
        print(f"Error fetching best times: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

    # Filter by course type if requested
    if course_filter != 'ALL':
        best_times = [t for t in best_times if course_filter in t['event']]

    # Filter to USA Swimming times only if requested
    if usa_only:
        hs_count = sum(1 for t in best_times if not t.get('usa_swimming', True))
        best_times = [t for t in best_times if t.get('usa_swimming', True)]
        if hs_count > 0:
            print(f"Note: Filtered out {hs_count} high school time(s)")
            print(f"      Use without --usa-only to include high school times\n")

    # Filter out events without standards unless --all-events is specified
    if not show_all_events and swimmer_info:
        age = swimmer_info.get('age')
        age_group = swimmer_info.get('age_group')
        gender = swimmer_info.get('gender')

        if age and gender:
            # Load standards to check which events are eligible
            standards = load_time_standards()

            if standards:
                eligible_times = []
                filtered_count = 0

                for time_entry in best_times:
                    event = time_entry['event']

                    # Check if this event has ANY standards (bronze, silver, or age group)
                    # for this age/gender by checking all relevant age groups
                    has_standards = False

                    for level in ['bronze', 'silver', 'age_group']:
                        level_age_group = get_age_group_for_standard(age, level)
                        try:
                            event_standards = standards[level_age_group][gender].get(event)
                            if event_standards and event_standards.get(level):
                                has_standards = True
                                break
                        except (KeyError, AttributeError):
                            continue

                    if has_standards:
                        eligible_times.append(time_entry)
                    else:
                        filtered_count += 1

                if filtered_count > 0:
                    print(f"Note: Filtered out {filtered_count} event(s) without time standards for {age_group} {gender}")
                    print(f"      Use --all-events to show all events\n")

                return eligible_times

    return best_times


def calculate_time_age_months(date_str):
    """Calculate how many months ago a time was achieved."""
    from datetime import datetime

    if not date_str or date_str.strip() == '' or date_str == '–':
        return None

    try:
        # Parse date (format: "Jan 5, 2025" or similar)
        time_date = datetime.strptime(date_str.strip(), '%b %d, %Y')
        today = datetime.now()

        # Calculate difference in months
        months = (today.year - time_date.year) * 12 + (today.month - time_date.month)

        # Adjust if the day hasn't occurred yet this month
        if today.day < time_date.day:
            months -= 1

        return max(0, months)  # Don't return negative months
    except:
        return None


def display_best_times(best_times, swimmer_id, swimmer_info=None, show_standards=False, show_time_age=False):
    """Display best times in a formatted table."""
    if not best_times:
        print("No best times found.")
        return

    # Load standards if requested
    standards = None
    age_group = None
    age = None
    gender = None

    if show_standards:
        standards = load_time_standards()
        if not standards:
            print("Warning: Time standards file not found. Run: python3 parse_standards_pdf.py")
            print("Continuing without standards...")
            show_standards = False

        if swimmer_info:
            age_group = swimmer_info.get('age_group')
            age = swimmer_info.get('age')
            gender = swimmer_info.get('gender')

            if not age or not gender:
                print("Warning: Swimmer age/gender not available. Cannot show standards.")
                show_standards = False

    # Determine table width and headers
    if show_standards:
        if show_time_age:
            width = 165
            print("=" * width)
            print(f"PERSONAL BEST TIMES - Swimmer ID: {swimmer_id}")
            if swimmer_info:
                name = swimmer_info.get('name', '')
                age = swimmer_info.get('age', '')
                print(f"Name: {name}, Age: {age}, Age Group: {age_group}, Gender: {gender}")
            print("=" * width)
            print(f"{'Event':<20} {'Time':<10} {'Standard':<12} {'Next Goal':<12} {'Diff':<8} {'Meet':<37} {'Date':<13} {'Age(mo)':<7}")
            print("-" * width)
        else:
            width = 155
            print("=" * width)
            print(f"PERSONAL BEST TIMES - Swimmer ID: {swimmer_id}")
            if swimmer_info:
                name = swimmer_info.get('name', '')
                age = swimmer_info.get('age', '')
                print(f"Name: {name}, Age: {age}, Age Group: {age_group}, Gender: {gender}")
            print("=" * width)
            print(f"{'Event':<20} {'Time':<10} {'Standard':<12} {'Next Goal':<12} {'Diff':<8} {'Meet':<37} {'Date':<13}")
            print("-" * width)
    else:
        width = 110
        print("=" * width)
        print(f"PERSONAL BEST TIMES - Swimmer ID: {swimmer_id}")
        print("=" * width)
        print(f"{'Event':<20} {'Time':<12} {'Meet':<45} {'Date':<15} {'Note'}")
        print("-" * width)

    for entry in best_times:
        event = entry['event'][:19]
        time_val = entry['time']
        date_val = entry['date']
        extracted = entry.get('extracted', '')
        is_usa = entry.get('usa_swimming', True)
        usa_best = entry.get('usa_best')

        # Add HS indicator for high school times
        hs_indicator = "" if is_usa else "HS"

        # Function to display a single row
        def display_row(evt, tm, dt, meet, is_usa_tm, indicator="", usa_label=False):
            if show_standards:
                meet_val = meet[:36]

                # Compare to standards (only for USA Swimming times)
                if is_usa_tm:
                    current_std, next_std, time_diff = compare_to_standards(
                        tm, evt, age, gender, standards
                    )
                else:
                    # High school times don't count for standards
                    current_std, next_std, time_diff = None, None, None

                current_str = current_std if current_std else "-"
                next_str = next_std if next_std else "-"

                if time_diff is not None:
                    if time_diff > 0:
                        diff_str = f"-{abs(time_diff):.2f}"
                    else:
                        diff_str = f"+{abs(time_diff):.2f}"
                else:
                    diff_str = "-"

                # Add indicator to time if applicable
                time_display = f"{tm} {indicator}".strip()

                # For USA best time, prefix event with spaces to indicate it's related
                event_display = f"  (USA Best)" if usa_label else evt

                if show_time_age:
                    # Calculate age of time in months
                    months_ago = calculate_time_age_months(dt)
                    age_str = f"{months_ago}mo" if months_ago is not None else "-"
                    print(f"{event_display:<20} {time_display:<10} {current_str:<12} {next_str:<12} {diff_str:<8} {meet_val:<37} {dt:<13} {age_str:<7}")
                else:
                    print(f"{event_display:<20} {time_display:<10} {current_str:<12} {next_str:<12} {diff_str:<8} {meet_val:<37} {dt:<13}")
            else:
                meet_val = meet[:44]
                # Combine extracted and indicator
                note = f"{extracted if not usa_label else ''} {indicator}".strip()
                event_display = f"  (USA Best)" if usa_label else evt
                print(f"{event_display:<20} {tm:<12} {meet_val:<45} {dt:<15} {note}")

        # Display the main time (overall best)
        display_row(event, time_val, date_val, entry['meet'], is_usa, hs_indicator, usa_label=False)

        # If this is a HS time and we have a USA Swimming best, display it on the next line
        if usa_best:
            display_row(event, usa_best['time'], usa_best['date'], usa_best['meet'],
                       True, "", usa_label=True)

    print("=" * width)
    print(f"Total: {len(best_times)} personal best times")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Get swimmer personal best times from SwimCloud',
        epilog='''
Configuration:
  Create a swimmers.json file in the same directory to configure your swimmers:
  {
    "Ellie": 1519225,
    "John": 123456
  }

To find a swimmer's ID:
  1. Go to https://www.swimcloud.com
  2. Search for the swimmer
  3. Click on their profile
  4. The swimmer ID is in the URL: https://www.swimcloud.com/swimmer/SWIMMER_ID/

Examples:
  %(prog)s --list                        # List configured swimmers
  %(prog)s Ellie                         # Show SCY times (only events with standards)
  %(prog)s Ellie --usa-only              # Show only USA Swimming times (no HS meets)
  %(prog)s Ellie --all-events            # Show all events including non-standard events
  %(prog)s Ellie --standards             # Show SCY times with standards comparison
  %(prog)s Ellie --standards --time-age  # Include age of each time in months
  %(prog)s Ellie --standards --usa-only  # Standards with USA Swimming times only
  %(prog)s "John" --lcm                  # Show LCM times for John
  %(prog)s 1519225                       # Show SCY times by swimmer ID
  %(prog)s 1519225 --all                 # Show all times (SCY and LCM)
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('name_or_id', type=str, nargs='?',
                       help='Swimmer name (from config) or ID from swimcloud.com')
    parser.add_argument('--list', action='store_true',
                       help='List all configured swimmers')

    course_group = parser.add_mutually_exclusive_group()
    course_group.add_argument('--lcm', action='store_true',
                            help='Show LCM (Long Course Meters) times only')
    course_group.add_argument('--all', action='store_true',
                            help='Show all times (both SCY and LCM)')

    parser.add_argument('--standards', action='store_true',
                       help='Show time standards comparison (requires swimmer config with age/gender)')
    parser.add_argument('--time-age', action='store_true',
                       help='Show age of each best time in months (only with --standards)')
    parser.add_argument('--all-events', action='store_true',
                       help='Show all events, including those without time standards for swimmer\'s age group')
    parser.add_argument('--usa-only', action='store_true',
                       help='Show only USA Swimming times (exclude high school meets)')

    args = parser.parse_args()

    # Handle --list option
    if args.list:
        list_configured_swimmers()
        return

    # Require name_or_id if not listing
    if not args.name_or_id:
        parser.print_help()
        sys.exit(1)

    # Look up swimmer ID (either from config by name, or use directly if numeric)
    swimmer_id, swimmer_info = lookup_swimmer_id(args.name_or_id)

    if swimmer_id is None:
        print(f"Error: Swimmer '{args.name_or_id}' not found in configuration.")
        print(f"\nConfigured swimmers:")
        list_configured_swimmers()
        print(f"\nOr use a numeric swimmer ID directly.")
        sys.exit(1)

    # Determine course filter
    if args.all:
        course_filter = 'ALL'
    elif args.lcm:
        course_filter = 'LCM'
    else:
        course_filter = 'SCY'  # Default

    # Display swimmer info
    if swimmer_info and swimmer_info.get('name'):
        name = swimmer_info['name']
        age = swimmer_info.get('age')
        if age:
            print(f"Swimmer: {name} (Age: {age})")
        else:
            print(f"Swimmer: {name}")

    # Get and display times
    best_times = get_swimmer_best_times(swimmer_id, course_filter,
                                       swimmer_info=swimmer_info,
                                       show_all_events=args.all_events,
                                       usa_only=args.usa_only)
    display_best_times(best_times, swimmer_id, swimmer_info,
                      show_standards=args.standards,
                      show_time_age=args.time_age)


if __name__ == "__main__":
    main()
