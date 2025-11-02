#!/usr/bin/env python3
"""
Streamlit web app for viewing swimmer best times from SwimCloud.
Uses the existing get_best_times.py module for core functionality.
"""

import streamlit as st
import json
from io import StringIO
import sys

# Import functions from existing CLI script
from get_best_times import (
    get_swimmer_best_times,
    display_best_times,
    lookup_swimmer_id,
    calculate_age
)

# Page configuration
st.set_page_config(
    page_title="Swimming Times Dashboard",
    page_icon="🏊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better table display
st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
    }
    pre {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.4;
        white-space: pre;
        overflow-x: auto;
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


def capture_display_output(best_times, swimmer_id, swimmer_info, show_standards, show_time_age):
    """Capture the CLI display output as a string."""
    # Redirect stdout to capture print statements
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        display_best_times(
            best_times=best_times,
            swimmer_id=swimmer_id,
            swimmer_info=swimmer_info,
            show_standards=show_standards,
            show_time_age=show_time_age
        )
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    return output


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
                    # Capture the formatted output
                    output = capture_display_output(
                        best_times=best_times,
                        swimmer_id=swimmer_id,
                        swimmer_info=swimmer_info,
                        show_standards=show_standards,
                        show_time_age=show_time_age
                    )

                    # Display in a code block for proper formatting
                    st.code(output, language=None)

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
