import json
import os
from src.wrestlers import get_wrestler_by_name

TAGTEAMS_FILE_RELATIVE_TO_ROOT = 'data/tagteams.json'

def _get_members_list_from_team_data(team_data):
    """
    Extracts a list of member names from team data, handling both string (pipe-separated)
    and list formats for the 'Members' field.
    """
    members_data = team_data.get('Members')
    if isinstance(members_data, list):
        return members_data
    elif isinstance(members_data, str):
        return [m.strip() for m in members_data.split('|') if m.strip()]
    return []

def _get_list_from_data_field(data_field):
    """
    Extracts a list of items from a data field, handling both string (pipe-separated)
    and list formats. Returns an empty list if the field is None or empty.
    """
    if isinstance(data_field, list):
        return data_field
    elif isinstance(data_field, str):
        return [item.strip() for item in data_field.split('|') if item.strip()]
    return []

def _get_tagteams_file_path():
    """Constructs the absolute path to the tagteams data file."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(project_root, TAGTEAMS_FILE_RELATIVE_TO_ROOT)

def load_tagteams():
    """Loads tag-team data from the JSON file and ensures 'Members' is a string."""
    filepath = _get_tagteams_file_path()
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        tagteams = json.load(f)
    
    # Ensure 'Members', 'Moves', and 'Awards' fields are always lists after loading
    for team in tagteams:
        team['Members'] = _get_list_from_data_field(team.get('Members'))
        team['Moves'] = _get_list_from_data_field(team.get('Moves'))
        team['Awards'] = _get_list_from_data_field(team.get('Awards'))
    return tagteams

def save_tagteams(tagteams_list):
    """Saves tag-team data to the JSON file, ensuring 'Members' is a '|' separated string."""
    filepath = _get_tagteams_file_path()
    
    # Create a copy to modify before saving, so the original list in memory isn't altered
    # if it's being used elsewhere in the current execution context.
    tagteams_to_save = []
    for team in tagteams_list:
        team_copy = team.copy()
        
        # Convert 'Members', 'Moves', and 'Awards' lists back to pipe-separated strings for saving
        for field in ['Members', 'Moves', 'Awards']:
            data = team_copy.get(field)
            if isinstance(data, list):
                team_copy[field] = '|'.join(data)
            elif not isinstance(data, str):
                team_copy[field] = '' # Ensure it's a string even if empty

        tagteams_to_save.append(team_copy)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(tagteams_to_save, f, indent=4)

def get_tagteam_by_name(name):
    """Retrieves a single tag-team by its name."""
    return next((tt for tt in load_tagteams() if tt['Name'] == name), None)

def add_tagteam(tagteam_data):
    """Adds a new tag-team to the list."""
    tagteams = load_tagteams()
    tagteams.append(tagteam_data)
    save_tagteams(tagteams)

def update_tagteam(original_name, updated_data):
    """Updates an existing tag-team's data."""
    tagteams = load_tagteams()
    for i, tt in enumerate(tagteams):
        if tt['Name'] == original_name:
            tagteams[i] = updated_data
            break
    save_tagteams(tagteams)

def delete_tagteam(name):
    """Deletes a tag-team by its name."""
    tagteams = [tt for tt in load_tagteams() if tt['Name'] != name]
    save_tagteams(tagteams)

def get_wrestler_names():
    """Returns a list of all wrestler names."""
    from src.wrestlers import load_wrestlers
    return sorted([w['Name'] for w in load_wrestlers()])

def _calculate_tagteam_weight(member_names):
    """Calculates the combined weight of tag team members."""
    from src.wrestlers import load_wrestlers # Import here to avoid circular dependency
    all_wrestlers = load_wrestlers()
    total_weight = 0
    for member_name in member_names:
        if member_name:
            wrestler = next((w for w in all_wrestlers if w['Name'] == member_name), None)
            if wrestler:
                    # Extract only numeric part if weight includes units (e.g., "250 lbs")
                    # Ensure weight is treated as an integer for calculation
                    weight_str = str(wrestler.get('Weight', '0')).split(' ')[0]
                    try:
                        total_weight += int(weight_str)
                    except ValueError:
                        # Handle cases where weight is not a valid number, treat as 0
                        pass
    return str(total_weight) if total_weight > 0 else ''

def recalculate_all_tagteam_weights():
    """
    Recalculates the weight for all tag teams based on their current members
    and updates the tagteam data.
    """
    all_tagteams = load_tagteams()
    updated_count = 0
    for team in all_tagteams:
        member_names = _get_members_list_from_team_data(team)
        
        if member_names:
            new_weight = _calculate_tagteam_weight(member_names)
            if team.get('Weight') != new_weight:
                team['Weight'] = new_weight
                updated_count += 1
        elif team.get('Weight') != '': # If no members, weight should be empty
            team['Weight'] = ''
            updated_count += 1
            
    if updated_count > 0:
        save_tagteams(all_tagteams)
    return updated_count

def get_active_members_status(member_names):
    """Checks if all specified members are active."""
    for member_name in member_names:
        if member_name:
            wrestler = get_wrestler_by_name(member_name)
            if wrestler and wrestler.get('Status') != 'Active':
                return False
    return True

def update_tagteam_record(team_name, result):
    """Updates a tag team's win/loss/draw record."""
    all_tagteams = load_tagteams()
    team_found = False
    for team in all_tagteams:
        if team['Name'] == team_name:
            team_found = True
            if result == 'Win':
                team['Wins'] = str(int(team.get('Wins', 0)) + 1)
            elif result == 'Loss':
                team['Losses'] = str(int(team.get('Losses', 0)) + 1)
            elif result == 'Draw':
                team['Draws'] = str(int(team.get('Draws', 0)) + 1)
            break
    if team_found:
        save_tagteams(all_tagteams)
    return team_found

def reset_all_tagteam_records():
    """Sets all win/loss/draw records for every tag team to 0."""
    all_tagteams = load_tagteams()
    for team in all_tagteams:
        team['Wins'] = '0'
        team['Losses'] = '0'
        team['Draws'] = '0'
    save_tagteams(all_tagteams)

