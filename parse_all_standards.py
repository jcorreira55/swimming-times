#!/usr/bin/env python3
"""
Parse all NE Swimming time standards from multiple PDFs and create unified JSON file.
"""

import json
import re
import sys
import os

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not installed. Install with: pip install pdfplumber")
    sys.exit(1)


def parse_time_to_seconds(time_str):
    """Convert time string like '1:23.45' or '23.45' to seconds."""
    if not time_str or time_str.strip() == '' or time_str.strip() == 'n/a':
        return None

    time_str = time_str.strip()

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


def normalize_event_name(event):
    """Normalize event names to match SwimCloud format."""
    if not event:
        return None

    event = event.strip().upper()

    # Remove extra spaces
    event = re.sub(r'\s+', ' ', event)

    # Map abbreviations to full names (order matters - do longer patterns first)
    replacements = [
        (' FREE', ' Free'),
        (' BREAST', ' Breast'),
        (' BACK', ' Back'),
        (' FLY', ' Fly'),
        (' FR', ' Free'),
        (' BR', ' Breast'),
        (' BK', ' Back'),
        (' BA', ' Back'),
        (' FL', ' Fly'),
    ]

    for abbrev, full in replacements:
        event = event.replace(abbrev, full)

    # Add SCY suffix if not present
    if 'SCY' not in event and 'LCM' not in event and 'SCM' not in event:
        event = event + ' SCY'

    return event


def parse_bronze_silver_table(table, age_group_name):
    """
    Parse Bronze or Silver Championships table.

    Structure (5 columns):
    Row 0: GIRLS | | | BOYS |
    Row 1: Cut Off | Cut Time | EVENT | Cut Time | Cut off
    Row 2+: time | time | event | time | time

    Returns dict with structure: {event: {'Girl': time, 'Boy': time}}
    """
    standards = {}

    if not table or len(table) < 3:
        return standards

    # Process data rows (skip first 2 header rows)
    for row in table[2:]:
        if not row or len(row) < 5:
            continue

        # Extract event name (column 2)
        event = row[2]
        if not event or not event.strip():
            continue

        event = normalize_event_name(event)
        if not event:
            continue

        # Parse times (Cut Time columns only, ignore Cut Off)
        girl_time = parse_time_to_seconds(row[1])
        boy_time = parse_time_to_seconds(row[3])

        if girl_time or boy_time:
            standards[event] = {
                'Girl': girl_time,
                'Boy': boy_time
            }

    return standards


def parse_age_group_table(table):
    """
    Parse Age Group Championships table.

    Structure (7 columns):
    Row 0: GIRLS | | | EVENT | BOYS | |
    Row 1: LCM | SCM | SCY | EVENT | SCY | SCM | LCM
    Row 2+: time | time | time | event | time | time | time

    Returns dict with structure: {event: {'Girl': time, 'Boy': time}}
    """
    standards = {}

    if not table or len(table) < 3:
        return standards

    # Process data rows (skip first 2 header rows)
    for row in table[2:]:
        if not row or len(row) < 7:
            continue

        # Extract event name (column 3)
        event = row[3]
        if not event or not event.strip():
            continue

        event = normalize_event_name(event)
        if not event:
            continue

        # Parse SCY times only (column 2 for girls, column 4 for boys)
        girl_time = parse_time_to_seconds(row[2])
        boy_time = parse_time_to_seconds(row[4])

        if girl_time or boy_time:
            standards[event] = {
                'Girl': girl_time,
                'Boy': boy_time
            }

    return standards


def parse_bronze_championships(pdf_path):
    """Parse Bronze Championships PDF - has multiple age groups."""
    print(f"\nParsing Bronze Championships: {pdf_path}")
    standards = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  Page {page_num}/{len(pdf.pages)}...")

            # Extract text to find age group
            text = page.extract_text()
            if not text:
                continue

            # Find age group on this page
            age_group = None
            for line in text.split('\n'):
                line = line.strip()
                if line == '8 & Under':
                    age_group = '8&U'
                    break
                elif line == '9-10':
                    age_group = '9-10'
                    break
                elif line == '11-12':
                    age_group = '11-12'
                    break
                elif line == '13-14':
                    age_group = '13-14'
                    break
                elif line in ['15 & Over', '15-18', '15+']:
                    age_group = '15+'
                    break

            if not age_group:
                print(f"    Warning: Could not determine age group on page {page_num}")
                continue

            print(f"    Age group: {age_group}")

            # Extract tables
            tables = page.extract_tables()
            if not tables:
                continue

            # Parse first table
            table = tables[0]
            event_standards = parse_bronze_silver_table(table, age_group)

            if event_standards:
                standards[age_group] = event_standards

    return standards


def parse_silver_championships(pdf_path):
    """Parse Silver Championships PDF - has multiple age groups."""
    print(f"\nParsing Silver Championships: {pdf_path}")
    standards = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  Page {page_num}/{len(pdf.pages)}...")

            # Extract text to find age group
            text = page.extract_text()
            if not text:
                continue

            # Find age group on this page
            age_group = None
            for line in text.split('\n'):
                line = line.strip()
                if line == '8 & Under':
                    age_group = '8&U'
                    break
                elif line == '9-10':
                    age_group = '9-10'
                    break
                elif line == '11-12':
                    age_group = '11-12'
                    break
                elif line == '13-14':
                    age_group = '13-14'
                    break
                elif line in ['15 & Over', '15-18', '15+']:
                    age_group = '15+'
                    break

            if not age_group:
                print(f"    Warning: Could not determine age group on page {page_num}")
                continue

            print(f"    Age group: {age_group}")

            # Extract tables
            tables = page.extract_tables()
            if not tables:
                continue

            # Parse first table
            table = tables[0]
            event_standards = parse_bronze_silver_table(table, age_group)

            if event_standards:
                standards[age_group] = event_standards

    return standards


def parse_age_group_championships(pdf_path, expected_age_groups):
    """Parse Age Group Championships PDF."""
    filename = os.path.basename(pdf_path)
    print(f"\nParsing Age Group Championships: {filename}")
    standards = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  Page {page_num}/{len(pdf.pages)}...")

            # Extract text to find age group
            text = page.extract_text()
            if not text:
                continue

            # Skip BONUS TIME STANDARDS pages
            if 'BONUS TIME STANDARDS' in text:
                print(f"    Skipping bonus standards page")
                continue

            # Find age group on this page
            age_group = None
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if '10 & Under' in line:
                    age_group = '10&U'
                    break
                elif line_stripped == 'GIRLS' and i > 0:
                    # Check previous line for age group
                    prev_line = lines[i-1].strip()
                    if '11-12' in prev_line:
                        age_group = '11-12'
                        break
                    elif '13-14' in prev_line:
                        age_group = '13-14'
                        break
                elif line_stripped.startswith('GIRLS') and '11-12' in line:
                    age_group = '11-12'
                    break
                elif line_stripped.startswith('GIRLS') and '13-14' in line:
                    age_group = '13-14'
                    break
                elif '15-18' in line:
                    age_group = '15+'  # Normalize to 15+ to match Bronze/Silver
                    break

            if not age_group:
                print(f"    Warning: Could not determine age group on page {page_num}")
                continue

            print(f"    Age group: {age_group}")

            # Extract tables
            tables = page.extract_tables()
            if not tables:
                continue

            # Parse first table
            table = tables[0]
            event_standards = parse_age_group_table(table)

            if event_standards:
                standards[age_group] = event_standards

    return standards


def merge_standards(bronze, silver, age_group):
    """
    Merge Bronze, Silver, and Age Group standards into unified structure.

    Final structure:
    {
        "8&U": {
            "Girl": {
                "50 Free SCY": {
                    "bronze": 59.99,
                    "silver": 44.89,
                    "age_group": 32.49
                }
            }
        }
    }
    """
    merged = {}

    # Collect all age groups
    all_age_groups = set()
    all_age_groups.update(bronze.keys())
    all_age_groups.update(silver.keys())
    all_age_groups.update(age_group.keys())

    print(f"\nMerging standards for age groups: {sorted(all_age_groups)}")

    for ag in all_age_groups:
        merged[ag] = {'Girl': {}, 'Boy': {}}

        # Collect all events for this age group
        all_events = set()

        if ag in bronze:
            all_events.update(bronze[ag].keys())
        if ag in silver:
            all_events.update(silver[ag].keys())
        if ag in age_group:
            all_events.update(age_group[ag].keys())

        for event in all_events:
            for gender in ['Girl', 'Boy']:
                # Get times from each level
                bronze_time = None
                silver_time = None
                ag_time = None

                if ag in bronze and event in bronze[ag]:
                    bronze_time = bronze[ag][event].get(gender)

                if ag in silver and event in silver[ag]:
                    silver_time = silver[ag][event].get(gender)

                if ag in age_group and event in age_group[ag]:
                    ag_time = age_group[ag][event].get(gender)

                # Only add if at least one time exists
                if bronze_time or silver_time or ag_time:
                    merged[ag][gender][event] = {
                        'bronze': bronze_time,
                        'silver': silver_time,
                        'age_group': ag_time
                    }

    return merged


def main():
    """Main function."""
    standards_dir = '/home/john/times/standards'

    print("=" * 70)
    print("NE Swimming Time Standards Parser - All Documents")
    print("=" * 70)

    # Parse Bronze Championships
    bronze_path = os.path.join(standards_dir, '2025-26-scy-bronze-championships-standards---2025-10-03_042880.pdf')
    bronze_standards = parse_bronze_championships(bronze_path)

    # Parse Silver Championships
    silver_path = os.path.join(standards_dir, '2025-26-ne-silver-championships-scy-standards---2025-10-03_053659.pdf')
    silver_standards = parse_silver_championships(silver_path)

    # Parse Age Group Championships
    ag_10u_path = os.path.join(standards_dir, '2025-26-scy-10-under-time-standards---2025-10-03_079194.pdf')
    ag_11_14_path = os.path.join(standards_dir, '2025-26-scy-11-14-time-standards---2025-10-03_049262.pdf')
    ag_15_18_path = os.path.join(standards_dir, '2025-26-scy-15-18-time-standards---2025-10-03_070075.pdf')

    ag_standards = {}
    ag_standards.update(parse_age_group_championships(ag_10u_path, ['10&U']))
    ag_standards.update(parse_age_group_championships(ag_11_14_path, ['11-12', '13-14']))
    ag_standards.update(parse_age_group_championships(ag_15_18_path, ['15-18']))

    # Merge all standards
    final_standards = merge_standards(bronze_standards, silver_standards, ag_standards)

    if not final_standards:
        print("\nERROR: PDF parsing failed or returned no data.")
        sys.exit(1)

    # Save to JSON
    output_path = '/home/john/times/time_standards.json'
    with open(output_path, 'w') as f:
        json.dump(final_standards, f, indent=2)

    print("\n" + "=" * 70)
    print(f"SUCCESS: Time standards saved to: {output_path}")
    print("=" * 70)
    print(f"\nAge groups found: {', '.join(sorted(final_standards.keys()))}")

    # Show summary
    print("\nSummary:")
    for age_group in sorted(final_standards.keys()):
        girl_events = len(final_standards[age_group].get("Girl", {}))
        boy_events = len(final_standards[age_group].get("Boy", {}))
        print(f"  {age_group:8} - Girls: {girl_events:2} events, Boys: {boy_events:2} events")

    total_events = sum(
        len(final_standards[ag][gender])
        for ag in final_standards
        for gender in final_standards[ag]
    )
    print(f"\nTotal event standards: {total_events}")


if __name__ == "__main__":
    main()
