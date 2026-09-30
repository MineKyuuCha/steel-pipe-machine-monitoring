"""
app.py
------
Steel Pipe Production Monitoring System - Streamlit dashboard.

Reads from PostgreSQL. receiver.py (fed by the ESP32) writes events in
via database.insert_event() -- this file only ever reads.

The live-updating parts of the page are wrapped in @st.fragment blocks,
so only those sections refresh on a timer -- the header, sidebar nav,
and page chrome stay still instead of the whole page flashing every
refresh.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from database import (
    init_db,
    MACHINES,
    compute_today_stats,
    get_recent_events,
    format_duration,
)

st.set_page_config(
    page_title="Steel Pipe Production Monitoring",
    page_icon="\U0001F3ED",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# Two different refresh speeds: the clock/cards are cheap to redraw and
# look nicer updating quickly. The chart is the most expensive thing to
# rebuild each cycle (a brand new Plotly figure every time) and doesn't
# need to be that fast -- ON/OFF status doesn't change sub-second, so a
# slower chart refresh removes most of the visible "flash" without
# losing anything meaningful.
FAST_REFRESH_SECONDS = 1
SLOW_REFRESH_SECONDS = 10

# ---------------------------------------------------------------- styling --
# This CSS forces a consistent dark look regardless of the Streamlit Cloud
# "theme" setting, so it looks the same for every viewer.
st.markdown(
    """
    <style>
    .stApp { background-color: #0b1120; }
    section[data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }

    /* General fallback: without this, plain st.subheader()/markdown text
       inherits Streamlit's default light-theme grey, which is nearly
       invisible against our dark background. */
    h1, h2, h3, h4, h5, h6 { color: #f8fafc !important; }
    p, span, label, li, strong { color: #e5e7eb; }

    .header-title { font-size: 28px; font-weight: 800; color: #f8fafc; margin-bottom: 0; }
    .header-sub { color: #94a3b8; font-size: 14px; margin-top: 2px; }
    .header-meta { text-align: right; color: #e5e7eb; font-size: 14px; line-height: 1.8; }

    .ov-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 18px 20px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }
    .ov-label { color: #9ca3af; font-size: 12px; font-weight: 700; letter-spacing: 0.04em; }
    .ov-value { color: #f8fafc; font-size: 30px; font-weight: 700; margin-top: 6px; }
    .ov-icon {
        width: 46px; height: 46px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 20px;
    }

    .machine-card {
        border-radius: 12px; padding: 16px 18px; background-color: #111827;
        border: 1px solid #1f2937; box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }
    .machine-card hr { border-color: #263041; margin: 8px 0; }
    .status-badge {
        color: white; padding: 3px 12px; border-radius: 6px;
        font-size: 12px; font-weight: 700; letter-spacing: 0.5px;
    }
    .machine-power-icon {
        width: 46px; height: 46px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 20px;
    }
    .machine-power-icon.on { background: rgba(34,197,94,0.15); color: #22c55e; box-shadow: 0 0 14px rgba(34,197,94,0.4); }
    .machine-power-icon.off { background: rgba(239,68,68,0.15); color: #ef4444; box-shadow: 0 0 14px rgba(239,68,68,0.3); }
    .card-row { color: #9ca3af; margin: 3px 0; font-size: 14px; }
    .card-row b { color: #f3f4f6; }

    .event-row { font-size: 14px; padding: 7px 0; border-bottom: 1px solid #1f2937; color: #e5e7eb; }
    .sysinfo-row { display: flex; justify-content: space-between; font-size: 13px; color: #9ca3af; padding: 4px 0; }
    .sysinfo-row b { color: #e5e7eb; }

    /* Pill-style buttons for the timeline's time-range selector */
    div[data-testid="stRadio"] div[role="radiogroup"] { gap: 6px; }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background: #111827; border: 1px solid #263041; border-radius: 999px;
        padding: 4px 16px; margin-right: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

COLORS = {"A": "#22c55e", "B": "#3b82f6"}

# --------------------------------------------------------------- sidebar --
# The nav menu itself is static -- it only reruns when clicked, never on
# a timer, so it never needs to be inside a fragment.
with st.sidebar:
    st.markdown("### \U0001F3ED Steel Pipe Monitor")

    try:
        from streamlit_option_menu import option_menu
        page = option_menu(
            menu_title=None,
            options=["Dashboard", "Machines", "History", "Reports", "Settings"],
            icons=["bar-chart-line", "diagram-3", "clock-history", "file-earmark-text", "gear"],
            default_index=0,
            styles={
                "container": {"padding": "0", "background-color": "#0f172a"},
                "icon": {"color": "#93c5fd", "font-size": "16px"},
                "nav-link": {"font-size": "14px", "color": "#cbd5e1", "margin": "2px 0", "border-radius": "6px"},
                "nav-link-selected": {"background-color": "#2563eb", "color": "white"},
            },
        )
    except ImportError:
        page = st.radio(
            "Navigate", ["Dashboard", "Machines", "History", "Reports", "Settings"],
            index=0, label_visibility="collapsed",
        )

    st.markdown("---")


@st.fragment(run_every=FAST_REFRESH_SECONDS)
def render_sidebar_system_info():
    """Only this small block re-runs on a timer -- the nav above it stays still."""
    stats = {m: compute_today_stats(m) for m in MACHINES}
    machines_on = sum(1 for m in MACHINES if stats[m]["current_status"] == "ON")
    machines_off = len(MACHINES) - machines_on
    now = datetime.now()

    with st.sidebar:
        st.markdown("**SYSTEM INFO**")
        st.markdown(
            f"""
            <div class="sysinfo-row"><span>Connected Nodes</span><b>{len(MACHINES)}</b></div>
            <div class="sysinfo-row"><span>Online</span><b>{machines_on}</b></div>
            <div class="sysinfo-row"><span>Offline</span><b>{machines_off}</b></div>
            <div class="sysinfo-row"><span>Last Update</span><b>{now.strftime('%H:%M:%S')}</b></div>
            """,
            unsafe_allow_html=True,
        )


render_sidebar_system_info()

if page != "Dashboard":
    st.markdown(f"## {page}")
    st.info("This section is coming soon in a later version of the prototype.")
    st.stop()


def overview_card(col, label, value, icon, bg):
    with col:
        st.markdown(
            f"""
            <div class="ov-card">
                <div>
                    <div class="ov-label">{label}</div>
                    <div class="ov-value">{value}</div>
                </div>
                <div class="ov-icon" style="background-color:{bg};">{icon}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


@st.fragment(run_every=FAST_REFRESH_SECONDS)
def render_fast_section():
    """
    The cheap-to-redraw parts: header clock, overview cards, machine
    status cards. Refreshes quickly with minimal visible flash since
    none of this involves rebuilding a chart.
    """
    stats = {m: compute_today_stats(m) for m in MACHINES}
    machines_on = sum(1 for m in MACHINES if stats[m]["current_status"] == "ON")
    machines_off = len(MACHINES) - machines_on
    combined_on_seconds = sum(stats[m]["total_on_seconds"] for m in MACHINES)
    now = datetime.now()

    # ------------------------------------------------------------ header --
    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.markdown(
            '<p class="header-title">\U0001F3ED STEEL PIPE PRODUCTION MONITORING SYSTEM</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="header-sub">Real-time Machine Status Monitoring</p>', unsafe_allow_html=True)
    with head_r:
        st.markdown(
            f"""
            <div class="header-meta">
                <div>{now.strftime('%d %B %Y')}</div>
                <div>\U0001F550 {now.strftime('%H:%M:%S')}</div>
                <div><span style="color:#22c55e;">\u25CF</span> System Online</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ----------------------------------------------------------- overview --
    st.subheader("Overview")
    c1, c2, c3, c4 = st.columns(4)
    overview_card(c1, "TOTAL MACHINES", len(MACHINES), "\U0001F916", "#1d4ed8")
    overview_card(c2, "MACHINES ON", machines_on, "\u23FB", "#15803d")
    overview_card(c3, "MACHINES OFF", machines_off, "\u23FB", "#b91c1c")
    overview_card(c4, "COMBINED ON TIME", format_duration(combined_on_seconds), "\u23F1\ufe0f", "#b45309")

    st.divider()

    # ------------------------------------------------------- machine cards --
    st.subheader("Machine Status")
    cols = st.columns(len(MACHINES))

    for col, m in zip(cols, MACHINES):
        s = stats[m]
        is_on = s["current_status"] == "ON"
        badge_color = "#16a34a" if is_on else "#dc2626"
        since_txt = s["since"].strftime("%H:%M:%S") if s["since"] else "-"
        running_txt = format_duration(s["running_seconds"]) if s["since"] else "-"
        running_label = "Running Time" if is_on else "Off Duration"
        icon_class = "on" if is_on else "off"

        with col:
            st.markdown(
                f"""
                <div class="machine-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#f3f4f6;">
                            <span style="color:{badge_color};">\u25CF</span> MACHINE {m}
                        </span>
                        <span class="status-badge" style="background-color:{badge_color};">{s['current_status']}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:14px; margin:14px 0;">
                        <div class="machine-power-icon {icon_class}">\u23FB</div>
                        <div style="flex:1;">
                            <p class="card-row">Since <b>{since_txt}</b></p>
                            <p class="card-row">{running_label} <b>{running_txt}</b></p>
                        </div>
                    </div>
                    <hr>
                    <p class="card-row">Total ON Today <b style="color:{COLORS.get(m)};">{format_duration(s['total_on_seconds'])}</b></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()


@st.fragment(run_every=SLOW_REFRESH_SECONDS)
def render_slow_section():
    """
    The expensive-to-redraw parts: the Plotly chart, recent events, and
    summary table. Refreshes less often on purpose -- ON/OFF status
    doesn't change sub-second, so there's nothing lost by updating this
    section every few seconds instead of every one.
    """
    stats = {m: compute_today_stats(m) for m in MACHINES}

    # ---------------------------------------------------- chart + events --
    chart_col, events_col = st.columns([2, 1])

    with chart_col:
        st.subheader("Machine Status Timeline")

        range_options = {
            "Last 15 min": timedelta(minutes=15),
            "Last 1 hour": timedelta(hours=1),
            "Last 6 hours": timedelta(hours=6),
            "Last 12 hours": timedelta(hours=12),
            "Today": None,
        }
        selected_range = st.radio(
            "Time range", list(range_options.keys()), index=4,
            horizontal=True, label_visibility="collapsed", key="timeline_range",
        )

        fig = go.Figure()

        day_start = datetime.combine(date.today(), datetime.min.time())
        now = datetime.now()
        window = range_options[selected_range]
        range_start = max(day_start, now - window) if window else day_start

        # Give each machine its own horizontal level.
        machine_y = {m: i for i, m in enumerate(reversed(MACHINES))}

        for m in MACHINES:
            timeline = stats[m]["timeline"]

            # Remove invalid/duplicate timestamps
            clean_timeline = []
            for t, status in timeline:
                if t <= now:
                    if not clean_timeline or t > clean_timeline[-1][0]:
                        clean_timeline.append((t, status))

            if not clean_timeline:
                clean_timeline = [(day_start, "OFF")]

            current_status = stats[m]["current_status"]
            if clean_timeline[-1][0] < now:
                clean_timeline.append((now, current_status))

            y = machine_y[m]

            # Two separate traces per machine: a thick colored bar while
            # ON, a thin muted-gray bar while OFF. This is what actually
            # encodes status -- before, the color never changed with
            # status at all, which is the bug you spotted. The color
            # change itself marks each transition, so no separate
            # marker glyph is needed on top of it.
            on_x, on_y = [], []
            off_x, off_y = [], []

            for i in range(len(clean_timeline) - 1):
                start_time, status = clean_timeline[i]
                end_time, _ = clean_timeline[i + 1]

                target_x, target_y = (on_x, on_y) if status == "ON" else (off_x, off_y)
                target_x.extend([start_time, end_time, end_time])
                target_y.extend([y, y, None])

            fig.add_trace(
                go.Scatter(
                    x=on_x, y=on_y, mode="lines", name=f"Machine {m}",
                    line=dict(width=14, color=COLORS.get(m, "#3b82f6")),
                    connectgaps=False,
                    hovertemplate=f"<b>Machine {m} \u2014 ON</b><br>%{{x|%H:%M:%S}}<extra></extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=off_x, y=off_y, mode="lines", name=f"Machine {m} (OFF)",
                    line=dict(width=6, color="#374151"),
                    connectgaps=False, showlegend=False,
                    hovertemplate=f"<b>Machine {m} \u2014 OFF</b><br>%{{x|%H:%M:%S}}<extra></extra>",
                )
            )

        fig.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=70, r=20, t=20, b=40),

            xaxis=dict(
                title="Time",
                range=[range_start, now],
                tickformat="%H:%M",
                showgrid=True,
                gridcolor="#1f2937",
            ),

            yaxis=dict(
                title="",
                tickmode="array",
                tickvals=[machine_y[m] for m in reversed(MACHINES)],
                ticktext=[f"Machine {m}" for m in reversed(MACHINES)],
                range=[-0.5, len(MACHINES) - 0.5],
                showgrid=False,
                fixedrange=True,
            ),

            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),

            paper_bgcolor="#0b1120",
            plot_bgcolor="#0b1120",
            uirevision="machine-status-timeline",
        )

        st.plotly_chart(
            fig, use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False, "scrollZoom": True},
        )
        st.caption("Colored bar = ON \u00b7 Gray bar = OFF \u2014 hover a bar for the exact time")

    with events_col:
        st.subheader("Recent Events")
        events = get_recent_events(8)
        if not events:
            st.caption("No events yet -- waiting for machine data.")
        for ev in events:
            icon = "\U0001F7E2" if ev["status"] == "ON" else "\U0001F534"
            t_str = ev["timestamp"].strftime("%H:%M:%S")
            color = "#22c55e" if ev["status"] == "ON" else "#ef4444"
            st.markdown(
                f"""<div class="event-row">{icon} <b>{t_str}</b> \u2014 Machine {ev['machine_name']}
                <span style="float:right; color:{color}; font-weight:700;">{ev['status']}</span></div>""",
                unsafe_allow_html=True,
            )

    st.divider()


@st.fragment(run_every=FAST_REFRESH_SECONDS)
def render_summary_section():
    """
    Today's Summary, on its own fast timer so Total ON Time and OFF Time
    visibly tick up live, second by second -- separate from the slower
    chart/events section above, since a small table is cheap to redraw
    often but a full Plotly chart isn't.
    """
    stats = {m: compute_today_stats(m) for m in MACHINES}

    st.subheader("Today's Summary")
    rows = []
    for m in MACHINES:
        s = stats[m]
        rows.append(
            {
                "Machine": f"Machine {m}",
                "Status": s["current_status"],
                "First ON": s["first_on"].strftime("%H:%M:%S") if s["first_on"] else "-",
                "Total ON Time": format_duration(s["total_on_seconds"]),
                "OFF Time": format_duration(s["total_off_seconds"]),
                "Utilization %": round(s["utilization_pct"], 1),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Utilization %": st.column_config.ProgressColumn(
                "Utilization", min_value=0, max_value=100, format="%.1f%%"
            )
        },
    )


render_fast_section()
render_slow_section()
render_summary_section()