from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from src.segments import (
    load_segments, get_segment_by_position, add_segment, update_segment, delete_segment,
    load_summary_content, _slugify, delete_all_segments_for_event,
    load_active_wrestlers, load_active_tagteams, get_match_by_id,
    validate_match_data, _get_all_wrestlers_involved, _get_all_tag_teams_involved # Added for AI context
)
from src.events import get_event_by_name, get_event_by_slug
from src.belts import load_belts
import os # Added for AI API keys
import litellm # Added for AI API calls
from src.wrestlers import load_wrestlers # Added for AI context
from src.tagteams import load_tagteams # Added for AI context
from src.prefs import load_preferences # Added for AI context
import json

segments_bp = Blueprint('segments', __name__, url_prefix='/events/<string:event_slug>/segments')

def _sort_key_ignore_the(name):
    """Returns a sort key that ignores a leading 'The '."""
    if name.lower().startswith('the '):
        return name[4:]
    return name

SEGMENT_TYPE_OPTIONS = ["Match", "Promo", "Interview", "In-ring", "Brawl", "Video Package"]
# Used for per-individual and per-team result selection (unchanged)
MATCH_RESULT_OPTIONS = ["Win", "Loss", "Draw", "No Contest"]
WINNER_METHOD_OPTIONS = ["pinfall", "submission", "KO", "referee stoppage", "disqualification", "countout"]

CONCISE_NARRATIVE_PROMPT = """
ACT AS A FAST-PACED, ACTION-FOCUSED COMMENTATOR, providing a concise, move-by-move summary for a wrestling newsletter or match report. 
CRITICAL RULES FOR THIS STYLE:
1. **Focus on Action ONLY:** Describe the moves and the immediate flow of momentum.
2. **Elaborate on General Actions:** When a general action (e.g., "several power moves") is implied or given, expand upon it by describing specific moves appropriate to the participants' 'Wrestling_Styles' and 'Signature_Moves' (provided in their dossiers). Use generic names for non-signature moves.
3. **STRICTLY EXCLUDE DIRECT MENTION OF STATS/STYLES:** Do not explicitly mention wrestler stats (height, weight), alignment, or wrestling styles in the narrative. Instead, *show* their style through the moves described.
4. **Be Brief and Punchy:** Use short, sharp sentences to drive the action forward without flowery descriptions.
"""

STANDARD_NARRATIVE_PROMPT = """
Your description of the match should be vivid and reflect the participants' unique styles.
- You MUST incorporate some of their listed Signature Moves into the narrative.
- You SHOULD describe other common wrestling moves that are appropriate for their selected Wrestling Styles (e.g., describe suplexes for a Powerhouse, quick arm-drags for a Luchador, or brawling outside the ring for a Brawler).
- Use the provided physical stats (height, weight) to inform the story of the match where appropriate (e.g., a smaller wrestler using speed against a larger one).
- **CRITICAL RULE:** You must *only* use the specific, branded move names provided in a wrestler's 'Signature Moves' list. For all other moves, you MUST use the generic, common name for that maneuver (e.g., "piledriver," "suplex," "DDT"). You are NOT allowed to invent new branded move names (like "The Matthews Driver") for any wrestler.
"""

NARRATIVE_STYLE_INSTRUCTIONS = {
    "Standard Commentary": STANDARD_NARRATIVE_PROMPT,
    "Concise": CONCISE_NARRATIVE_PROMPT,
    "Dirt Sheet / Tabloid": STANDARD_NARRATIVE_PROMPT, # Can be customized later
    "Cinematic": STANDARD_NARRATIVE_PROMPT, # Can be customized later
}

def _get_segment_form_data(form):
    """Extracts segment data from the form, including new match participant and result data."""
    position_str = form.get('position')
    position = int(position_str) if position_str and position_str.isdigit() else None
    
    segment_type = form.get('type')
    header = form.get('header', '')
    summary_text = form.get('summary_text', '')

    segment_data = {
        'position': position,
        'type': segment_type,
        'header': header,
    }

    match_details = None
    if segment_type == 'Match':
        match_sides_json = form.get('match_sides_json', '[]')
        match_sides = json.loads(match_sides_json)
        
        match_results_json = form.get('match_results_json', '{}')
        match_results_data = json.loads(match_results_json)

        # New fields
        overall_match_result = form.get('match_result', '')
        winner_method = form.get('winner_method', '')
        match_result_display = form.get('match_result_display', '') # New field

        match_details = {
            'sides': match_sides,
            'match_time': form.get('match_time', ''),
            'match_championship': form.get('match_championship', ''),
            'winning_side_index': match_results_data.get('winning_side_index', -1),
            'individual_results': match_results_data.get('individual_results', {}),
            'team_results': match_results_data.get('team_results', {}),
            'sync_teams_to_individuals': match_results_data.get('sync_teams_to_individuals', True),
            'match_result': overall_match_result,   # e.g., "Side 1 (A, B) wins" or "Draw (...)"
            'winner_method': winner_method,         # e.g., "pinfall"
            'match_result_display': match_result_display,
            'match_visibility': json.loads(form.get('match_visibility_json', '{}')), # New field
            'warnings': [],
        }
    
    return segment_data, match_details, summary_text

def _validate_segment_form_data(event_slug, segment_data, original_position=None):
    """Performs basic validation on common segment data fields, including position uniqueness."""
    errors = []
    position = segment_data['position']

    if position is None:
        errors.append("Position is required and must be a positive integer.")
    elif not isinstance(position, int) or position <= 0:
        errors.append("Position must be a positive integer.")
    
    if not segment_data['type']:
        errors.append("Type is required.")
    if segment_data['type'] not in SEGMENT_TYPE_OPTIONS:
        errors.append(f"Invalid segment type: {segment_data['type']}.")

    # Check for duplicate position only if position is valid
    if position is not None and isinstance(position, int) and position > 0:
        existing_segments = load_segments(event_slug)
        for seg in existing_segments:
            # If we are in edit mode, allow the segment to keep its own position
            if original_position is not None and seg['position'] == original_position:
                continue
            if seg['position'] == position:
                errors.append(f"Position {position} is already taken by another segment. Please choose a different position.")
                break
    
    return errors

@segments_bp.route('/create', methods=['GET', 'POST'])
def create_segment(event_slug):
    """Handles segment creation for a specific event."""
    event = get_event_by_name(event_slug)
    if not event:
        flash(f"Event '{event_slug}' not found.", 'danger')
        return redirect(url_for('events.list_events'))

    sluggified_event_name = _slugify(event_slug)
    all_wrestlers = sorted(load_active_wrestlers(), key=lambda w: w['Name'])
    all_tagteams = sorted(load_active_tagteams(), key=lambda t: _sort_key_ignore_the(t['Name']))
    all_belts = load_belts()

    match_data_for_template = {
        'sides': [], 'participants_display': '', 'match_time': '',
        'match_championship': '',
        'match_class': '', 'winning_side_index': -1, 'individual_results': {},
        'team_results': {}, 'sync_teams_to_individuals': True, 'warnings': [],
        'match_result': '', 'winner_method': '', 'match_result_display': '',
        'match_visibility': {
            'hide_from_card': False,
            'hide_summary': False,
            'hide_result': False,
        }
    }

    if request.method == 'POST':
        segment_data, match_details, summary_content = _get_segment_form_data(request.form)
        errors = _validate_segment_form_data(sluggified_event_name, segment_data, original_position=None)
        
        if segment_data['type'] == 'Match':
            if match_details:
                match_errors, match_warnings = validate_match_data(match_details['sides'], match_details)
                errors.extend(match_errors)
                match_details['warnings'] = match_warnings
                match_data_for_template.update(match_details)
            else:
                errors.append("Match data is missing for a segment of type 'Match'.")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('booker/segments/form.html', event_slug=event_slug, segment=segment_data,
                                   segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content=summary_content,
                                   all_wrestlers=all_wrestlers, all_tagteams=all_tagteams, all_belts=all_belts,
                                   match_data=match_data_for_template, match_result_options=MATCH_RESULT_OPTIONS,
                                   winner_method_options=WINNER_METHOD_OPTIONS,
                                   edit_mode=False) # Explicitly set edit_mode

        try:
            success, message = add_segment(sluggified_event_name, segment_data, summary_content, match_details)
            if success:
                flash(message, 'success')
                return redirect(url_for('events.edit_event', event_name=event_slug))
            else:
                flash(message, 'danger')
        except ValueError as e:
            flash(str(e), 'danger')

        return render_template('booker/segments/form.html', event_slug=event_slug, segment=segment_data,
                               segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content=summary_content,
                               all_wrestlers=all_wrestlers, all_tagteams=all_tagteams, all_belts=all_belts,
                               match_data=match_data_for_template, match_result_options=MATCH_RESULT_OPTIONS,
                               winner_method_options=WINNER_METHOD_OPTIONS,
                               edit_mode=False) # Explicitly set edit_mode

    return render_template('booker/segments/form.html', event_slug=event_slug, segment={},
                           segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content="",
                           all_wrestlers=all_wrestlers, all_tagteams=all_tagteams, all_belts=all_belts,
                           match_data=match_data_for_template, match_result_options=MATCH_RESULT_OPTIONS,
                           winner_method_options=WINNER_METHOD_OPTIONS,
                           edit_mode=False) # Explicitly set edit_mode

@segments_bp.route('/edit/<int:position>', methods=['GET', 'POST'])
def edit_segment(event_slug, position):
    """Handles segment editing for a specific event."""
    event = get_event_by_name(event_slug)
    if not event:
        flash(f"Event '{event_slug}' not found.", 'danger')
        return redirect(url_for('events.list_events'))

    sluggified_event_name = _slugify(event_slug)
    segment = get_segment_by_position(sluggified_event_name, position)
    if not segment:
        flash(f"Segment at position {position} not found.", 'danger')
        return redirect(url_for('events.edit_event', event_name=event_slug))

    all_wrestlers = sorted(load_active_wrestlers(), key=lambda w: w['Name'])
    all_tagteams = sorted(load_active_tagteams(), key=lambda t: _sort_key_ignore_the(t['Name']))
    all_belts = load_belts()
    summary_content = load_summary_content(segment.get('summary_file', ''))
    
    # Initialize with full default structure to prevent Undefined errors in template
    match_data_for_template = {
        'sides': [], 'participants_display': '', 'match_time': '',
        'match_championship': '',
        'match_class': '', 'winning_side_index': -1, 'individual_results': {},
        'team_results': {}, 'sync_teams_to_individuals': True, 'warnings': [],
        'match_result': '', 'winner_method': '', 'match_result_display': '',
        'match_visibility': {
            'hide_from_card': False,
            'hide_summary': False,
            'hide_result': False,
        }
    }

    if segment.get('type') == 'Match' and segment.get('match_id'):
        full_match = get_match_by_id(sluggified_event_name, segment['match_id'])
        if full_match:
            # Update the default structure with actual match data
            match_data_for_template.update(full_match)
            # Ensure all sub-keys are present, especially for match_visibility,
            # in case the loaded match data is incomplete.
            match_data_for_template.setdefault('match_visibility', {
                'hide_from_card': False,
                'hide_summary': False,
                'hide_result': False,
            })
            match_data_for_template['match_visibility'].setdefault('hide_from_card', False)
            match_data_for_template['match_visibility'].setdefault('hide_summary', False)
            match_data_for_template['match_visibility'].setdefault('hide_result', False)

    if request.method == 'POST':
        updated_segment_data, updated_match_details, new_summary_content = _get_segment_form_data(request.form)
        errors = _validate_segment_form_data(sluggified_event_name, updated_segment_data, original_position=position)

        if updated_segment_data['type'] == 'Match':
            if updated_match_details:
                match_errors, match_warnings = validate_match_data(updated_match_details['sides'], updated_match_details)
                errors.extend(match_errors)
                updated_match_details['warnings'] = match_warnings
            else:
                errors.append("Match data is missing for a segment of type 'Match'.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('booker/segments/form.html', event_slug=event_slug, segment=updated_segment_data,
                                   segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content=new_summary_content,
                                   original_position=position, all_wrestlers=all_wrestlers, all_tagteams=all_tagteams,
                                   all_belts=all_belts, match_data=updated_match_details or {},
                                   match_result_options=MATCH_RESULT_OPTIONS,
                                   winner_method_options=WINNER_METHOD_OPTIONS,
                                   edit_mode=True) # Explicitly set edit_mode
        try:
            success, message = update_segment(sluggified_event_name, position, updated_segment_data, new_summary_content, updated_match_details)
            if success:
                flash(message, 'success')
                return redirect(url_for('events.edit_event', event_name=event_slug))
            else:
                flash(message, 'danger')
        except ValueError as e:
            flash(str(e), 'danger')
        
        return render_template('booker/segments/form.html', event_slug=event_slug, segment=updated_segment_data,
                               segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content=new_summary_content,
                               original_position=position, all_wrestlers=all_wrestlers, all_tagteams=all_tagteams,
                               all_belts=all_belts, match_data=updated_match_details or {},
                               match_result_options=MATCH_RESULT_OPTIONS,
                               winner_method_options=WINNER_METHOD_OPTIONS,
                               edit_mode=True) # Explicitly set edit_mode

    return render_template('booker/segments/form.html', event_slug=event_slug, segment=segment,
                           segment_type_options=SEGMENT_TYPE_OPTIONS, summary_content=summary_content,
                           original_position=position, all_wrestlers=all_wrestlers, all_tagteams=all_tagteams,
                           all_belts=all_belts, match_data=match_data_for_template,
                           match_result_options=MATCH_RESULT_OPTIONS,
                           winner_method_options=WINNER_METHOD_OPTIONS,
                           edit_mode=True) # Explicitly set edit_mode

@segments_bp.route('/delete/<int:position>', methods=['POST'])
def delete_segment_route(event_slug, position):
    """Handles segment deletion for a specific event."""
    event = get_event_by_name(event_slug)
    if not event:
        flash(f"Event '{event_slug}' not found.", 'danger')
        return redirect(url_for('events.list_events'))

    sluggified_event_name = _slugify(event_slug)
    if delete_segment(sluggified_event_name, position):
        flash(f"Segment at position {position} deleted successfully!", 'success')
    else:
        flash(f"Failed to delete segment at position {position}.", 'danger')
    return redirect(url_for('events.edit_event', event_name=event_slug))


@segments_bp.route('/<int:position>/ai-generate', methods=['POST'])
def ai_generate(event_slug, position):
    """
    Generates AI content for a segment based on context and user input.
    This function assembles a detailed context packet and returns the full prompt.
    """
    litellm.drop_params = True # Enable dropping of unsupported parameters for AI models
    print(f"AI Generate: event_slug={event_slug}, position (from URL)={position}")
    user_input = request.get_json()
    print(f"AI Generate: user_input={user_input}")

    # Sluggify event_slug for consistent lookup
    sluggified_event_name = _slugify(event_slug)
    print(f"AI Generate: Sluggified event name: {sluggified_event_name}")

    # Load user's AI preferences
    prefs = load_preferences()
    ai_provider = prefs.get('ai_provider')
    ai_model = prefs.get('ai_model')
    google_api_key = prefs.get('google_api_key')
    openai_api_key = prefs.get('openai_api_key')

    # Set API key based on provider
    if ai_provider == 'Google':
        os.environ["GEMINI_API_KEY"] = google_api_key
    elif ai_provider == 'OpenAI':
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
    if not ai_model:
        return jsonify({'error': 'AI model not configured in preferences.'}), 400
    if ai_provider == 'Google' and not google_api_key:
        return jsonify({'error': 'Google API key not configured in preferences.'}), 400
    if ai_provider == 'OpenAI' and not openai_api_key:
        return jsonify({'error': 'OpenAI API key not configured in preferences.'}), 400


    segment = None
    if position != 0:  # Existing segment
        segment = get_segment_by_position(sluggified_event_name, position) # Use sluggified name
        if not segment:
            print(f"AI Generate: Segment not found for event_slug={sluggified_event_name}, position={position}")
            return jsonify({'error': 'Segment not found'}), 404
    else:  # New segment (position == 0)
        # Construct a temporary segment dictionary from user input for AI context
        # Ensure 'position' from user_input is used, defaulting to 0 if not provided or invalid
        segment_position_from_input = user_input.get('position')
        try:
            segment_position_from_input = int(segment_position_from_input)
        except (ValueError, TypeError):
            segment_position_from_input = 0 # Default to 0 if conversion fails

        segment = {
            'position': segment_position_from_input,
            'type': user_input.get('segment_type'),
            'header': user_input.get('segment_header', ''),
        }
        if segment['type'] == 'Match':
            segment['sides'] = json.loads(user_input.get('match_sides_json', '[]'))
            segment['match_championship'] = user_input.get('match_championship', '')
            segment['match_result'] = user_input.get('overall_match_result', '')
            segment['winner_method'] = user_input.get('winner_method', '')
            segment['match_time'] = user_input.get('match_time', '')
            segment['match_visibility'] = json.loads(user_input.get('match_visibility_json', '{}'))
        # For Promo segments, we might need to capture the speaker from user_input if it's a new segment
        if segment['type'] == 'Promo':
            segment['promo_speaker'] = user_input.get('promo_speaker', '')


    event = get_event_by_slug(sluggified_event_name) # Use sluggified name
    if not event:
        # If get_event_by_slug fails, it might be because event_slug is the original name, not the slug.
        # Try to get by name.
        event = get_event_by_name(sluggified_event_name) # Use sluggified name
        if event:
            print(f"AI Generate: Event found by name for event_slug={sluggified_event_name}")
        else:
            print(f"AI Generate: Event not found for event_slug={sluggified_event_name} (neither by slug nor by name)")
            return jsonify({'error': 'Event not found'}), 404
    
    print(f"AI Generate: Loaded Event: {event.get('Event_Name')}, Date: {event.get('Event_Date')}")

    all_wrestlers_data = load_wrestlers()
    all_tagteams_data = load_tagteams()

    # Identify participants for dossier creation
    participants = set()
    if segment['type'] == 'Match':
        wrestlers_in_match = _get_all_wrestlers_involved(segment.get('sides', []))
        teams_in_match = _get_all_tag_teams_involved(segment.get('sides', []), all_tagteams_data)
        participants.update(wrestlers_in_match)
        participants.update(teams_in_match)
    elif segment['type'] == 'Promo':
        # If a speaker is specified for a new promo, add them to participants
        if segment.get('promo_speaker'):
            participants.add(segment['promo_speaker'])
        # If it's an existing promo, try to infer participants from the header or existing data
        # For simplicity, we'll assume the 'promo_speaker' from user_input is the primary participant.
        pass # No additional participants inferred for now for Promo/other types

    # Gather dossiers
    dossiers = []
    for p_name in participants:
        wrestler = next((w for w in all_wrestlers_data if w.get('Name') == p_name), None)
        if wrestler:
            dossier = {
                "Type": "Wrestler",
                "Name": wrestler.get('Name'),
                "Nickname": wrestler.get('Nickname'),
                "Alignment": wrestler.get('Alignment'),
                "Wrestling_Styles": wrestler.get('Wrestling_Styles', '').split('|') if wrestler.get('Wrestling_Styles') else [],
                "Belt": wrestler.get('Belt'),
                "Manager": wrestler.get('Manager'),
                "Faction": wrestler.get('Faction'),
                "Height": wrestler.get('Height'),
                "Weight": wrestler.get('Weight'),
                # Handle 'Moves' which might be a pipe-separated string or already a list.
                # Uses walrus operator (Python 3.8+) for cleaner assignment and check.
                "Moves": (
                    (wrestler_moves.split('|') if isinstance(wrestler_moves, str) else wrestler_moves)
                    if isinstance(wrestler_moves, (str, list)) else []
                ) if (wrestler_moves := wrestler.get('Moves')) else [],
            }
            dossiers.append(dossier)
        else:
            tagteam = next((t for t in all_tagteams_data if t.get('Name') == p_name), None)
            if tagteam:
                members_raw = tagteam.get('Members')
                members_processed = []
                if isinstance(members_raw, str):
                    members_processed = members_raw.split('|')
                elif isinstance(members_raw, list):
                    members_processed = members_raw

                dossier = {
                    "Type": "Tag-Team",
                    "Name": tagteam.get('Name'),
                    "Members": members_processed,
                    "Alignment": tagteam.get('Alignment'),
                    "Belt": tagteam.get('Belt'),
                    "Manager": tagteam.get('Manager'),
                    "Faction": tagteam.get('Faction'),
                    # Handle 'Moves' which might be a pipe-separated string or already a list.
                    "Moves": (
                        (tagteam_moves.split('|') if isinstance(tagteam_moves, str) else tagteam_moves)
                        if isinstance(tagteam_moves, (str, list)) else []
                    ) if (tagteam_moves := tagteam.get('Moves')) else [],
                }
                dossiers.append(dossier)

    # Receive user's creative direction
    feud_summary = user_input.get('feud_summary', '')
    story_beats = user_input.get('story_beats', '')
    
    # Match-specific inputs
    detail_level = user_input.get('detail_level', 'Brief Summary')
    narrative_style = user_input.get('narrative_style', 'Standard Commentary')
    include_entrances = user_input.get('include_entrances', False)
    commentary_level = user_input.get('commentary_level', 'None')

    # Promo-specific inputs
    promo_speaker = user_input.get('promo_speaker', '')
    promo_style = user_input.get('promo_style', '')

    # Assemble the final prompt for the AI
    ai_prompt_parts = []
    ai_prompt_parts.append("You are an AI assistant for a professional wrestling booking simulator. Your task is to generate a segment summary based on the provided context and creative direction.")
    ai_prompt_parts.append("\n--- Event Context ---")
    ai_prompt_parts.append(f"Event Name: {event.get('Event_Name', 'N/A')}")
    ai_prompt_parts.append(f"Event Date: {event.get('Date', 'N/A')}")
    ai_prompt_parts.append(f"Segment Position: {segment.get('position', 'N/A')}")
    ai_prompt_parts.append(f"Segment Type: {segment.get('type', 'N/A')}")
    if segment.get('header'):
        ai_prompt_parts.append(f"Segment Header: {segment.get('header')}")

    if segment.get('type') == 'Match':
        if segment.get('match_championship'):
            ai_prompt_parts.append(f"Championship on the line: {segment.get('match_championship')}")
        if segment.get('match_result'):
            ai_prompt_parts.append(f"Overall Match Result: {segment.get('match_result')}")
        if segment.get('winner_method'):
            ai_prompt_parts.append(f"Winning Method: {segment.get('winner_method')}")
        if segment.get('match_time'):
            ai_prompt_parts.append(f"Match Time: {segment.get('match_time')}")
        if segment.get('match_visibility', {}).get('hide_from_card'):
            ai_prompt_parts.append("Match Visibility: Hidden from card")
        if segment.get('match_visibility', {}).get('hide_summary'):
            ai_prompt_parts.append("Match Visibility: Summary hidden from event summary")
        if segment.get('match_visibility', {}).get('hide_result'):
            ai_prompt_parts.append("Match Visibility: Result hidden from card")
    elif segment.get('type') == 'Promo':
        if promo_speaker:
            ai_prompt_parts.append(f"Promo Speaker: {promo_speaker}")
        if promo_style:
            ai_prompt_parts.append(f"Promo Style: {promo_style}")

    ai_prompt_parts.append("\n--- Creative Direction ---")
    ai_prompt_parts.append("IN-RING ACTION INSTRUCTIONS:")
    
    style_instructions = NARRATIVE_STYLE_INSTRUCTIONS.get(narrative_style, STANDARD_NARRATIVE_PROMPT)
    ai_prompt_parts.append(style_instructions)
    ai_prompt_parts.append("---")

    if feud_summary:
        ai_prompt_parts.append(f"Feud/Storyline Summary: {feud_summary}")
    if story_beats:
        ai_prompt_parts.append(f"Key Story Beats & Desired Outcome: {story_beats}")
    
    if segment.get('type') == 'Match':
        ai_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        ai_prompt_parts.append(f"Narrative Style: {narrative_style}")
        ai_prompt_parts.append(f"Include Ring Entrances: {'Yes' if include_entrances else 'No'}")
        ai_prompt_parts.append(f"Commentary Level: {commentary_level}")
    elif segment.get('type') == 'Promo':
        ai_prompt_parts.append(f"Promo Speaker: {promo_speaker}")
        ai_prompt_parts.append(f"Promo Style: {promo_style}")
        if detail_level != 'Brief Summary':
            ai_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        if narrative_style != 'Standard Commentary':
            ai_prompt_parts.append(f"Narrative Style: {narrative_style}")
    else:
        if detail_level != 'Brief Summary':
            ai_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        if narrative_style != 'Standard Commentary':
            ai_prompt_parts.append(f"Narrative Style: {narrative_style}")

    if dossiers:
        ai_prompt_parts.append("\n--- Participant Dossiers ---")
        for dossier in dossiers:
            ai_prompt_parts.append(json.dumps(dossier, indent=2))
        ai_prompt_parts.append("--- End Participant Dossiers ---")

    ai_prompt_parts.append("\n--- Task ---")
    task_description = f"Generate a segment summary for Segment {segment.get('position', 'N/A')} of {event.get('Event_Name', 'N/A')}. The summary should be written in the specified narrative style and detail level, incorporating the feud/storyline context, key story beats, and participant information."
    
    if segment.get('type') == 'Match':
        if include_entrances:
            task_description += " Describe the entrances."
        if commentary_level != 'None':
            task_description += f" Weave in commentary appropriate to the '{commentary_level}' level."
    elif segment.get('type') == 'Promo':
        task_description += f" Focus on the promo delivered by {promo_speaker} in a {promo_style} style."
    
    ai_prompt_parts.append(task_description)
    ai_prompt_parts.append("\n--- Generated Segment Summary ---")

    final_prompt = "\n".join(ai_prompt_parts)

    # Assemble the user-facing prompt for review
    user_review_prompt_parts = []
    user_review_prompt_parts.append("\n--- Event Context ---")
    user_review_prompt_parts.append(f"Event Name: {event.get('Event_Name', 'N/A')}")
    user_review_prompt_parts.append(f"Event Date: {event.get('Date', 'N/A')}")
    user_review_prompt_parts.append(f"Segment Position: {segment.get('position', 'N/A')}")
    user_review_prompt_parts.append(f"Segment Type: {segment.get('type', 'N/A')}")
    if segment.get('header'):
        user_review_prompt_parts.append(f"Segment Header: {segment.get('header')}")

    if segment.get('type') == 'Match':
        if segment.get('match_championship'):
            user_review_prompt_parts.append(f"Championship on the line: {segment.get('match_championship')}")
        if segment.get('match_result'):
            user_review_prompt_parts.append(f"Overall Match Result: {segment.get('match_result')}")
        if segment.get('winner_method'):
            user_review_prompt_parts.append(f"Winning Method: {segment.get('winner_method')}")
        if segment.get('match_time'):
            user_review_prompt_parts.append(f"Match Time: {segment.get('match_time')}")
        if segment.get('match_visibility', {}).get('hide_from_card'):
            user_review_prompt_parts.append("Match Visibility: Hidden from card")
        if segment.get('match_visibility', {}).get('hide_summary'):
            user_review_prompt_parts.append("Match Visibility: Summary hidden from event summary")
        if segment.get('match_visibility', {}).get('hide_result'):
            user_review_prompt_parts.append("Match Visibility: Result hidden from card")
    elif segment.get('type') == 'Promo':
        if promo_speaker:
            user_review_prompt_parts.append(f"Promo Speaker: {promo_speaker}")
        if promo_style:
            user_review_prompt_parts.append(f"Promo Style: {promo_style}")

    user_review_prompt_parts.append("\n--- Creative Direction ---")
    if feud_summary:
        user_review_prompt_parts.append(f"Feud/Storyline Summary: {feud_summary}")
    if story_beats:
        user_review_prompt_parts.append(f"Key Story Beats & Desired Outcome: {story_beats}")
    
    if segment.get('type') == 'Match':
        user_review_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        user_review_prompt_parts.append(f"Narrative Style: {narrative_style}")
        user_review_prompt_parts.append(f"Include Ring Entrances: {'Yes' if include_entrances else 'No'}")
        user_review_prompt_parts.append(f"Commentary Level: {commentary_level}")
    elif segment.get('type') == 'Promo':
        user_review_prompt_parts.append(f"Promo Speaker: {promo_speaker}")
        user_review_prompt_parts.append(f"Promo Style: {promo_style}")
        if detail_level != 'Brief Summary':
            user_review_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        if narrative_style != 'Standard Commentary':
            user_review_prompt_parts.append(f"Narrative Style: {narrative_style}")
    else:
        if detail_level != 'Brief Summary':
            user_review_prompt_parts.append(f"Desired Level of Detail: {detail_level}")
        if narrative_style != 'Standard Commentary':
            user_review_prompt_parts.append(f"Narrative Style: {narrative_style}")

    user_review_prompt = "\n".join(user_review_prompt_parts)

    print("\n--- Generated AI Prompt (Full for AI) ---")
    print(final_prompt)
    print("---------------------------\n")

    # If the request is only for the prompt, return it immediately without calling the AI API
    if user_input.get('get_prompt_only'):
        return jsonify({'prompt': user_review_prompt})

    # Prepare messages for Litellm API
    messages = [{"role": "user", "content": final_prompt}]
    ai_summary = "Error: Could not generate summary."

    try:
        response = litellm.completion(model=ai_model, messages=messages)
        ai_summary = response.choices[0].message.content
    except Exception as e:
        print(f"Error calling Litellm API: {e}")
        ai_summary = f"Error generating content: {e}. Please check your API key and model settings in preferences."

    # Return the generated summary and the full prompt for debugging/review
    return jsonify({'summary': ai_summary, 'prompt': final_prompt})
