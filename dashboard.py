import streamlit as st
import json
import os
import pandas as pd
import altair as alt
import datetime
import csv
import psutil

# Function to load metrics from metrics.json
def load_metrics(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='UTF-8') as file:
            return json.load(file)
    return []

# Function to load logs from a log file (if any)
def load_logs(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='UTF-8') as file:
            return file.read()
    return "No logs available."

# Function to read reminders from reminders.csv
def read_csv(file_path):
    events = []
    with open(file_path, mode='r', encoding='UTF-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            event_name = row['Event name'].strip()
            event_date = datetime.datetime.strptime(row['Event date and time'].strip(), '%m/%d/%Y %H:%M:%S')
            event_weekday = row['Weekday'].strip()
            events.append({'name': event_name, 'date': event_date, 'weekday': event_weekday})
    return events

# Function to get system usage metrics
def get_system_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq_curr, cpu_freq_min, cpu_freq_max = psutil.cpu_freq()
    memory_info = psutil.virtual_memory()
    memory_swap = psutil.swap_memory()
    disk_usage = psutil.disk_usage('/')
    net_info  = psutil.net_if_stats()
    network_info = psutil.net_io_counters()
    network_sent = network_info.bytes_sent
    network_recv = network_info.bytes_recv
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    return cpu_usage, cpu_count, cpu_freq_curr, cpu_freq_min, cpu_freq_max, memory_info, memory_swap, disk_usage, net_info, network_sent, network_recv, uptime


# Load metrics and logs
metrics_file_path = 'metrics.json'
downloader_metrics_file_path = 'downloader_metrics.json'
logs_file_path = 'reminders.log'

metrics = load_metrics(metrics_file_path)
downloader_metrics = load_metrics(downloader_metrics_file_path)
logs = load_logs(logs_file_path)
downloader_logs = load_logs('downloader.log')

# Streamlit dashboard
st.set_page_config(page_title="Scripts Dashboard", layout="wide")
sidebar = st.sidebar
tab1, tab2, tab3 = st.tabs(["Dashboard", "System Info / Metrics", "Logs"])

# Sidebar
with sidebar:
    # Display System Usage
        st.subheader("Server Metrics")
        cpu_usage, cpu_count, cpu_freq_curr, cpu_freq_min, cpu_freq_max, memory_info, memory_swap, disk_usage, net_info, network_sent, network_recv, uptime = get_system_usage()
        st.metric(label="CPU Usage", value=f"{cpu_usage} %")
        st.progress(int(cpu_usage))
        st.metric(label="Memory Usage", value=f"{memory_info.percent} %")
        st.progress(int(memory_info.percent))
        st.write(f"{memory_info.used / (1024 ** 3):.2f} GB / {memory_info.total / (1024 ** 3):.2f} GB")
        st.metric(label="Disk Usage", value=f"{disk_usage.percent} %")
        st.progress(int(disk_usage.percent))
        st.metric(label="Network Sent", value=f"{network_sent / (1024 ** 2):.2f} MB")
        st.metric(label="Network Received", value=f"{network_recv / (1024 ** 2):.2f} MB")
        st.metric(label="System Uptime", value=str(uptime).split('.')[0])

# Dashboard
with tab1:
    column1, column2 = st.columns([1,1], gap="medium")

    # Display Reminders
    with column1:
        st.subheader("Reminders")
        events = read_csv("reminders.csv")
        if events:
            events_df = pd.DataFrame(events)
            
            # Calculate tomorrow's date
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            tomorrow_date = tomorrow.date()
            
            # Add a new column to indicate if the reminder is for tomorrow
            events_df['is_tomorrow'] = events_df['date'].dt.date == tomorrow_date
            
            st.dataframe(
                data=events_df,
                use_container_width=True,
                height=900,
                column_config={
                    "name": st.column_config.TextColumn(label="Event name"),
                    "date": st.column_config.DatetimeColumn(
                        label="Event date and time",
                        format="YYYY/MM/DD HH:mm:ss"),
                    "weekday": st.column_config.TextColumn(label="Weekday"),
                    "is_tomorrow": st.column_config.CheckboxColumn(label="Tomorrow's Reminder")})
        else:
            st.write("No reminders available.")

    with column2:
        # Display Metrics
        st.header("Metrics")
        if metrics:
            metrics_df = pd.DataFrame(metrics)
            dl_metrics_df = pd.DataFrame(downloader_metrics)

            # Convert timestamp to datetime and extract date
            metrics_df['timestamp'] = pd.to_datetime(metrics_df['timestamp'])
            metrics_df['date'] = metrics_df['timestamp'].dt.date
            dl_metrics_df['timestamp'] = pd.to_datetime(dl_metrics_df['timestamp'])
            dl_metrics_df['date'] = dl_metrics_df['timestamp'].dt.date

            graph1, graph2, graph3 = st.columns([1,1,1])

            # Plot the metrics
            with graph1:
                with st.container(border=True):
                    st.subheader("Tomorrow's Reminders")
                    current_value = metrics_df['reminders_tomorrow_count'].iloc[-1]
                    
                    # Only calculate delta if we have enough historical data
                    if len(metrics_df) >= 3:
                        delta = int(current_value - metrics_df['reminders_tomorrow_count'].iloc[-3])
                        st.metric(
                            label="Tomorrow's Reminders", 
                            value=current_value,
                            label_visibility="collapsed", 
                            delta=delta
                        )
                    else:
                        st.metric(
                            label="Tomorrow's Reminders", 
                            value=current_value,
                            label_visibility="collapsed"
                        )
                        
                metrics_chart = alt.Chart(metrics_df).mark_line().encode(
                    x='date:T',
                    y=alt.Y('reminders_tomorrow_count:Q', title=None),
                    tooltip=['date:T', 'reminders_tomorrow_count:Q']
                ).properties(
                    width=700,
                    height=300
                ).interactive(bind_x=True, bind_y=False)

                st.altair_chart(metrics_chart, use_container_width=True)
            
            with graph2:
                with st.container(border=True):
                    st.subheader("Next 3 Days' Reminders")
                    current_value = metrics_df['reminders_3days_count'].iloc[-1]
                    if len(metrics_df) >= 3:
                        delta = int(current_value - metrics_df['reminders_3days_count'].iloc[-3])
                        st.metric(label="Next 3 Days' Reminders", value=current_value, 
                                label_visibility="collapsed", delta=delta)
                    else:
                        st.metric(label="Next 3 Days' Reminders", value=current_value, 
                                label_visibility="collapsed")
                metrics_chart = alt.Chart(metrics_df).mark_line().encode(
                    x='date:T',
                    y=alt.Y('reminders_3days_count:Q', title=None),
                    tooltip=['date:T', 'reminders_3days_count:Q']
                ).properties(
                    width=700,
                    height=300
                ).interactive(bind_x=True, bind_y=False)
                st.altair_chart(metrics_chart, use_container_width=True)

            with graph3:
                with st.container(border=True):
                    st.subheader("Total Reminders")
                    current_value = metrics_df['total_reminders_count'].iloc[-1]
                    if len(metrics_df) >= 3:
                        delta = int(current_value - metrics_df['total_reminders_count'].iloc[-3])
                        st.metric(label="Total Reminders", value=current_value, 
                                label_visibility="collapsed", delta=delta)
                    else:
                        st.metric(label="Total Reminders", value=current_value, 
                                label_visibility="collapsed")
                metrics_chart = alt.Chart(metrics_df).mark_line().encode(
                    x='date:T',
                    y=alt.Y('total_reminders_count:Q', title=None),
                    tooltip=['date:T', 'total_reminders_count:Q']
                ).properties(
                    width=700,
                    height=300
                ).interactive(bind_x=True, bind_y=False)
                st.altair_chart(metrics_chart, use_container_width=True)

            # Display Performance Metrics
            st.subheader("Sheet Download time")
            if not dl_metrics_df.empty:
                current_time = dl_metrics_df['request_time'].iloc[-1]
                st.metric(label="Download time", 
                        value=f"{current_time.round(4)} s", 
                        label_visibility="collapsed")
                metrics_chart = alt.Chart(dl_metrics_df).mark_line().encode(
                    x='date:T',
                    y=alt.Y('request_time:Q', title=None),
                    tooltip=['date:T', 'request_time:Q']
                ).properties(
                    width=700,
                    height=250
                ).interactive(bind_x=True, bind_y=False)
                st.altair_chart(metrics_chart, use_container_width=True)
            else:
                st.write("No download metrics available.")

# System Info / Metrics
with tab2:
    st.header("System Info / Metrics")  
    col1, col2 = st.columns([1,1])
    with col1:
        st.subheader("System Information")
        boot, system = st.columns([1,1])
        with boot:
            st.write(f"Boot Time: {datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}")
        with system:
            st.write(f"System Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.subheader("CPU Info")
        info, freq = st.columns([1,1])
        with info:
            st.write(f"CPU Usage: {cpu_usage}%")
            st.write(f"CPU Count: {cpu_count}")
        with freq:
            st.write(f"CPU Frequency: {cpu_freq_curr:.2f} MHz")
            st.write(f"CPU Min Frequency: {cpu_freq_min:.2f} MHz")
            st.write(f"CPU Max Frequency: {cpu_freq_max:.2f} MHz")

        st.subheader("Memory Info")
        phys, swap = st.columns([1,1])
        with phys:
            st.write(f"Total Physical Memory: {memory_info.total / (1024 ** 3):.2f} GB")
            st.write(f"Memory Used: {memory_info.used / (1024 ** 3):.2f} GB")
            st.write(f"Physical Memory Usage: {memory_info.percent}%")
            st.progress(int(memory_info.percent))
        with swap:
            st.write(f"Total Swap Memory: {memory_swap.total / (1024 ** 3):.2f} GB")
            st.write(f"Swap Memory Used: {memory_swap.used / (1024 ** 3):.2f} GB")
            st.write(f"Swap Memory Usage: {memory_swap.percent}%")
            st.progress(int(memory_swap.percent))

        st.subheader("Disk Info")
        st.write(f"Disk Usage: {disk_usage.percent}%")
        st.write(f"Disk Used: {disk_usage.used / (1024 ** 3):.2f} GB")
        st.write(f"Disk Total: {disk_usage.total / (1024 ** 3):.2f} GB")

        st.subheader("Network Info")
        # Filter active interfaces
        active_interfaces = {iface: info for iface, info in net_info.items() if info.isup}

        if active_interfaces:
            # Create columns dynamically based on number of active interfaces
            cols = st.columns(len(active_interfaces))
            
            # Display each interface in its own column
            for (iface, iface_info), col in zip(active_interfaces.items(), cols):
                with col:
                    st.write(f"Interface: {iface}")
                    st.write(iface_info)
        else:
            st.write("No active network interfaces found")
        st.write(f"Network Sent: {network_sent / (1024 ** 2):.2f} MB")
        st.write(f"Network Received: {network_recv / (1024 ** 2):.2f} MB")
    with col2:
        st.subheader("System Uptime")
        st.write(f"System Uptime: {uptime}")

        st.subheader("System Processes")
        processes = []
        for process in psutil.process_iter(['pid', 'name', 'username']):
            processes.append(process.info)
        processes_df = pd.DataFrame(processes)
        st.dataframe(
            data=processes_df,
            use_container_width=True,
            height=500)

# Logs
with tab3:
    # Display Logs
    st.header("Logs")
    st.subheader("Reminders Log")
    st.text_area("Reminders Logs", value=logs, height=450, label_visibility="collapsed")
    st.subheader("Downloader Log")
    st.text_area("Downloader Logs", value=downloader_logs, height=450, label_visibility="collapsed")