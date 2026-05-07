#!/usr/bin/env python3
"""
PNW Trail Planner -- CS361 Main Program (Milestone #1).

A text-based CLI that helps a hiker plan multi-night PNW backcountry
trips. All microservice-backed data is mocked in data.py for this
sprint.

Run with: python3 main.py
"""

import os
import sys
from data import HOME_CITIES, TRAILS, FORECASTS, DAYLIGHT, DRIVE_TIMES


# ---------------------------------------------------------------------------
# Defaults used by the Reliability quality attribute when forecast data
# for a day is missing. Conservative-by-design.
# ---------------------------------------------------------------------------
FALLBACK_FORECAST = {
    "high_f": 50,
    "low_f": 40,
    "summary": "data unavailable -- assuming rain",
    "wind_mph": 15,
    "precip": "light",
}

# Extreme-weather thresholds (Safety quality attribute).
WIND_DANGER_MPH = 40
TEMP_DANGER_LOW_F = 20
TEMP_DANGER_HIGH_F = 95
HEAVY_PRECIP = {"heavy_snow", "heavy_rain", "thunderstorms"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def clear_screen():
    """Clear the terminal so each view starts on a fresh screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner_top():
    print("=" * 62)
    print("                  PNW TRAIL PLANNER".ljust(62))
    print("=" * 62)


def prompt_for_choice(valid_choices, allow_help=True):
    """Get a numeric choice from the user. Returns the chosen string.
    """
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return "0"

        if allow_help and raw == "?":
            return "?"
        if raw in valid_choices:
            return raw
        print(f"  (please type one of: {', '.join(sorted(valid_choices))}"
              + (", or ?)" if allow_help else ")"))


def fetch_forecast_safe(trail_id):
    #Return (forecast_days, used_fallback_for_any_day).

    #Implements Reliability NFR: when a microservice returns missing data
    #for a day, fall back to conservative defaults rather than crashing.

    raw_days = FORECASTS.get(trail_id, [])
    used_fallback = False
    safe_days = []
    for day in raw_days:
        # Detect missing data: any required field is None.
        if (day.get("high_f") is None or day.get("low_f") is None
                or day.get("summary") is None or day.get("wind_mph") is None
                or day.get("precip") is None):
            used_fallback = True
            safe_days.append({
                "date": day["date"],
                "high_f": FALLBACK_FORECAST["high_f"],
                "low_f": FALLBACK_FORECAST["low_f"],
                "summary": FALLBACK_FORECAST["summary"],
                "wind_mph": FALLBACK_FORECAST["wind_mph"],
                "precip": FALLBACK_FORECAST["precip"],
                "_is_fallback": True,
            })
        else:
            safe_days.append({**day, "_is_fallback": False})
    return safe_days, used_fallback


def detect_extreme_weather(forecast_days):
    #Return list of human-readable reasons the forecast is dangerous.
    reasons = []
    for d in forecast_days:
        if d["wind_mph"] is not None and d["wind_mph"] >= WIND_DANGER_MPH:
            reasons.append(
                f"sustained winds {d['wind_mph']} mph on {d['date']}")
        if d["low_f"] is not None and d["low_f"] < TEMP_DANGER_LOW_F:
            reasons.append(
                f"overnight low {d['low_f']} F on {d['date']}")
        if d["high_f"] is not None and d["high_f"] > TEMP_DANGER_HIGH_F:
            reasons.append(f"high {d['high_f']} F on {d['date']}")
        if d.get("precip") in HEAVY_PRECIP:
            reasons.append(f"{d['precip'].replace('_',' ')} on {d['date']}")
    return reasons


def drive_time_str(home_city, trail_id):
    if home_city is None:
        return "(set home city to see drive time)"
    hours, minutes = DRIVE_TIMES.get((home_city, trail_id), (0, 0))
    return f"{hours} hr {minutes} min from {home_city}"


# ---------------------------------------------------------------------------
# Packing list (User Story: Generate condition-aware packing list)
# ---------------------------------------------------------------------------
def build_packing_list(forecast_days, num_nights):
    #Return a categorized packing list with conditional items flagged.

    #Each item is (name, is_conditional). Total is between 15 and 20.
    
    has_rain = any(d["precip"] in {"light", "heavy_rain"} for d in forecast_days)
    has_snow = any(d["precip"] in {"snow", "heavy_snow"} for d in forecast_days)
    cold_night = any(d["low_f"] is not None and d["low_f"] < 32
                     for d in forecast_days)
    high_wind = any(d["wind_mph"] is not None and d["wind_mph"] >= 20
                    for d in forecast_days)
    hot = any(d["high_f"] is not None and d["high_f"] >= 85
              for d in forecast_days)

    # Base list (always present).
    shelter = [
        ("Tent (3-season)" if not has_snow else "4-season tent", has_snow),
        ("Sleeping bag (rated 30 F)" if not cold_night
         else "Sleeping bag (rated 0 F)", cold_night),
        ("Sleeping pad", False),
        ("Ground cloth", False),
    ]
    clothing = [
        ("Base layer top & bottom", False),
        ("Hiking pants", False),
        ("Insulating mid-layer", False),
        (f"Hiking socks ({num_nights + 1} pairs)", False),
    ]
    food_water = [
        (f"Meals ({num_nights + 1}) -- scaled for {num_nights} nights", False),
        ("Water filter", False),
        ("Fuel canister (1)", False),
        ("Stove & cookpot", False),
    ]
    nav_safety = [
        ("Map & compass", False),
        ("Headlamp", False),
        ("First-aid kit", False),
    ]
    weather = []

    if cold_night:
        clothing.append(("Insulated jacket", True))
        clothing.append(("Warm hat & gloves", True))
    if high_wind:
        clothing.append(("Windbreaker shell", True))
    if has_rain or has_snow:
        weather.append(("Rain jacket", True))
        weather.append(("Pack cover", True))
    if hot:
        weather.append(("Electrolyte tablets", True))
        weather.append(("Extra water bottle", True))

    return [
        ("Shelter & Sleep",     shelter),
        ("Clothing",            clothing),
        ("Food & Water",        food_water),
        ("Navigation & Safety", nav_safety),
        ("Weather-specific",    weather),
    ]


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def view_home_city_setup():
    """View 1 -- first-run home city picker.

    Returns the chosen home city string, or None if user skipped.
    """
    clear_screen()
    print_banner_top()
    print("              Welcome to your trip planner".ljust(62))
    print("=" * 62)
    print()
    print("Before we start, pick the city you usually drive from.")
    print("We'll use this to estimate drive time to each trailhead.")
    print()
    print("[ABOUT] Your home city stays on this device only -- it")
    print("isn't shared or uploaded. You can change it any time")
    print("from the main menu.")
    print()
    print("Pick your home city:")
    valid = set()
    for i, city in enumerate(HOME_CITIES, start=1):
        print(f"   {i}) {city}")
        valid.add(str(i))
    print("   0) Skip for now (drive times will be hidden)")
    valid.add("0")
    print()
    print("Type ? at any prompt for help.")
    print()
    while True:
        choice = prompt_for_choice(valid)
        if choice == "?":
            view_help()
            return view_home_city_setup()
        if choice == "0":
            return None
        return HOME_CITIES[int(choice) - 1]


def view_main_menu(home_city):
    """View 2 -- main menu."""
    clear_screen()
    print_banner_top()
    print(f"Home city: {home_city if home_city else '(not set)'}")
    print("=" * 62)
    print()
    print("What would you like to do?")
    print()
    print("   1) Browse all trails")
    print("   2) Change home city")
    print("   3) Help / How to use this app")
    print("   4) Quit")
    print()
    print("Type ? at any prompt for help.")
    print()
    return prompt_for_choice({"1", "2", "3", "4"})


def view_trail_list(home_city):
    """View 3 -- trail list."""
    clear_screen()
    print("=" * 62)
    print(f"  TRAIL LIST                          "
          f"Showing {len(TRAILS)} of {len(TRAILS)} trails")
    print("=" * 62)
    print()
    print("  #   TRAIL                REGION  DIST     GAIN    DIFF      PERMIT")
    print("  --  -------------------  ------  -------  ------  --------  ------")
    valid = {"0"}
    for i, t in enumerate(TRAILS, start=1):
        hazard = " [HAZARD]" if t["hazard_flag"] else ""
        permit_short = "Yes" if t["permit"] != "Not required" else "No"
        print(f"   {i}) {t['name']:<19} {t['region']:<6}  "
              f"{t['distance_mi']:>4.1f} mi  {t['elevation_gain_ft']:>4} ft  "
              f"{t['difficulty']:<8}  {permit_short:<3}{hazard}")
        valid.add(str(i))
    print()
    print("   0) Back to main menu")
    print()
    print("Pick a trail number to see details, weather, and packing list.")
    print("Type ? for help.")
    print()
    return prompt_for_choice(valid)


def view_trip_setup(trail):
    """View 5 -- prompt for nights for the chosen trail."""
    clear_screen()
    print("=" * 62)
    print(f"  TRIP SETUP                                      {trail['name']}")
    print("=" * 62)
    print()
    print(f"You picked: {trail['name']} ({trail['area']}, {trail['region']})")
    print(f"{trail['distance_mi']} mi round trip, "
          f"{trail['elevation_gain_ft']} ft gain, "
          f"{trail['difficulty']}, {trail['permit']}")
    print()
    print("Now set your trip length so we can fetch the right forecast")
    print("and tailor the packing list.")
    print()
    print("Number of nights (1-5):")
    while True:
        try:
            raw = input("> ").strip()
            if raw == "?":
                view_help()
                continue
            if raw == "0":
                return None
            n = int(raw)
            if 1 <= n <= 5:
                return n
        except ValueError:
            pass
        print("  (please type a number from 1 to 5, or 0 to cancel)")


def view_trail_details(trail, num_nights, home_city):
    """View 6 -- combined details with optional hazard banner / fallback."""
    forecast, used_fallback = fetch_forecast_safe(trail["id"])
    daylight = DAYLIGHT.get(trail["id"], [])
    hazard_reasons = detect_extreme_weather(forecast)
    if trail["hazard_flag"]:
        hazard_reasons.insert(0, f"trail flagged for {trail['hazard_flag']}")

    clear_screen()
    print("=" * 62)
    print(f"  {trail['name'].upper()}")
    print(f"  {trail['area']}, {trail['region']}")
    print("=" * 62)
    print()

    # Safety NFR: hazard banner FIRST, before any other content.
    if hazard_reasons:
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
        print("        CONDITIONS UNSAFE -- CONSIDER RESCHEDULING")
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
        for r in hazard_reasons:
            print(f"  - {r}")
        print("  We recommend picking a different trail or date.")
        print("*** *** *** *** *** *** *** *** *** *** *** *** *** *** ***")
        print()

    # Reliability NFR: yellow-equivalent fallback notice.
    if used_fallback:
        print("[NOTICE] Forecast data was unavailable for one or more")
        print("days in your trip window. The packing list below uses")
        print("conservative defaults (assume rain, 40 F, winds 15 mph)")
        print("for those days.")
        print()

    print("TRAIL INFO")
    print(f"  Distance:        {trail['distance_mi']} mi round trip")
    print(f"  Elevation gain:  {trail['elevation_gain_ft']} ft")
    print(f"  Difficulty:      {trail['difficulty']}")
    print(f"  Permit:          {trail['permit']}")
    print(f"  Drive time:      {drive_time_str(home_city, trail['id'])}")
    if trail["hazard_flag"]:
        print(f"  Hazard flag:     {trail['hazard_flag']}")
    print()

    print("TRIP FORECAST")
    for d in forecast[:num_nights + 1]:
        flag = "  <- fallback" if d.get("_is_fallback") else ""
        print(f"  {d['date']:<10}  {d['high_f']:>2} / {d['low_f']:>2} F   "
              f"{d['summary']:<32}  Wind {d['wind_mph']} mph{flag}")
    print()

    print("DAYLIGHT")
    for d in daylight[:num_nights + 1]:
        print(f"  {d['date']:<10}  Sunrise {d['sunrise']}   "
              f"Sunset {d['sunset']}   {d['total']}")
    print()

    print("-" * 62)
    packing = build_packing_list(forecast[:num_nights + 1], num_nights)
    total_items = sum(len(items) for _, items in packing)
    print(f"PACKING LIST ({total_items} items)")
    print(f"Tailored to a {num_nights}-night trip. Items marked [*] were")
    print("added because of the forecast.")
    print("-" * 62)
    for cat_name, items in packing:
        if not items:
            continue
        print()
        print(f"  {cat_name}")
        for name, conditional in items:
            mark = "[*]" if conditional else "[ ]"
            print(f"    {mark} {name}")
    print()
    print("   1) See more trail details (parking, dogs, season notes)")
    print("   2) Change trip length")
    print("   0) Back to trail list")
    print()
    while True:
        c = prompt_for_choice({"0", "1", "2"})
        if c == "?":
            view_help()
            continue
        if c == "1":
            print()
            print(f"NOTES: {trail['notes']}")
            print()
            input("(press Enter to return)")
            continue
        return c


def view_help():
    """View 7 -- help."""
    clear_screen()
    print("=" * 62)
    print("  HELP -- HOW TO USE PNW TRAIL PLANNER")
    print("=" * 62)
    print()
    print("WHAT THIS APP DOES")
    print("  PNW Trail Planner helps you plan multi-night backcountry")
    print("  trips on Pacific Northwest trails. It combines trail data,")
    print("  weather forecast, daylight, and drive time so you don't")
    print("  have to check four different websites before a trip.")
    print()
    print("THE TYPICAL TASK PATH")
    print("  1. Pick a trail from the trail list.")
    print("  2. Set your trip length (number of nights).")
    print("  3. Review conditions, hazards, daylight, and drive time.")
    print("  4. Use the tailored packing list to pack for actual")
    print("     forecasted conditions, not generic gear lists.")
    print()
    print("WHAT IT COSTS YOU")
    print("  - Time: about 2 minutes per trip plan.")
    print("  - Privacy: nothing is uploaded; your home city stays on")
    print("    this device only.")
    print("  - Data: this is a planning tool, not a substitute for")
    print("    checking ranger updates and current closures.")
    print()
    print("GETTING UNSTUCK")
    print("  - Type 0 at any menu to go back one step.")
    print("  - Type ? at any prompt to see this help (it is also")
    print("    available as option 3 from the main menu).")
    print()
    print("SAFETY")
    print("  Any trail with a hazard flag (closure, avalanche, fire) or")
    print("  with extreme weather in the forecast will show a clearly")
    print("  marked warning above the trail details. Do not ignore")
    print("  those warnings.")
    print()
    input("Press Enter to return to the previous menu.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run():
    home_city = view_home_city_setup()

    while True:
        choice = view_main_menu(home_city)

        if choice == "?":
            view_help()
            continue
        if choice == "4":
            print()
            print("Goodbye -- happy trails.")
            return
        if choice == "3":
            view_help()
            continue
        if choice == "2":
            home_city = view_home_city_setup()
            continue

        # choice == "1": browse all trails
        list_choice = view_trail_list(home_city)
        if list_choice == "?":
            view_help()
            continue
        if list_choice == "0":
            continue
        trail = TRAILS[int(list_choice) - 1]

        nights = view_trip_setup(trail)
        if nights is None:
            continue

        # Allow "change trip length" loop on details screen.
        while True:
            details_choice = view_trail_details(trail, nights, home_city)
            if details_choice == "2":
                nights = view_trip_setup(trail)
                if nights is None:
                    break
                continue
            break  # 0 -> back to trail list


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print()
        print("Interrupted. Goodbye -- happy trails.")
        sys.exit(0)