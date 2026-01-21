import json
import os
import re
import unicodedata
import uuid

from .prefs import load_preferences
from .wrestlers import load_wrestlers
from .tagteams import load_tagteams
from .belts import load_belts # Added for championship logic

# Base directories
DATA_DIR = 'data'
EVENTS_DATA_DIR = os.path.join(DATA_DIR, 'events')
INCLUDES_DIR = 'includes'
TMP_DIR = os.path.join(INCLUDES_DIR, 'tmp')

# File paths for static data (relative to project root)
WRESTLERS_FILE = os.path.join(DATA_DIR, 'wrestlers.json')
TAGTEAMS_FILE = os.path.join(DATA_DIR, 'tagteams.json')


def _classify_match(sides):
    """
    Classifies a match based on its sides array.
    """
    num_sides = len(sides)
    all_single_wrestlers = all(len(side) == 1 for side in sides)
    any_side_has_multiple_wrestlers = any(len(side) > 1 for side in sides)

    if any_side_has_multiple_wrestlers:
        return "tag"
    elif all_single_wrestlers and num_sides >= 10:
        return "battle_royal"
    elif all_single_wrestlers and 2 <= num_sides <= 9:
        return "singles"
    else:
        return "other"

def _get_all_wrestlers_involved(sides):
    """Extracts all unique wrestler names involved in the match from the sides structure."""
    wrestlers = set()
    for side in sides:
        for participant in side:
            wrestlers.add(participant)
    return list(wrestlers)

def _get_all_tag_teams_involved(sides, all_tagteams_data):
    """
    Identifies tag teams from the provided `sides` that match known tag teams.
    """
    teams = set()
    team_member_sets = {
        team_data.get('Name'): set(_get_members_list_from_team_data(team_data))
        for team_data in all_tagteams_data if team_data.get('Name') and team_data.get('Members')
    }
    
    for side in sides:
        side_members_set = set(side)
        for team_name, members_set in team_member_sets.items():
            if members_set.issubset(side_members_set) and len(members_set) > 1:
                teams.add(team_name)
    
    return list(teams)

def _generate_side_display_string(side, all_tagteams_data):
    """Generates a display string for a single side, expanding tag teams."""
    side_set = set(side)
    # Find teams whose members are fully contained within this side
    contained_teams = [
        team for team in all_tagteams_data 
        if set(_get_members_list_from_team_data(team)).issubset(side_set) and len(_get_members_list_from_team_data(team)) > 1
    ]
    
    # Get all wrestlers who are part of the found teams
    wrestlers_in_teams = set()
    for team in contained_teams:
        for member in _get_members_list_from_team_data(team):
            wrestlers_in_teams.add(member)
            
    # Get wrestlers who are not in any of the found teams
    independent_wrestlers = [w for w in side if w not in wrestlers_in_teams]
    
    # Build the string parts
    parts = []
    for team in contained_teams:
        members_str = ", ".join(_get_members_list_from_team_data(team))
        parts.append(f"{team['Name']} ({members_str})")
    
    parts.extend(independent_wrestlers)
    
    return ", ".join(parts)

def _generate_match_result_string(match_data, all_tagteams_data):
    """Constructs the match result string, e.g., 'Winner(s) def. Loser(s) (Time)'."""
    winning_idx = match_data.get('winning_side_index')
    if winning_idx is None or winning_idx == -1:
        return "Result not determined."

    sides = match_data.get('sides', [])
    if not (0 <= winning_idx < len(sides)):
        return "Invalid winning side."

    winning_side_participants = sides[winning_idx]
    losing_sides_participants = [side for i, side in enumerate(sides) if i != winning_idx]

    winning_side_str = _generate_side_display_string(winning_side_participants, all_tagteams_data)
    
    losing_sides_strs = [_generate_side_display_string(side, all_tagteams_data) for side in losing_sides_participants]
    losing_side_str = ", ".join(losing_sides_strs)

    match_time = match_data.get('match_time')
    time_str = f"({match_time})" if match_time else ""

    return f"{winning_side_str} def. {losing_side_str} {time_str}".strip()

def generate_match_result_display_string(match_data, all_tagteams_data, all_belts_data):
    """
    Generates a human-readable display string for a match result.
    """
    sides = match_data.get('sides', [])
    winning_side_index = match_data.get('winning_side_index', -1)
    match_result_overall = match_data.get('match_result', '') # e.g., "Side 1 (...) wins", "Draw (Time limit)"
    winner_method = match_data.get('winner_method', '')
    match_championship = match_data.get('match_championship', '')
    match_time = match_data.get('match_time', '')

    display_parts = []
    
    def _get_side_display(side_participants):
        return _generate_side_display_string(side_participants, all_tagteams_data)

    if winning_side_index != -1 and 0 <= winning_side_index < len(sides):
        # It's a win/loss scenario
        winning_side_participants = sides[winning_side_index]
        losing_sides_participants = [side for i, side in enumerate(sides) if i != winning_side_index]

        winner_str = _get_side_display(winning_side_participants)
        loser_str = ", ".join([_get_side_display(side) for side in losing_sides_participants if side])

        display_parts.append(f"{winner_str} def. {loser_str}")

        if winner_method:
            display_parts.append(f"by {winner_method}")

        if match_championship:
            belt = next((b for b in all_belts_data if b.get('Name') == match_championship), None)
            if belt:
                current_holder = belt.get('Current_Holder')
                is_retain = False
                if current_holder:
                    if belt.get('Holder_Type') == 'Tag-Team':
                        winning_side_members = set(winning_side_participants)
                        team_members = set(next((_get_members_list_from_team_data(t) for t in all_tagteams_data if t['Name'] == current_holder), []))
                        if team_members and team_members.issubset(winning_side_members):
                            is_retain = True
                    else: # Singles
                        if current_holder in winning_side_participants:
                            is_retain = True
                
                if is_retain:
                    display_parts.append(f"to retain the {match_championship}")
                else:
                    display_parts.append(f"to win the {match_championship}")

    else:
        # It's a draw or no contest
        if sides:
            participant_display_for_draw = " vs ".join([_get_side_display(side) for side in sides])
            # The overall_match_result already contains the "ended in a ..." part for draws/no contests
            if match_result_overall:
                # For draws/no contests, format as "ended in a [result]"
                display_parts.append(f"{participant_display_for_draw} ended in a {match_result_overall.lower()}")
            else:
                display_parts.append(participant_display_for_draw) # Fallback if overall result is empty
        elif match_result_overall:
            # If no sides but overall result exists (e.g., "No contest" without participants)
            display_parts.append(f"Ended in a {match_result_overall.lower()}")

    final_string = " ".join(display_parts)

    if match_time:
        final_string += f" ({match_time})"

    return final_string

def _prepare_match_data_for_storage(match_data_input, all_wrestlers_data, all_tagteams_data):
    """
    Prepares match data for storage, including classifying the match,
    initializing individual and team results, and setting default options.
    """
    prepared_match_data = match_data_input.copy()
    sides = prepared_match_data.get('sides', [])

    # Always re-classify the match based on the current sides
    prepared_match_data["match_class"] = _classify_match(sides)

    all_wrestlers_in_match = _get_all_wrestlers_involved(sides)
    all_teams_in_match = _get_all_tag_teams_involved(sides, all_tagteams_data)

    # Initialize or update individual results
    if "individual_results" not in prepared_match_data:
        prepared_match_data["individual_results"] = {}
    
    for wrestler in all_wrestlers_in_match:
        if wrestler not in prepared_match_data["individual_results"]:
            prepared_match_data["individual_results"][wrestler] = "No Contest"
    
    current_wrestler_results_keys = list(prepared_match_data["individual_results"].keys())
    for wrestler_key in current_wrestler_results_keys:
        if wrestler_key not in all_wrestlers_in_match:
            del prepared_match_data["individual_results"][wrestler_key]

    # Initialize or update team results
    if "team_results" not in prepared_match_data:
        prepared_match_data["team_results"] = {}
    
    for team in all_teams_in_match:
        if team not in prepared_match_data["team_results"]:
            prepared_match_data["team_results"][team] = "No Contest"

    current_team_results_keys = list(prepared_match_data["team_results"].keys())
    for team_key in current_team_results_keys:
        if team_key not in all_teams_in_match:
            del prepared_match_data["team_results"][team_key]

    if "winning_side_index" not in prepared_match_data:
        prepared_match_data["winning_side_index"] = -1

    if "sync_teams_to_individuals" not in prepared_match_data:
        prepared_match_data["sync_teams_to_individuals"] = True

    # NEW: Ensure overall match result and winner method fields exist
    if "match_result" not in prepared_match_data:
        prepared_match_data["match_result"] = ""

    if "winner_method" not in prepared_match_data:
        prepared_match_data["winner_method"] = ""

    if "match_result_display" not in prepared_match_data:
        prepared_match_data["match_result_display"] = ""

    # NEW: Ensure match_visibility fields exist with defaults
    if "match_visibility" not in prepared_match_data:
        prepared_match_data["match_visibility"] = {
            'hide_from_card': False,
            'hide_summary': False,
            'hide_result': False,
        }
    else:
        # Ensure all sub-keys are present if match_visibility exists but is incomplete
        prepared_match_data["match_visibility"].setdefault('hide_from_card', False)
        prepared_match_data["match_visibility"].setdefault('hide_summary', False)
        prepared_match_data["match_visibility"].setdefault('hide_result', False)


    return prepared_match_data

def _sync_team_results_to_individuals(match_results, all_tagteams_data):
    """
    Synchronizes team results to individual members.
    """
    if not match_results.get("sync_teams_to_individuals", True):
        return match_results

    team_results = match_results.get("team_results", {})
    individual_results = match_results.get("individual_results", {})
    
    team_members_map = {
        team_data['Name']: _get_members_list_from_team_data(team_data)
        for team_data in all_tagteams_data if 'Name' in team_data and 'Members' in team_data
    }

    for team_name, result in team_results.items():
        if team_name in team_members_map:
            for member in team_members_map[team_name]:
                individual_results[member] = result
    
    match_results["individual_results"] = individual_results
    return match_results

def _validate_match_structure(sides):
    """
    Validates the structure of match sides, checking for empty sides or unbalanced teams.
    Returns a list of warning messages.
    """
    warnings = []
    num_sides = len(sides)
    if num_sides == 0:
        warnings.append("Match has no sides specified.")
        return warnings

    side_lengths = [len(side) for side in sides]
    
    if any(length == 0 for length in side_lengths):
        warnings.append("Some sides have no wrestlers specified.")
        
    if len(set(side_lengths)) > 1:
        min_members = min(side_lengths)
        max_members = max(side_lengths)
        warnings.append(f"Match sides appear unbalanced (e.g., sides have {min_members} to {max_members} wrestlers). Review match structure.")

    return warnings

def _validate_result_completeness(match_results, sides, all_wrestlers_in_match, all_teams_in_match, all_tagteams_data):
    """
    Validates the completeness and consistency of match results.
    Returns a list of warning messages.
    """
    warnings = []
    overall_match_result = match_results.get("match_result")
    individual_results = match_results.get("individual_results", {})
    team_results = match_results.get("team_results", {})
    winning_side_index = match_results.get("winning_side_index")

    if not overall_match_result:
        warnings.append("Overall match result is not set.")

    valid_results = ["Win", "Loss", "Draw", "No Contest"]
    for wrestler in all_wrestlers_in_match:
        if wrestler not in individual_results or individual_results[wrestler] not in valid_results:
            warnings.append(f"Result missing or invalid for wrestler: {wrestler}")
    
    for team in all_teams_in_match:
        if team not in team_results or team_results[team] not in valid_results:
            warnings.append(f"Result missing or invalid for team: {team}")

    if winning_side_index is not None and winning_side_index != -1 and 0 <= winning_side_index < len(sides):
        winning_side_members = set(sides[winning_side_index])
        
        for wrestler in winning_side_members:
            if individual_results.get(wrestler) != "Win":
                warnings.append(f"Wrestler '{wrestler}' on declared winning side has result '{individual_results.get(wrestler, 'N/A')}' instead of 'Win'.")
        
        for i, side in enumerate(sides):
            if i != winning_side_index:
                for wrestler in side:
                    if individual_results.get(wrestler) == "Win":
                        warnings.append(f"Wrestler '{wrestler}' on a non-winning side has result 'Win'.")
        
        team_members_map = {
            team_data['Name']: set(_get_members_list_from_team_data(team_data))
            for team_data in all_tagteams_data if 'Name' in team_data and 'Members' in team_data
        }
        
        for team_name in all_teams_in_match:
            if team_name in team_members_map:
                members_of_this_team = team_members_map[team_name]
                is_team_on_winning_side = members_of_this_team.issubset(winning_side_members)
                
                if is_team_on_winning_side:
                    if team_results.get(team_name) != "Win":
                        warnings.append(f"Team '{team_name}' (on winning side) has result '{team_results.get(team_name, 'N/A')}' instead of 'Win'.")
                else:
                    if team_results.get(team_name) == "Win":
                        warnings.append(f"Team '{team_name}' (on non-winning side) has result 'Win'.")

    return warnings

from .tagteams import _get_members_list_from_team_data # Import the helper from tagteams

def _get_project_root():
    """Returns the absolute path to the project root directory."""
    current_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(current_dir, os.pardir))


def _get_segments_file_path(event_slug):
    """Constructs the absolute path to the segments JSON file for a given event."""
    root = _get_project_root()
    return os.path.join(root, EVENTS_DATA_DIR, f'{event_slug}_segments.json')


def _get_matches_file_path(event_slug):
    """Constructs the absolute path to the matches JSON file for a given event."""
    root = _get_project_root()
    return os.path.join(root, EVENTS_DATA_DIR, f'{event_slug}_matches.json')


def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf-8')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value


def _get_summary_file_path(event_slug, segment_type, header, position):
    """Constructs the absolute path to a segment's summary Markdown file."""
    root = _get_project_root()
    event_tmp_dir = os.path.join(root, TMP_DIR, _slugify(event_slug))
    header_slug = _slugify(header) if header else "no-header"
    type_slug = _slugify(segment_type)
    return os.path.join(event_tmp_dir, f'{type_slug}_{header_slug}_{position}.md')


def _ensure_summary_dir_exists(event_slug):
    """Ensures the directory for an event's segment summaries exists."""
    root = _get_project_root()
    event_tmp_dir = os.path.join(root, TMP_DIR, _slugify(event_slug))
    os.makedirs(event_tmp_dir, exist_ok=True)
    return event_tmp_dir


def load_segments(event_slug):
    """Loads segments for a specific event from its JSON file."""
    file_path = _get_segments_file_path(event_slug)
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content:
            return []
        return json.loads(content)


def save_segments(event_slug, segments_list):
    """Saves segments for a specific event to its JSON file."""
    file_path = _get_segments_file_path(event_slug)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(segments_list, f, indent=4)


def load_matches(event_slug):
    """Loads match data for a specific event from its JSON file."""
    file_path = _get_matches_file_path(event_slug)
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content:
            return []
        return json.loads(content)


def save_matches(event_slug, matches_list):
    """Saves match data for a specific event to its JSON file."""
    file_path = _get_matches_file_path(event_slug)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(matches_list, f, indent=4)


def get_segment_by_position(event_slug, position):
    """Retrieves a single segment for an event by its position."""
    segments = load_segments(event_slug)
    for segment in segments:
        if segment.get('position') == int(position):
            return segment
    return None


def get_match_by_id(event_slug, match_id):
    """Retrieves a single match by its match_id for a given event."""
    matches = load_matches(event_slug)
    for match in matches:
        if match.get('match_id') == match_id:
            return match
    return None


def load_summary_content(summary_file_path):
    """Loads the content of a summary file."""
    if not os.path.exists(summary_file_path):
        return ""
    with open(summary_file_path, 'r', encoding='utf-8') as f:
        return f.read()


def save_summary_content(summary_file_path, content):
    """Saves content to a summary file."""
    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
    with open(summary_file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def delete_summary_file(summary_file_path):
    """Deletes a summary file if it exists."""
    if os.path.exists(summary_file_path):
        os.remove(summary_file_path)


def load_active_wrestlers():
    """Loads active wrestlers from wrestlers.json."""
    return [w for w in load_wrestlers() if w.get('Status') == 'Active']


def load_active_tagteams():
    """Loads active tag teams from tagteams.json."""
    return [t for t in load_tagteams() if t.get('Status') == 'Active']


def _generate_participants_display_string(sides, all_tagteams_data):
    """
    Generates a human-readable display string for match participants,
    expanding tag teams within each side.
    """
    side_display_strings = []
    for side in sides:
        side_display_strings.append(_generate_side_display_string(side, all_tagteams_data))
    return " vs ".join(side_display_strings)


def validate_match_data(sides, match_results=None):
    """
    Validates match data based on specified rules.
    """
    errors = []
    warnings = []

    if not sides or len(sides) < 2:
        errors.append("A match must have at least 2 sides.")
        return errors, warnings

    for i, side in enumerate(sides):
        if not side:
            errors.append(f"Side {i+1} must have at least one participant.")

    warnings.extend(_validate_match_structure(sides))

    if match_results:
        all_tagteams_data = load_tagteams()
        all_wrestlers_in_match = _get_all_wrestlers_involved(sides)
        all_teams_in_match = _get_all_tag_teams_involved(sides, all_tagteams_data)
        warnings.extend(_validate_result_completeness(match_results, sides, all_wrestlers_in_match, all_teams_in_match, all_tagteams_data))

    return errors, warnings

def add_segment(event_slug, segment_data, summary_content, match_data=None):
    """Adds a new segment to an event. If it's a match, also adds match data."""
    segments = load_segments(event_slug)
    if any(s.get('position') == segment_data['position'] for s in segments):
        return False, "A segment with this position already exists."

    if segment_data['type'] == 'Match' and match_data is not None:
        all_wrestlers_data = load_wrestlers()
        all_tagteams_data = load_tagteams()
        processed_match_data = _prepare_match_data_for_storage(match_data, all_wrestlers_data, all_tagteams_data)
        processed_match_data = _sync_team_results_to_individuals(processed_match_data, all_tagteams_data)

        # Auto-generate header if empty
        if not segment_data.get('header'):
            match_class = processed_match_data.get('match_class', 'other')
            if match_class == 'singles':
                segment_data['header'] = 'Singles Match'
            elif match_class == 'tag':
                segment_data['header'] = 'Tag-Team Match'
            elif match_class == 'battle_royal':
                segment_data['header'] = 'Battle Royal'
            else:
                segment_data['header'] = 'Match'

        errors, warnings = validate_match_data(processed_match_data.get('sides', []), processed_match_data)
        if errors:
            raise ValueError(f"Match data validation failed: {', '.join(errors)}")
        processed_match_data['warnings'] = warnings if warnings else []

        # Generate the match_result_display string
        all_belts_data = load_belts() # Load belts here for the display string generation
        generated_display_string = generate_match_result_display_string(processed_match_data, all_tagteams_data, all_belts_data)
        
        # Use user-provided match_result_display if available, otherwise use generated
        final_match_result_display = match_data.get('match_result_display') or generated_display_string

        match_id = str(uuid.uuid4())
        # Generate participants_display here
        participants_display = _generate_participants_display_string(processed_match_data['sides'], all_tagteams_data)

        match_id = str(uuid.uuid4())
        segment_data['match_id'] = match_id
        segment_data['participants_display'] = participants_display # Use the generated string
        segment_data['sides'] = processed_match_data['sides']
        segment_data['match_result'] = processed_match_data.get('match_result', "")
        segment_data['match_result_display'] = final_match_result_display # Store the final string

        full_match_data_to_save = processed_match_data.copy()
        full_match_data_to_save['match_id'] = match_id
        full_match_data_to_save['segment_position'] = segment_data['position']
        full_match_data_to_save['match_result_display'] = final_match_result_display # Also store in full match data
        
        _add_match(event_slug, full_match_data_to_save)
    else:
        # If not a match, ensure match-specific fields are cleared
        segment_data.pop('match_id', None)
        segment_data.pop('participants_display', None)
        segment_data.pop('sides', None)
        segment_data.pop('match_result', None)
        segment_data.pop('match_result_display', None)
        segment_data.pop('match_visibility', None) # Clear this too

    # Generate summary file path (must be done after header is set)
    segment_data['summary_file'] = _get_summary_file_path(
        event_slug,
        segment_data.get('type', ''),
        segment_data.get('header', ''),
        segment_data['position']
    )

    segments.append(segment_data)
    segments.sort(key=lambda s: s['position'])
    save_segments(event_slug, segments)
    save_summary_content(segment_data['summary_file'], summary_content)
    return True, "Segment added successfully."


def _add_match(event_slug, match_data):
    """Internal function to add a new match to an event's matches file."""
    matches = load_matches(event_slug)
    matches.append(match_data)
    save_matches(event_slug, matches)


def update_segment(event_slug, original_position, updated_data, summary_content, match_data=None):
    """Updates an existing segment for an event. If it's a match, also updates match data."""
    segments = load_segments(event_slug)
    segment_index = -1
    for i, segment in enumerate(segments):
        if segment.get('position') == int(original_position):
            segment_index = i
            old_summary_file_path = segment.get('summary_file')
            old_match_id = segment.get('match_id')
            break

    if segment_index == -1:
        return False, f"Segment at position {original_position} not found."

    if updated_data['position'] != int(original_position) and \
       any(s.get('position') == updated_data['position'] for s in segments if s.get('position') != int(original_position)):
        return False, f"New position '{updated_data['position']}' conflicts with another segment."

    if updated_data['type'] == 'Match' and match_data is not None:
        all_wrestlers_data = load_wrestlers()
        all_tagteams_data = load_tagteams()
        processed_match_data = _prepare_match_data_for_storage(match_data, all_wrestlers_data, all_tagteams_data)
        processed_match_data = _sync_team_results_to_individuals(processed_match_data, all_tagteams_data)

        # Auto-generate header if empty
        if not updated_data.get('header'):
            match_class = processed_match_data.get('match_class', 'other')
            if match_class == 'singles':
                updated_data['header'] = 'Singles Match'
            elif match_class == 'tag':
                updated_data['header'] = 'Tag-Team Match'
            elif match_class == 'battle_royal':
                updated_data['header'] = 'Battle Royal'
            else:
                updated_data['header'] = 'Match'

        errors, warnings = validate_match_data(processed_match_data.get('sides', []), processed_match_data)
        if errors:
            raise ValueError(f"Match data validation failed: {', '.join(errors)}")
        processed_match_data['warnings'] = warnings if warnings else []

        # Generate the match_result_display string
        all_belts_data = load_belts() # Load belts here for the display string generation
        generated_display_string = generate_match_result_display_string(processed_match_data, all_tagteams_data, all_belts_data)

        # Use user-provided match_result_display if available, otherwise use generated
        final_match_result_display = match_data.get('match_result_display') or generated_display_string

        # Generate participants_display here
        participants_display = _generate_participants_display_string(processed_match_data['sides'], all_tagteams_data)

        updated_data['participants_display'] = participants_display # Use the generated string
        updated_data['sides'] = processed_match_data['sides']
        updated_data['match_result'] = processed_match_data.get('match_result', "")
        updated_data['match_result_display'] = final_match_result_display # Store the final string

        full_match_data_to_save = processed_match_data.copy()
        full_match_data_to_save['segment_position'] = updated_data['position']
        full_match_data_to_save['match_result_display'] = final_match_result_display # Also store in full match data

        if old_match_id:
            updated_data['match_id'] = old_match_id
            full_match_data_to_save['match_id'] = old_match_id
            _update_match(event_slug, old_match_id, full_match_data_to_save)
        else:
            match_id = str(uuid.uuid4())
            updated_data['match_id'] = match_id
            full_match_data_to_save['match_id'] = match_id
            _add_match(event_slug, full_match_data_to_save)
            
    elif old_match_id:
        _delete_match(event_slug, old_match_id)
        updated_data.pop('match_id', None)
        updated_data.pop('participants_display', None)
        updated_data.pop('sides', None)
        updated_data.pop('match_result', None)
        updated_data.pop('match_result_display', None)
        updated_data.pop('match_visibility', None) # Clear this too

    segments[segment_index] = updated_data
    new_summary_file_path = _get_summary_file_path(
        event_slug,
        updated_data.get('type', ''),
        updated_data.get('header', ''),
        updated_data['position']
    )
    segments[segment_index]['summary_file'] = new_summary_file_path

    if old_summary_file_path and old_summary_file_path != new_summary_file_path:
        delete_summary_file(old_summary_file_path)

    segments.sort(key=lambda s: s['position'])
    save_segments(event_slug, segments)
    save_summary_content(new_summary_file_path, summary_content)
    return True, "Segment updated successfully."


def _update_match(event_slug, match_id, updated_match_data):
    """Internal function to update an existing match in an event's matches file."""
    matches = load_matches(event_slug)
    found = False
    for i, match in enumerate(matches):
        if match.get('match_id') == match_id:
            matches[i] = updated_match_data
            found = True
            break
    if found:
        save_matches(event_slug, matches)
    return found


def delete_segment(event_slug, position):
    """Deletes a segment and its associated summary file and match data for an event."""
    segments = load_segments(event_slug)
    segment_to_delete = next((s for s in segments if s.get('position') == int(position)), None)

    if segment_to_delete:
        segments = [s for s in segments if s.get('position') != int(position)]
        save_segments(event_slug, segments)
        delete_summary_file(segment_to_delete.get('summary_file', ''))
        
        if segment_to_delete.get('match_id'):
            _delete_match(event_slug, segment_to_delete['match_id'])
        return True
    return False


def _delete_match(event_slug, match_id):
    """Internal function to delete a match from an event's matches file."""
    matches = load_matches(event_slug)
    matches_after_delete = [m for m in matches if m.get('match_id') != match_id]
    if len(matches_after_delete) < len(matches):
        save_matches(event_slug, matches_after_delete)
        return True
    return False


def delete_all_segments_for_event(event_name):
    """
    Deletes the segments and matches JSON files and all associated summary Markdown files.
    """
    sluggified_event_name = _slugify(event_name)
    segments_file_path = _get_segments_file_path(sluggified_event_name)
    matches_file_path = _get_matches_file_path(sluggified_event_name)

    segments = load_segments(sluggified_event_name)
    for segment in segments:
        if 'summary_file' in segment:
            delete_summary_file(segment['summary_file'])

    if os.path.exists(segments_file_path):
        os.remove(segments_file_path)

    if os.path.exists(matches_file_path):
        os.remove(matches_file_path)
        
    return True
