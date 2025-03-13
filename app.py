import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import pytz

# Page config
st.set_page_config(page_title="Workout Progress Tracker", layout="wide")

# Constants
WORKOUT_AREAS = ["Shoulder", "Bicep", "Chest", "Tricep", "Upper leg", "Calf", "Back"]
GOAL_WEIGHT = 500000
CSV_FILE = "attached_assets/Workout Spreadsheet - Sheet1 (4).csv"

# Load data function
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(CSV_FILE)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Drop completely empty rows
        df = df.dropna(how='all')
        df = df[df['Workout Area'].notna()]

        # Remove the "Totals" row
        df = df[df['Workout Area'] != 'Totals']

        # Convert date column with proper format
        df['Date'] = pd.to_datetime(df['Date'], format='%B %d, %Y at %I:%M:%S %p')

        # Clean numeric columns
        for col in ['Total Lifted', 'Weight Left']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

        # Sort by date
        df = df.sort_values('Date')

        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'session_total' not in st.session_state:
    st.session_state.session_total = 0

# Title
st.title("💪 Workout Progress Tracker")
st.subheader(f"Progress towards {GOAL_WEIGHT:,} pounds goal")

# Create two columns for the main layout
col1, col2 = st.columns([2, 1])

with col1:
    # Progress Overview
    if not st.session_state.data.empty:
        total_lifted = GOAL_WEIGHT - float(st.session_state.data['Weight Left'].iloc[-1])
        remaining_weight = float(st.session_state.data['Weight Left'].iloc[-1])

        # Ensure progress is between 0 and 1
        progress = min(max(total_lifted / GOAL_WEIGHT, 0), 1)
        st.metric("Total Weight Lifted", f"{total_lifted:,.0f} lbs")
        st.progress(progress)
        st.metric("Remaining Weight", f"{remaining_weight:,.0f} lbs")

        # Progress Chart
        fig_progress = px.line(st.session_state.data, 
                             x='Date', 
                             y='Weight Left',
                             title='Weight Remaining Over Time')
        fig_progress.update_layout(showlegend=False)
        st.plotly_chart(fig_progress, use_container_width=True)
    else:
        st.warning("No data available. Please add your first workout!")

with col2:
    # Add New Entry
    st.subheader("Add New Workout")
    with st.form("new_workout", clear_on_submit=True):
        workout_area = st.selectbox("Workout Area", options=WORKOUT_AREAS)
        date = st.date_input("Date", datetime.now(pytz.timezone('US/Eastern')))
        time = st.time_input("Time", datetime.now(pytz.timezone('US/Eastern')).time())

        # Calculator section
        st.subheader("Weight Calculator")
        col1, col2 = st.columns([3, 1])
        with col1:
            weight_to_add = st.number_input("Weight to Add (lbs)", min_value=0, value=0, step=5)
        with col2:
            if st.form_submit_button("Add to Total"):
                st.session_state.session_total += weight_to_add

        # Display running total
        st.metric("Current Session Total", f"{st.session_state.session_total:,} lbs")

        # Main submit button
        submitted = st.form_submit_button("Add Workout")

        if submitted:
            try:
                # Combine date and time
                datetime_combined = datetime.combine(date, time)

                # Calculate remaining weight
                current_weight_left = float(st.session_state.data['Weight Left'].iloc[-1]) if not st.session_state.data.empty else GOAL_WEIGHT
                weight_left = current_weight_left - st.session_state.session_total

                new_entry = pd.DataFrame({
                    'Workout Area': [workout_area],
                    'Date': [datetime_combined],
                    'Total Lifted': [st.session_state.session_total],
                    'Weight Left': [weight_left]
                })

                # Update the data
                st.session_state.data = pd.concat([st.session_state.data, new_entry], ignore_index=True)

                # Reset session total
                st.session_state.session_total = 0

                st.success("Workout added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding workout: {str(e)}")

# Analytics Section
st.header("📊 Workout Analytics")

if not st.session_state.data.empty:
    # Create two columns for analytics
    col1, col2 = st.columns(2)

    with col1:
        # Breakdown by Workout Area
        workout_area_stats = st.session_state.data.groupby('Workout Area')['Total Lifted'].sum().reset_index()
        fig_breakdown = px.pie(workout_area_stats, 
                             values='Total Lifted', 
                             names='Workout Area',
                             title='Total Weight Lifted by Workout Area')
        st.plotly_chart(fig_breakdown, use_container_width=True)

    with col2:
        # Weekly Progress
        st.session_state.data['Week'] = st.session_state.data['Date'].dt.isocalendar().week
        weekly_progress = st.session_state.data.groupby('Week')['Total Lifted'].sum().reset_index()
        fig_weekly = px.bar(weekly_progress, 
                           x='Week', 
                           y='Total Lifted',
                           title='Weekly Progress')
        st.plotly_chart(fig_weekly, use_container_width=True)

    # Historical Data View
    st.header("📝 Historical Data")
    st.dataframe(
        st.session_state.data.sort_values('Date', ascending=False)
        [['Workout Area', 'Date', 'Total Lifted', 'Weight Left']]
        .style.format({
            'Total Lifted': '{:,.0f}',
            'Weight Left': '{:,.0f}'
        }),
        hide_index=True
    )

    # Summary Statistics
    st.header("📈 Summary Statistics")
    col1, col2, col3 = st.columns(3)

    # Calculate daily statistics
    daily_stats = st.session_state.data.groupby(st.session_state.data['Date'].dt.date).agg({
        'Total Lifted': 'sum',
        'Date': 'count'
    })

    with col1:
        st.metric("Average Weight per Session (Day)", 
                 f"{daily_stats['Total Lifted'].mean():,.0f} lbs")

    with col2:
        st.metric("Max Weight in Single Session (Day)", 
                 f"{daily_stats['Total Lifted'].max():,.0f} lbs")

    with col3:
        st.metric("Total Workout Sessions (Days)", 
                 len(daily_stats))
else:
    st.info("Add your first workout to see analytics!")