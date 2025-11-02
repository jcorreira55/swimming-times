#!/usr/bin/env python3
"""
Streamlit web app for viewing swimmer best times from SwimCloud.
Uses the existing get_best_times.py module for core functionality.
"""

import streamlit as st
import json

# Import functions from existing CLI script
from get_best_times import (
    get_swimmer_best_times,
    calculate_age
)

# Page configuration
st.set_page_config(
    page_title="Swimming Times Dashboard",
    page_icon="🏊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile-friendly display
st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
    }
    /* Make expanders more prominent */
    .streamlit-expanderHeader {
        font-size: 1.1rem;
        font-weight: 600;
    }
    /* Better spacing on mobile */
    @media (max-width: 768px) {
        .stMetric {
            padding: 0.5rem 0;
        }
        div[data-testid="column"] {
            padding: 0.25rem;
        }
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_swimmer_times(swimmer_id, course_filter, swimmer_info, show_all_events, usa_only):
    """Fetch swimmer times with caching."""
    return get_swimmer_best_times(
        swimmer_id=swimmer_id,
        course_filter=course_filter,
        swimmer_info=swimmer_info,
        show_all_events=show_all_events,
        usa_only=usa_only
    )


def load_swimmers_from_secrets():
    """Load swimmers from Streamlit secrets."""
    try:
        # Streamlit secrets are accessed via st.secrets
        # Need to convert AttrDict to regular dict recursively
        swimmers_raw = st.secrets["swimmers"]
        swimmers = {}

        for name, data in swimmers_raw.items():
            # Convert nested AttrDict to regular dict
            swimmers[name] = {
                'id': data['id'],
                'birthday': data['birthday'],
                'gender': data['gender']
            }

        return swimmers
    except Exception as e:
        st.error(f"Error loading swimmers from secrets: {e}")
        return {}


def display_times_mobile_friendly(best_times, swimmer_info, show_standards, show_time_age):
    """Display times in a mobile-friendly format using Streamlit components."""
    from get_best_times import (
        compare_to_standards,
        calculate_time_age_months,
        load_time_standards
    )

    if not best_times:
        st.warning("No times found")
        return

    # Load standards if needed
    standards = None
    age = None
    gender = None

    if show_standards and swimmer_info:
        standards = load_time_standards()
        age = swimmer_info.get('age')
        gender = swimmer_info.get('gender')

    # Display each time as a card
    for entry in best_times:
        event = entry['event']
        time_val = entry['time']
        meet = entry['meet']
        date_val = entry['date']
        is_usa = entry.get('usa_swimming', True)
        usa_best = entry.get('usa_best')

        # Create expandable section for each event
        with st.expander(f"**{event}** - {time_val} {'🏫' if not is_usa else ''}", expanded=False):
            # Main time info
            col1, col2 = st.columns([1, 1])

            with col1:
                st.metric("Time", time_val)
                if not is_usa:
                    st.caption("🏫 High School Meet")

            with col2:
                if show_time_age:
                    months_ago = calculate_time_age_months(date_val)
                    age_str = f"{months_ago} months ago" if months_ago is not None else "N/A"
                    st.metric("Time Age", age_str)

            st.write(f"**Meet:** {meet}")
            st.write(f"**Date:** {date_val}")

            # Standards comparison
            if show_standards and standards and age and gender:
                if is_usa:
                    current_std, next_std, time_diff = compare_to_standards(
                        time_val, event, age, gender, standards
                    )

                    if current_std or next_std:
                        st.divider()
                        st.write("**Standards:**")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Current", current_std if current_std else "Not yet")

                        with col2:
                            st.metric("Next Goal", next_std if next_std else "—")

                        with col3:
                            if time_diff is not None:
                                diff_str = f"{abs(time_diff):.2f}s {'faster needed' if time_diff > 0 else 'faster than needed'}"
                                st.metric("Difference", diff_str)
                else:
                    st.info("High school times don't count toward USA Swimming standards")

            # USA Swimming best time if available
            if usa_best:
                st.divider()
                st.write("**Best USA Swimming Time:**")

                col1, col2 = st.columns([1, 1])

                with col1:
                    st.metric("USA Time", usa_best['time'])

                with col2:
                    st.write(f"**Meet:** {usa_best['meet']}")
                    st.write(f"**Date:** {usa_best['date']}")

                # Standards for USA best
                if show_standards and standards and age and gender:
                    current_std, next_std, time_diff = compare_to_standards(
                        usa_best['time'], event, age, gender, standards
                    )

                    if current_std or next_std:
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Current", current_std if current_std else "Not yet")

                        with col2:
                            st.metric("Next Goal", next_std if next_std else "—")

                        with col3:
                            if time_diff is not None:
                                diff_str = f"{abs(time_diff):.2f}s"
                                st.metric("Difference", diff_str)


def main():
    """Main Streamlit app."""

    # Title and description
    st.title("🏊 Swimming Times Dashboard")
    st.markdown("View best times and standards for swimmers from SwimCloud")

    # Load swimmers from secrets
    swimmers = load_swimmers_from_secrets()

    if not swimmers:
        st.error("No swimmers configured. Please add swimmers to Streamlit secrets.")
        st.info("""
        To configure swimmers, go to your app settings in Streamlit Cloud and add a `swimmers` section to secrets.
        """)
        return

    # Sidebar for configuration
    st.sidebar.header("⚙️ Configuration")

    # Swimmer selection
    swimmer_names = ["Select a swimmer..."] + sorted(swimmers.keys())
    selected_name = st.sidebar.selectbox("Select Swimmer", swimmer_names)

    if selected_name == "Select a swimmer...":
        st.info("👈 Select a swimmer from the sidebar to view their times")
        return

    # Course filter
    course_filter = st.sidebar.radio(
        "Course Type",
        options=["SCY", "LCM", "ALL"],
        index=0,
        help="SCY = Short Course Yards, LCM = Long Course Meters"
    )

    # Display options
    st.sidebar.subheader("Display Options")
    show_standards = st.sidebar.checkbox("Show Standards", value=True, help="Compare times to Bronze/Silver/Age Group standards")
    show_time_age = st.sidebar.checkbox("Show Time Age", value=False, help="Show how many months ago each time was achieved")
    show_all_events = st.sidebar.checkbox("Show All Events", value=False, help="Include events without time standards")
    usa_only = st.sidebar.checkbox("USA Swimming Only", value=False, help="Exclude high school meet times")

    # Fetch button
    fetch_button = st.sidebar.button("🔄 Fetch Times", type="primary", use_container_width=True)

    # Info about caching
    st.sidebar.markdown("---")
    st.sidebar.caption("ℹ️ Results are cached for 1 hour. Click 'Fetch Times' to refresh.")

    # Main content area
    if fetch_button:
        # Look up swimmer info
        swimmer_data = swimmers[selected_name]

        # Handle both dict and simple ID formats
        if isinstance(swimmer_data, dict):
            swimmer_id = str(swimmer_data.get('id', ''))
            birthday = swimmer_data.get('birthday')
            gender = swimmer_data.get('gender')

            swimmer_info = {
                'name': selected_name,
                'id': swimmer_id,
                'birthday': birthday,
                'gender': gender
            }

            # Calculate age and age group if birthday provided
            if birthday:
                from get_best_times import get_age_group
                swimmer_info['age'] = calculate_age(birthday)
                swimmer_info['age_group'] = get_age_group(swimmer_info['age'])
            else:
                swimmer_info['age'] = None
                swimmer_info['age_group'] = None
        else:
            # Simple format (just ID)
            swimmer_id = str(swimmer_data)
            swimmer_info = None

        # Show spinner while fetching
        with st.spinner(f"Fetching times for {selected_name}..."):
            try:
                # Fetch times
                best_times = fetch_swimmer_times(
                    swimmer_id=swimmer_id,
                    course_filter=course_filter,
                    swimmer_info=swimmer_info,
                    show_all_events=show_all_events,
                    usa_only=usa_only
                )

                if best_times:
                    # Display header with swimmer info
                    st.subheader(f"Personal Best Times - {selected_name}")

                    if swimmer_info:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Age", swimmer_info.get('age', 'N/A'))
                        with col2:
                            st.metric("Age Group", swimmer_info.get('age_group', 'N/A'))
                        with col3:
                            st.metric("Gender", swimmer_info.get('gender', 'N/A'))

                    st.markdown("---")

                    # Display times in mobile-friendly format
                    display_times_mobile_friendly(
                        best_times=best_times,
                        swimmer_info=swimmer_info,
                        show_standards=show_standards,
                        show_time_age=show_time_age
                    )

                    # Success message
                    st.success(f"✅ Found {len(best_times)} personal best times")

                else:
                    st.warning("No times found for this swimmer")

            except Exception as e:
                st.error(f"Error fetching times: {e}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())

    else:
        # Show placeholder
        st.info("Click '🔄 Fetch Times' in the sidebar to load data")

        # Show swimmer info if selected
        if selected_name and selected_name != "Select a swimmer...":
            swimmer_data = swimmers[selected_name]

            st.subheader(f"Swimmer: {selected_name}")

            if isinstance(swimmer_data, dict):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Swimmer ID", swimmer_data.get('id', 'N/A'))

                with col2:
                    birthday = swimmer_data.get('birthday')
                    if birthday:
                        age = calculate_age(birthday)
                        st.metric("Age", age)
                    else:
                        st.metric("Age", "N/A")

                with col3:
                    st.metric("Gender", swimmer_data.get('gender', 'N/A'))
            else:
                st.metric("Swimmer ID", swimmer_data)


if __name__ == "__main__":
    main()
