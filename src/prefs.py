import json
import os
import datetime # Import datetime

PREFS_FILE = 'data/prefs.json'
FAN_HOME_CUSTOM_TEXT_FILE = 'data/fan_league_home_custom_text.md'

def _get_prefs_file_path():
    """Constructs the absolute path to the preferences file."""
    # Assuming data/prefs.json is relative to the project root
    # For now, it's relative to where the app is run from, adjust if needed.
    return os.path.join(os.getcwd(), PREFS_FILE)

def _get_fan_home_custom_text_file_path():
    """Constructs the absolute path to the fan home custom text file."""
    return os.path.join(os.getcwd(), FAN_HOME_CUSTOM_TEXT_FILE)

def load_fan_home_custom_text():
    """Loads the custom text for the fan mode homepage."""
    file_path = _get_fan_home_custom_text_file_path()
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def save_fan_home_custom_text(text):
    """Saves the custom text for the fan mode homepage."""
    file_path = _get_fan_home_custom_text_file_path()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

def load_preferences():
    """
    Loads preferences from data/prefs.json.
    Returns a dictionary of preferences, with default values if the file is not found
    or specific preferences are missing.
    """
    prefs_path = _get_prefs_file_path()
    prefs_data = {}
    default_prefs = {
        "league_name": "Fantasy Elite Wrestling",
        "league_short": "FEW",
        "fan_mode_show_logo": True,
        "fan_mode_header_name_display": "Full Name",
        "fan_mode_show_records": True,
        "fan_mode_show_profile_records": True, # New preference
        "fan_mode_show_contract_info": False,  # New preference
        "fan_mode_roster_sort_order": "Alphabetical",
        "fan_mode_show_future_events": True,
        "fan_mode_show_non_match_headers": True,
        "fan_mode_show_quick_results": True,
        "fan_mode_home_show_champions": True,
        "fan_mode_home_show_news": "Show Links Only",
        "fan_mode_home_number_news": 5,
        "fan_mode_home_show_recent_events": True,
        "fan_mode_home_number_events": 5,
        "fan_mode_injured_wrestler_display": "Show Normally",
        "fan_mode_suspended_roster_display": "Show Normally",
        "ai_provider": "",
        "ai_model": "",
        "google_api_key": "",
        "openai_api_key": "",
        "game_date_mode": "real-time", # New preference
        "game_date": datetime.date.today().isoformat(), # New preference
        "weight_unit": "lbs." # New preference for weight unit
    }

    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, 'r', encoding='utf-8') as f:
                json_list = json.load(f)
                for item in json_list:
                    if 'Pref' in item and 'Value' in item:
                        key = item['Pref'].lower() # Convert to lowercase for consistent access
                        prefs_data[key] = item['Value']
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {prefs_path}. Using default preferences.")
            prefs_data = {} # Reset to empty to be filled by defaults

    # Merge with defaults to ensure all expected preferences are present
    final_prefs = default_prefs.copy()
    final_prefs.update(prefs_data)
    
    return final_prefs

def save_preferences(prefs_dict):
    """
    Saves preferences to data/prefs.json.
    Expects a dictionary like {'league_name': '...', 'league_short': '...'}.
    """
    prefs_path = _get_prefs_file_path()
    
    # Convert back to the list of dictionaries format for saving
    json_list = [
        {"Pref": "League_Name", "Value": prefs_dict.get("league_name", "")},
        {"Pref": "League_Short", "Value": prefs_dict.get("league_short", "")},
        {"Pref": "Fan_Mode_Show_Logo", "Value": prefs_dict.get("fan_mode_show_logo", True)},
        {"Pref": "Fan_Mode_Header_Name_Display", "Value": prefs_dict.get("fan_mode_header_name_display", "Full Name")},
        {"Pref": "Fan_Mode_Show_Records", "Value": prefs_dict.get("fan_mode_show_records", True)},
        {"Pref": "Fan_Mode_Show_Profile_Records", "Value": prefs_dict.get("fan_mode_show_profile_records", True)}, # New preference
        {"Pref": "Fan_Mode_Show_Contract_Info", "Value": prefs_dict.get("fan_mode_show_contract_info", False)}, # New preference
        {"Pref": "Fan_Mode_Roster_Sort_Order", "Value": prefs_dict.get("fan_mode_roster_sort_order", "Alphabetical")},
        {"Pref": "Fan_Mode_Show_Future_Events", "Value": prefs_dict.get("fan_mode_show_future_events", True)},
        {"Pref": "Fan_Mode_Show_Non_Match_Headers", "Value": prefs_dict.get("fan_mode_show_non_match_headers", True)},
        {"Pref": "Fan_Mode_Show_Quick_Results", "Value": prefs_dict.get("fan_mode_show_quick_results", True)},
        {"Pref": "Fan_Mode_Home_Show_Champions", "Value": prefs_dict.get("fan_mode_home_show_champions", True)},
        {"Pref": "Fan_Mode_Home_Show_News", "Value": prefs_dict.get("fan_mode_home_show_news", "Show Links Only")},
        {"Pref": "Fan_Mode_Home_Number_News", "Value": prefs_dict.get("fan_mode_home_number_news", 5)},
        {"Pref": "Fan_Mode_Home_Show_Recent_Events", "Value": prefs_dict.get("fan_mode_home_show_recent_events", True)},
        {"Pref": "Fan_Mode_Home_Number_Events", "Value": prefs_dict.get("fan_mode_home_number_events", 5)},
        {"Pref": "Fan_Mode_Injured_Wrestler_Display", "Value": prefs_dict.get("fan_mode_injured_wrestler_display", "Show Normally")},
        {"Pref": "Fan_Mode_Suspended_Roster_Display", "Value": prefs_dict.get("fan_mode_suspended_roster_display", "Show Normally")},
        {"Pref": "AI_Provider", "Value": prefs_dict.get("ai_provider", "")},
        {"Pref": "AI_Model", "Value": prefs_dict.get("ai_model", "")},
        {"Pref": "Google_API_Key", "Value": prefs_dict.get("google_api_key", "")},
        {"Pref": "OpenAI_API_Key", "Value": prefs_dict.get("openai_api_key", "")},
        {"Pref": "Game_Date_Mode", "Value": prefs_dict.get("game_date_mode", "real-time")}, # New preference
        {"Pref": "Game_Date", "Value": prefs_dict.get("game_date", datetime.date.today().isoformat())}, # New preference
        {"Pref": "Weight_Unit", "Value": prefs_dict.get("weight_unit", "lbs.")} # New preference for weight unit
    ]

    os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
    with open(prefs_path, 'w', encoding='utf-8') as f:
        json.dump(json_list, f, indent=4)
