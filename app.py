"""
UK Road Casualties Dashboard (2021-2025)
Data: Department for Transport, STATS19 road safety data (cleaned, no missing values).

Keep this file in the same folder as:
    casualties_clean_no_missing.csv
    collisions_clean_no_missing.csv
    vehicles_clean_no_missing.csv

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------
st.set_page_config(page_title="UK Road Casualties Dashboard", page_icon="🚦", layout="wide")

DATA_DIR = Path(__file__).parent
FILES = {
    "casualties": "casualties_clean_no_missing.csv",
    "collisions": "collisions_clean_no_missing.csv",
    "vehicles": "vehicles_clean_no_missing.csv",
}

# ------------------------------------------------------------------
# Colours and icons (kept the same on every chart)
# ------------------------------------------------------------------
SEVERITY_ORDER = ["Fatal", "Serious", "Slight"]
SEVERITY_COLOURS = {"Fatal": "#C0392B", "Serious": "#F39C12", "Slight": "#5DADE2"}
SEVERITY_ICONS = {"Fatal": "⚫", "Serious": "🔴", "Slight": "🟡"}

SEX_COLOURS = {"Male": "#2E86C1", "Female": "#E75480"}
FUEL_COLOURS = {"Petrol": "#E67E22", "Diesel": "#566573", "Hybrid": "#58D68D",
                "Electric": "#1E8449", "Other": "#8E44AD",
                "Unknown": "#CCD1D1", "Not applicable (pedal cycle)": "#AED6F1"}
EV_COLOURS = {"Electric": "#1E8449", "Hybrid": "#58D68D"}

ROAD_USER_ICONS = {
    "Car occupant": "🚗", "Pedestrian": "🚶", "Motorcyclist": "🏍️", "Cyclist": "🚲",
    "Van occupant": "🚐", "Bus or coach occupant": "🚌", "Taxi occupant": "🚕",
    "E-scooter rider": "🛴", "HGV occupant": "🚛", "Mobility scooter rider": "🦽", "Other": "❔",
}
VEHICLE_ICONS = {
    "Car": "🚗", "Motorcycle": "🏍️", "Pedal cycle": "🚲", "Van": "🚐", "HGV": "🚛",
    "Bus or coach": "🚌", "Taxi": "🚕", "E-scooter": "🛴", "Agricultural vehicle": "🚜",
    "Mobility scooter": "🦽", "Other": "❔",
}

# Interactive condition pickers: data value -> label with icon
WEATHER_OPTIONS = {
    "Fine": "☀️ Fine", "Rain": "🌧️ Rain", "Snow": "❄️ Snow",
    "Fog or mist": "🌫️ Fog or mist", "Other": "🌬️ Other",
}
SURFACE_OPTIONS = {
    "Dry": "🛣️ Dry", "Wet or damp": "💧 Wet or damp", "Frost or ice": "🧊 Frost or ice",
    "Snow": "❄️ Snow", "Flood over 3cm deep": "🌊 Flooded",
}
LIGHT_OPTIONS = {
    "Daylight": "☀️ Daylight", "Darkness - lights lit": "💡 Dark, street lights on",
    "Darkness - lights unlit": "🔦 Dark, street lights off",
    "Darkness - no lighting": "🌑 Dark, no street lights",
}

AGE_GROUP_ORDER = ["0-15", "16-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
DRIVER_AGE_ORDER = ["0-5", "6-10", "11-15", "16-20", "21-25", "26-35", "36-45",
                    "46-55", "56-65", "66-75", "Over 75"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KSI = ["Fatal", "Serious"]


# ------------------------------------------------------------------
# Load data (read once, then cached)
# ------------------------------------------------------------------
def find_file(name):
    """Use the plain .csv if it's there, otherwise the compressed .csv.gz version."""
    for candidate in (DATA_DIR / name, DATA_DIR / f"{name}.gz"):
        if candidate.exists():
            return candidate
    return None


@st.cache_data(show_spinner="Loading the road safety data...")
def load_data():
    paths = {key: find_file(name) for key, name in FILES.items()}
    missing = [FILES[k] for k, p in paths.items() if p is None]
    if missing:
        return None, None, None, missing
    ids = {"collision_index": str}
    cas = pd.read_csv(paths["casualties"], dtype=ids)
    col = pd.read_csv(paths["collisions"], dtype=ids)
    veh = pd.read_csv(paths["vehicles"], dtype=ids)
    return cas, col, veh, []


cas_all, col_all, veh_all, missing_files = load_data()
if missing_files:
    st.error("⚠️ I can't find these files (.csv or .csv.gz) next to app.py:\n\n"
             + "\n".join(f"- {f}" for f in missing_files)
             + "\n\nPut them in the same folder as app.py, then refresh the page.")
    st.stop()


# ------------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------------
st.sidebar.title("🔎 Filters")
years = sorted(cas_all["collision_year"].unique())
year_range = st.sidebar.select_slider("📅 Years", options=years, value=(years[0], years[-1]))
severities = st.sidebar.multiselect(
    "🩹 Injury severity", SEVERITY_ORDER, default=SEVERITY_ORDER,
    format_func=lambda s: f"{SEVERITY_ICONS[s]} {s}")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Key**  \n"
    "⚫ **Fatal**: died within 30 days  \n"
    "🔴 **Serious**: needed hospital treatment  \n"
    "🟡 **Slight**: minor injury  \n"
    "**KSI** = killed or seriously injured"
)
st.sidebar.caption("Source: Department for Transport (STATS19), 2021-2025.")

in_years = lambda df: df[df["collision_year"].between(*year_range)]
cas = in_years(cas_all)
cas = cas[cas["casualty_severity"].isin(severities)]
col = in_years(col_all)
col = col[col["collision_severity"].isin(severities)]
veh = in_years(veh_all)

if cas.empty or col.empty:
    st.warning("Nothing matches these filters. Pick at least one injury severity.")
    st.stop()


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def fmt(n):
    return f"{n:,.0f}"


def pct(part, whole):
    return part / whole * 100 if whole else 0


def tidy(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=55, b=10),
                      plot_bgcolor="rgba(0,0,0,0)", legend_title_text="",
                      title_font_size=16)
    return fig


def note(text):
    """One plain sentence under a chart, saying what it shows."""
    st.caption(f"💬 {text}")


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("🚦 UK Road Casualties Dashboard")
st.markdown(f"Police-reported road collisions in Great Britain, **{year_range[0]} to {year_range[1]}**. "
            "Use the filters on the left to change the years or injury types.")

tabs = st.tabs(["📊 Overview", "🧍 Who gets hurt", "🕒 When it happens",
                "🌦️ Weather, light and roads", "🚗 Vehicles and drivers", "ℹ️ About the data"])

# ==================================================================
# 📊 OVERVIEW
# ==================================================================
with tabs[0]:
    total = len(cas)
    fatal = (cas["casualty_severity"] == "Fatal").sum()
    serious = (cas["casualty_severity"] == "Serious").sum()

    m = st.columns(4)
    m[0].metric("🩹 Casualties", fmt(total))
    m[1].metric("💥 Collisions", fmt(cas["collision_index"].nunique()))
    m[2].metric("⚫ People killed", fmt(fatal))
    m[3].metric("🚑 Killed or seriously injured", f"{pct(fatal + serious, total):.1f}%")

    st.info(f"📌 On average, about **{fmt(fatal / max(1, year_range[1] - year_range[0] + 1) / 365)} "
            f"people die** on Britain's roads every day in this period.")

    c1, c2 = st.columns([3, 2])
    by_year = (cas.groupby(["collision_year", "casualty_severity"]).size()
               .reset_index(name="casualties"))
    fig = px.bar(by_year, x="collision_year", y="casualties", color="casualty_severity",
                 title="Casualties each year, by injury severity",
                 category_orders={"casualty_severity": SEVERITY_ORDER},
                 color_discrete_map=SEVERITY_COLOURS)
    fig.update_xaxes(title="", type="category")
    fig.update_yaxes(title="Casualties")
    with c1:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("The number of people hurt each year has stayed at about 125,000 to 132,000.")

    sev = cas["casualty_severity"].value_counts().reindex(SEVERITY_ORDER).dropna().reset_index()
    sev.columns = ["severity", "casualties"]
    fig = px.pie(sev, names="severity", values="casualties", hole=0.55,
                 title="How badly people were hurt",
                 color="severity", color_discrete_map=SEVERITY_COLOURS)
    fig.update_traces(textinfo="percent+label", sort=False)
    with c2:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("About 1 in 5 casualties is killed or seriously injured.")

    sev_year = (cas.groupby(["collision_year", "casualty_severity"]).size()
                .reset_index(name="casualties"))
    fig = px.line(sev_year, x="collision_year", y="casualties", color="casualty_severity",
                  facet_col="casualty_severity", markers=True,
                  category_orders={"casualty_severity": SEVERITY_ORDER},
                  color_discrete_map=SEVERITY_COLOURS,
                  title="How each injury type changed over time (each panel has its own scale)")
    fig.update_yaxes(matches=None, showticklabels=True, rangemode="tozero", title="")
    fig.update_xaxes(type="category", title="")
    fig.update_traces(line_width=3, marker_size=9)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(showlegend=False)
    st.plotly_chart(tidy(fig, 330), use_container_width=True)
    note("Serious injuries have gone up, while slight injuries have gone down. Deaths have stayed about the same.")

# ==================================================================
# 🧍 WHO GETS HURT
# ==================================================================
with tabs[1]:
    users = (cas.groupby("casualty_type")
             .agg(casualties=("casualty_severity", "size"),
                  ksi_pct=("casualty_severity", lambda s: s.isin(KSI).mean() * 100))
             .reset_index())
    users["road_user"] = users["casualty_type"].map(lambda u: f"{ROAD_USER_ICONS.get(u, '❔')} {u}")

    view = st.radio("Show road users by:", ["👥 Number of casualties", "⚠️ Chance of being killed or seriously injured"],
                    horizontal=True)
    if view.startswith("👥"):
        d = users.sort_values("casualties")
        fig = px.bar(d, y="road_user", x="casualties", orientation="h", text_auto=",",
                     color="casualties", color_continuous_scale="Blues",
                     title="Which road users get hurt the most")
        fig.update_xaxes(title="Casualties")
        msg = "Car occupants are the biggest group, simply because most journeys are made by car."
    else:
        d = users.sort_values("ksi_pct")
        fig = px.bar(d, y="road_user", x="ksi_pct", orientation="h", text_auto=".1f",
                     color="ksi_pct", color_continuous_scale="Reds",
                     title="% of each road user group killed or seriously injured")
        fig.update_xaxes(title="% killed or seriously injured")
        msg = "Motorcyclists, pedestrians and e-scooter riders are about twice as likely as car occupants to be badly hurt."
    fig.update_yaxes(title="")
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(tidy(fig, 430), use_container_width=True)
    note(msg)

    c1, c2 = st.columns(2)
    ages = (cas.groupby(["age_group", "casualty_severity"]).size().reset_index(name="casualties"))
    fig = px.bar(ages, x="age_group", y="casualties", color="casualty_severity",
                 title="Casualties by age group",
                 category_orders={"age_group": AGE_GROUP_ORDER, "casualty_severity": SEVERITY_ORDER},
                 color_discrete_map=SEVERITY_COLOURS)
    fig.update_xaxes(title="Age group")
    fig.update_yaxes(title="Casualties")
    with c1:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("People aged 16 to 34 make up the largest share of casualties.")

    ksi_age = (cas[cas["casualty_severity"].isin(KSI)]
               .groupby("age_group").size().reindex(AGE_GROUP_ORDER).reset_index(name="ksi"))
    fig = px.bar(ksi_age, x="age_group", y="ksi", text_auto=",",
                 color="ksi", color_continuous_scale="OrRd",
                 title="People killed or seriously injured, by age group")
    fig.update_xaxes(title="Age group")
    fig.update_yaxes(title="Killed or seriously injured")
    fig.update_layout(coloraxis_showscale=False)
    with c2:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("Young people aged 16 to 24 have the most deaths and serious injuries.")

    c3, c4 = st.columns([2, 3])
    sex = cas["casualty_sex"].value_counts().reset_index()
    sex.columns = ["sex", "casualties"]
    fig = px.pie(sex, names="sex", values="casualties", hole=0.55, title="👨 Men and 👩 women",
                 color="sex", color_discrete_map=SEX_COLOURS)
    fig.update_traces(textinfo="percent+label")
    with c3:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("About 6 in 10 casualties are men.")

    sex_age = cas.groupby(["age_group", "casualty_sex"]).size().reset_index(name="casualties")
    fig = px.bar(sex_age, x="age_group", y="casualties", color="casualty_sex", barmode="group",
                 title="Men and women by age group",
                 category_orders={"age_group": AGE_GROUP_ORDER}, color_discrete_map=SEX_COLOURS)
    fig.update_xaxes(title="Age group")
    fig.update_yaxes(title="Casualties")
    with c4:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("The gap between men and women is widest among young adults.")

# ==================================================================
# 🕒 WHEN IT HAPPENS
# ==================================================================
with tabs[2]:
    m = st.columns(3)
    m[0].metric("💥 Collisions", fmt(len(col)))
    m[1].metric("🩹 Casualties in these collisions", fmt(col["number_of_casualties"].sum()))
    m[2].metric("⚫ Fatal collisions", fmt((col["collision_severity"] == "Fatal").sum()))

    heat = (col.groupby(["day_of_week", "hour"]).size().unstack(fill_value=0).reindex(DAY_ORDER))
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="YlOrRd",
                    labels=dict(x="Hour of the day (0 = midnight)", y="", color="Collisions"),
                    title="🕒 Busiest times for collisions")
    st.plotly_chart(tidy(fig, 360), use_container_width=True)
    note("Collisions peak on weekday afternoons between 3pm and 6pm, when people travel home from school and work.")

    c1, c2 = st.columns(2)
    night = col.assign(period=col["hour"].map(
        lambda h: "🌙 Night (10pm-5am)" if h >= 22 or h < 5 else "☀️ Day (5am-10pm)"))
    nf = night.groupby("period")["collision_severity"].apply(
        lambda s: (s == "Fatal").mean() * 100).reset_index(name="fatal_pct")
    fig = px.bar(nf, x="period", y="fatal_pct", text_auto=".1f", color="period",
                 color_discrete_sequence=["#F4D03F", "#1B2631"],
                 title="% of collisions that are fatal: day vs night")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="% fatal")
    fig.update_layout(showlegend=False)
    with c1:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("There are fewer collisions at night, but each one is about twice as likely to kill someone.")

    df_ = col.groupby("day_of_week")["collision_severity"].apply(
        lambda s: (s == "Fatal").mean() * 100).reindex(DAY_ORDER).reset_index(name="fatal_pct")
    fig = px.bar(df_, x="day_of_week", y="fatal_pct", text_auto=".2f",
                 color="fatal_pct", color_continuous_scale="Reds",
                 title="% of collisions that are fatal, by day of the week")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="% fatal")
    fig.update_layout(coloraxis_showscale=False)
    with c2:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("Weekend collisions, especially on Sundays, are more likely to be fatal.")

# ==================================================================
# 🌦️ WEATHER, LIGHT AND ROADS (interactive)
# ==================================================================
with tabs[3]:
    st.markdown("Pick a condition to see how dangerous it is compared with the average.")

    avg_fatal = pct((col["collision_severity"] == "Fatal").sum(), len(col))
    avg_ksi = pct(col["collision_severity"].isin(KSI).sum(), len(col))

    def condition_explorer(column, options, heading, key):
        st.subheader(heading)
        present = [k for k in options if k in set(col[column].dropna())]
        choice = st.radio("Choose one:", present, horizontal=True, key=key,
                          format_func=lambda k: options[k])
        sub = col[col[column] == choice]
        f = pct((sub["collision_severity"] == "Fatal").sum(), len(sub))
        k = pct(sub["collision_severity"].isin(KSI).sum(), len(sub))

        a, b, c, d = st.columns(4)
        a.metric(f"{options[choice]} collisions", fmt(len(sub)))
        b.metric("Share of all collisions", f"{pct(len(sub), len(col)):.1f}%")
        c.metric("⚫ Fatal", f"{f:.2f}%", delta=f"{f - avg_fatal:+.2f} pts vs average",
                 delta_color="inverse")
        d.metric("🚑 Killed or seriously injured", f"{k:.1f}%",
                 delta=f"{k - avg_ksi:+.1f} pts vs average", delta_color="inverse")

        summary = (col[col[column].isin(present)]
                   .groupby(column)["collision_severity"]
                   .apply(lambda s: (s == "Fatal").mean() * 100).reset_index(name="fatal_pct"))
        summary["label"] = summary[column].map(options)
        summary["highlight"] = summary[column].map(lambda v: "Selected" if v == choice else "Others")
        summary = summary.sort_values("fatal_pct")
        fig = px.bar(summary, y="label", x="fatal_pct", orientation="h", text_auto=".2f",
                     color="highlight",
                     color_discrete_map={"Selected": "#C0392B", "Others": "#D5D8DC"},
                     title=f"% of collisions that are fatal, by {heading.split(' ', 1)[1].lower()}")
        fig.add_vline(x=avg_fatal, line_dash="dash", line_color="#566573",
                      annotation_text="average", annotation_position="top")
        fig.update_xaxes(title="% fatal")
        fig.update_yaxes(title="")
        fig.update_layout(showlegend=False)
        st.plotly_chart(tidy(fig, 300), use_container_width=True)

    condition_explorer("weather_conditions", WEATHER_OPTIONS, "🌦️ Weather", "weather")
    note("Fog is the most dangerous weather per collision, but most fatal crashes happen in fine weather, "
         "when roads are busier and people drive faster.")
    st.divider()

    condition_explorer("light_conditions", LIGHT_OPTIONS, "💡 Light", "light")
    note("Roads with no street lights at night are almost 4 times as deadly as roads in daylight.")
    st.divider()

    condition_explorer("road_surface_conditions", SURFACE_OPTIONS, "🛣️ Road surface", "surface")
    note("Wet and flooded roads are a little more dangerous than dry roads.")
    st.divider()

    st.subheader("🚸 Speed limit and area")
    c1, c2 = st.columns(2)
    sp = (col.groupby("speed_limit")["collision_severity"]
          .apply(lambda s: (s == "Fatal").mean() * 100).reset_index(name="fatal_pct"))
    sp["speed_limit"] = sp["speed_limit"].astype(int).astype(str) + " mph"
    fig = px.bar(sp, x="speed_limit", y="fatal_pct", text_auto=".1f",
                 color="fatal_pct", color_continuous_scale="Reds",
                 title="% of collisions that are fatal, by speed limit")
    fig.update_xaxes(title="Speed limit")
    fig.update_yaxes(title="% fatal")
    fig.update_layout(coloraxis_showscale=False)
    with c1:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("A crash on a 60 mph road is about 7 times as likely to be fatal as one on a 20 mph road.")

    area = (col.groupby("area_type")
            .agg(collisions=("collision_index", "size"),
                 fatal=("collision_severity", lambda s: (s == "Fatal").sum())).reset_index())
    area["Share of all collisions"] = area["collisions"] / area["collisions"].sum() * 100
    area["Share of fatal collisions"] = area["fatal"] / max(1, area["fatal"].sum()) * 100
    area_long = area.melt(id_vars="area_type",
                          value_vars=["Share of all collisions", "Share of fatal collisions"],
                          var_name="measure", value_name="percent")
    area_long["area_type"] = area_long["area_type"].map({"Urban": "🏙️ Urban", "Rural": "🌳 Rural"})
    fig = px.bar(area_long, x="measure", y="percent", color="area_type", barmode="group",
                 text_auto=".0f", title="Urban and rural roads",
                 color_discrete_map={"🏙️ Urban": "#7F8C8D", "🌳 Rural": "#27AE60"})
    fig.update_xaxes(title="")
    fig.update_yaxes(title="%")
    with c2:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("Rural roads have about a third of collisions but nearly two thirds of fatal ones.")

    st.subheader("📍 Where fatal collisions happened")
    fatal_points = (col[col["collision_severity"] == "Fatal"][["latitude", "longitude"]]
                    .dropna().rename(columns={"latitude": "lat", "longitude": "lon"}))
    if len(fatal_points):
        st.map(fatal_points, size=200, color="#C0392B")
        note(f"Each red dot is one fatal collision ({fmt(len(fatal_points))} in total). Zoom in to see local roads.")

# ==================================================================
# 🚗 VEHICLES AND DRIVERS
# ==================================================================
with tabs[4]:
    m = st.columns(3)
    m[0].metric("🚗 Vehicles involved", fmt(len(veh)))
    m[1].metric("👨 Male drivers", f"{(veh['sex_of_driver'] == 'Male').mean() * 100:.0f}%")
    m[2].metric("🎂 Typical driver age", f"{veh['age_of_driver'].median():.0f} years")

    c1, c2 = st.columns(2)
    vt = veh["vehicle_type"].value_counts().sort_values().reset_index()
    vt.columns = ["vehicle_type", "vehicles"]
    vt["label"] = vt["vehicle_type"].map(lambda v: f"{VEHICLE_ICONS.get(v, '❔')} {v}")
    fig = px.bar(vt, y="label", x="vehicles", orientation="h", text_auto=",",
                 color="vehicles", color_continuous_scale="Blues",
                 title="Types of vehicle involved")
    fig.update_xaxes(title="Vehicles")
    fig.update_yaxes(title="")
    fig.update_layout(coloraxis_showscale=False)
    with c1:
        st.plotly_chart(tidy(fig, 430), use_container_width=True)
        note("Two in three vehicles involved are cars.")

    hide = st.toggle("Hide unknown fuel and pedal cycles", value=True)
    fuel = veh["propulsion_code"]
    if hide:
        fuel = fuel[~fuel.isin(["Unknown", "Not applicable (pedal cycle)"])]
    fu = fuel.value_counts().reset_index()
    fu.columns = ["fuel", "vehicles"]
    fig = px.pie(fu, names="fuel", values="vehicles", hole=0.5, title="⛽ Fuel type",
                 color="fuel", color_discrete_map=FUEL_COLOURS)
    fig.update_traces(textinfo="percent+label")
    with c2:
        st.plotly_chart(tidy(fig, 380), use_container_width=True)
        note("Petrol and diesel still make up most vehicles in collisions.")

    c3, c4 = st.columns(2)
    ev = (veh[veh["propulsion_code"].isin(["Electric", "Hybrid"])]
          .groupby(["collision_year", "propulsion_code"]).size().reset_index(name="vehicles"))
    fig = px.line(ev, x="collision_year", y="vehicles", color="propulsion_code", markers=True,
                  title="🔋 Electric and hybrid vehicles in collisions", color_discrete_map=EV_COLOURS)
    fig.update_traces(line_width=3, marker_size=9)
    fig.update_xaxes(title="", type="category")
    fig.update_yaxes(title="Vehicles", rangemode="tozero")
    with c3:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("Electric vehicles in collisions have tripled since 2021, as more people buy them.")

    da = (veh.groupby(["age_band_of_driver", "sex_of_driver"]).size().reset_index(name="vehicles"))
    fig = px.bar(da, x="age_band_of_driver", y="vehicles", color="sex_of_driver",
                 title="Drivers by age and sex",
                 category_orders={"age_band_of_driver": DRIVER_AGE_ORDER},
                 color_discrete_map=SEX_COLOURS)
    fig.update_xaxes(title="Driver age")
    fig.update_yaxes(title="Vehicles")
    with c4:
        st.plotly_chart(tidy(fig), use_container_width=True)
        note("Drivers aged 26 to 35 are involved in the most collisions.")

    med = veh.groupby("vehicle_type")["age_of_driver"].median().sort_values().reset_index()
    med["label"] = med["vehicle_type"].map(lambda v: f"{VEHICLE_ICONS.get(v, '❔')} {v}")
    fig = px.bar(med, y="label", x="age_of_driver", orientation="h", text_auto=".0f",
                 color="age_of_driver", color_continuous_scale="Purples",
                 title="Typical (median) driver age for each vehicle type")
    fig.update_xaxes(title="Age in years")
    fig.update_yaxes(title="")
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(tidy(fig, 420), use_container_width=True)
    note("E-scooter riders are the youngest (around 23) and mobility scooter users the oldest (around 67).")

# ==================================================================
# ℹ️ ABOUT THE DATA
# ==================================================================
with tabs[5]:
    st.subheader("📁 The three datasets")
    st.dataframe(pd.DataFrame({
        "Dataset": ["🩹 Casualties", "💥 Collisions", "🚗 Vehicles"],
        "One row is": ["One person killed or injured", "One reported road collision",
                       "One vehicle involved in a collision"],
        "Rows": [fmt(len(cas_all)), fmt(len(col_all)), fmt(len(veh_all))],
        "Columns": [cas_all.shape[1], col_all.shape[1], veh_all.shape[1]],
    }), hide_index=True, use_container_width=True)

    st.subheader("📖 Words used in this dashboard")
    st.markdown(
        """
| Term | Meaning |
|---|---|
| **Collision** | A road crash reported to the police where at least one person was injured |
| **Casualty** | A person killed or injured in a collision |
| **Fatal** | The person died within 30 days of the collision |
| **Serious** | An injury needing hospital treatment, such as a broken bone |
| **Slight** | A minor injury, such as a sprain or bruise |
| **KSI** | Killed or seriously injured |
| **Road user** | Anyone using the road: drivers, passengers, pedestrians, cyclists and riders |
| **Rural / urban** | Outside or inside a town or city with 10,000+ people |
        """
    )

    st.subheader("🧹 How the data was cleaned")
    st.markdown(
        """
- 📥 **Source:** Department for Transport road safety data (STATS19), 2021-2025.
- ✂️ **Rows with missing values were removed**: 17,231 casualties (2.6%), 33,620 collisions (6.5%)
  and 159,326 vehicles (17%). So totals here are a little lower than the official figures.
- 🗑️ **Dropped columns:** journey purpose and vehicle age had too many gaps (76% and 39% missing).
- ⛽ **Fuel type:** gaps were filled. Pedal cycles became "Not applicable", e-scooters "Electric",
  and the rest "Unknown".
- ⚠️ **Limits:** only crashes reported to the police are included. More police forces now use a
  newer injury system (CRASH), which records more injuries as serious, so part of the rise in
  serious injuries comes from that change.
        """
    )

    st.subheader("👀 Look at the data")
    choice = st.selectbox("Dataset", ["Casualties", "Collisions", "Vehicles"])
    preview = {"Casualties": cas, "Collisions": col, "Vehicles": veh}[choice]
    st.dataframe(preview.head(200), use_container_width=True)
    st.download_button(f"⬇️ Download filtered {choice.lower()} (CSV)",
                       preview.to_csv(index=False).encode("utf-8"),
                       file_name=f"{choice.lower()}_filtered.csv", mime="text/csv")
