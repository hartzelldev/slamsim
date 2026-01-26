from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.events import load_events, get_event_by_name, add_event, update_event, delete_event, save_event_summary
from src.segments import load_segments, get_match_by_id, _get_all_wrestlers_involved, _get_all_tag_teams_involved, _slugify, delete_all_segments_for_event, load_summary_content, load_matches
from src.wrestlers import update_wrestler_record
from src.tagteams import load_tagteams, update_tagteam_record, get_tagteam_by_name
from src.belts import get_belt_by_name, process_championship_change, update_reign_in_history, load_history_for_belt
from src.prefs import load_preferences, save_preferences # Import save_preferences
from src.date_utils import get_current_working_date # Import the new utility
from datetime import datetime

events_bp = Blueprint('events', __name__, url_prefix='/events')

STATUS_OPTIONS = ['Future', 'Past', 'Cancelled']

def _get_form_data(form):
    return {
        'Event_Name': form.get('event_name'), 'Subtitle': form.get('subtitle', ''),
        'Status': form.get('status'), 'Date': form.get('date'),
        'Venue': form.get('venue', ''), 'Location': form.get('location', ''),
        'Broadcasters': form.get('broadcasters', ''),
        'Finalized': form.get('finalized', 'false').lower() == 'true'
    }

@events_bp.route('/')
def list_events():
    selected_status = request.args.get('status', 'All')
    all_events = sorted(load_events(), key=lambda e: e.get('Date', '0000-00-00'), reverse=True)

    if selected_status != 'All':
        events_list = [e for e in all_events if e.get('Status') == selected_status]
    else:
        events_list = all_events

    status_options_for_filter = ['All'] + STATUS_OPTIONS
    return render_template('booker/events/list.html',
                           events=events_list,
                           status_options=status_options_for_filter,
                           selected_status=selected_status)

@events_bp.route('/create', methods=['GET', 'POST'])
def create_event():
    prefs = load_preferences() # Load preferences here
    current_working_date = get_current_working_date().isoformat() # Get the current working date

    if request.method == 'POST':
        event_data = _get_form_data(request.form)
        if not all([event_data['Event_Name'], event_data['Status'], event_data['Date']]):
            flash('Event Name, Status, and Date are required.', 'danger')
            return render_template('booker/events/form.html', event={}, status_options=STATUS_OPTIONS, segments=[], prefs=prefs)
        try:
            datetime.strptime(event_data['Date'], '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('booker/events/form.html', event=event_data, status_options=STATUS_OPTIONS, segments=[], prefs=prefs)
        
        if add_event(event_data):
            # Update game_date if checkbox is checked and mode is 'latest-event-date'
            if prefs.get('game_date_mode') == 'latest-event-date' and request.form.get('update_game_date'):
                prefs['game_date'] = event_data['Date']
                save_preferences(prefs)
                flash(f"Game date updated to {event_data['Date']}.", 'info')

            flash(f"Event '{event_data['Event_Name']}' created successfully! You can now add segments.", 'success')
            return redirect(url_for('events.edit_event', event_name=event_data['Event_Name']))
        else:
            flash(f"Event with name '{event_data['Event_Name']}' already exists.", 'danger')
            return render_template('booker/events/form.html', event=event_data, status_options=STATUS_OPTIONS, segments=[], prefs=prefs)
    
    # For GET request, pre-fill date with current working date
    return render_template('booker/events/form.html', event={'Date': current_working_date}, status_options=STATUS_OPTIONS, segments=[], prefs=prefs)

@events_bp.route('/edit/<string:event_name>', methods=['GET', 'POST'])
def edit_event(event_name):
    prefs = load_preferences() # Load preferences here
    current_working_date = get_current_working_date().isoformat() # Get the current working date

    event = get_event_by_name(event_name)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events.list_events'))
    sluggified_name = _slugify(event_name)
    segments = sorted(load_segments(sluggified_name), key=lambda s: s.get('position', 0))

    event_warnings = []
    if event.get('Status') == 'Past':
        all_matches_data = load_matches(sluggified_name)
        for segment in segments:
            if segment.get('type') == 'Match' and segment.get('match_id'):
                match_id = segment['match_id']
                match = next((m for m in all_matches_data if m.get('match_id') == match_id), None)
                if match and match.get('warnings'):
                    for warning in match['warnings']:
                        event_warnings.append(f"Segment {segment['position']}: {warning}")

    if request.method == 'POST':
        updated_data = _get_form_data(request.form)
        updated_data['Finalized'] = event.get('Finalized', False)
        if not all([updated_data['Event_Name'], updated_data['Status'], updated_data['Date']]):
            flash('Event Name, Status, and Date are required.', 'danger')
            return render_template('booker/events/form.html', event=event, segments=segments, status_options=STATUS_OPTIONS, original_name=event_name, event_warnings=event_warnings, prefs=prefs)
        try:
            datetime.strptime(updated_data['Date'], '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('booker/events/form.html', event=updated_data, segments=segments, status_options=STATUS_OPTIONS, original_name=event_name, event_warnings=event_warnings, prefs=prefs)
        
        if update_event(event_name, updated_data):
            # Update game_date if checkbox is checked and mode is 'latest-event-date'
            if prefs.get('game_date_mode') == 'latest-event-date' and request.form.get('update_game_date'):
                prefs['game_date'] = updated_data['Date']
                save_preferences(prefs)
                flash(f"Game date updated to {updated_data['Date']}.", 'info')

            flash(f"Event '{updated_data['Event_Name']}' updated successfully!", 'success')
            return redirect(url_for('events.edit_event', event_name=updated_data['Event_Name']))
        else:
            flash(f"Failed to update event. New name might conflict.", 'danger')
            return render_template('booker/events/form.html', event=updated_data, segments=segments, status_options=STATUS_OPTIONS, original_name=event_name, event_warnings=event_warnings, prefs=prefs)
    
    # For GET request, ensure event date is set, or use current working date if new event
    if not event.get('Date'):
        event['Date'] = current_working_date

    return render_template('booker/events/form.html', event=event, segments=segments, status_options=STATUS_OPTIONS, original_name=event_name, event_warnings=event_warnings, prefs=prefs)

@events_bp.route('/view/<string:event_name>')
def view_event(event_name):
    event = get_event_by_name(event_name)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events.list_events'))
    segments = load_segments(_slugify(event_name))
    for segment in segments:
        if segment.get('summary_file'):
            segment['summary_content'] = load_summary_content(segment['summary_file'])
    segments.sort(key=lambda s: s.get('position', 0))
    return render_template('booker/events/view.html', event=event, segments=segments)

@events_bp.route('/delete/<string:event_name>', methods=['POST'])
def delete_event_route(event_name):
    event = get_event_by_name(event_name)
    if event and event.get('Finalized'):
        flash('Cannot delete an event that has been finalized.', 'danger')
        return redirect(url_for('events.list_events'))
    if delete_event(event_name):
        delete_all_segments_for_event(event_name)
        flash(f"Event '{event_name}' and its segments deleted successfully!", 'success')
    else:
        flash(f"Failed to delete event '{event_name}'.", 'danger')
    return redirect(url_for('events.list_events'))

@events_bp.route('/finalize/<string:event_name>', methods=['POST'])
def finalize_event(event_name):
    event = get_event_by_name(event_name)
    if not event or event.get('Finalized'):
        flash('Event not found or already finalized.', 'warning')
        return redirect(url_for('events.list_events'))

    sluggified_name = _slugify(event_name)
    segments = sorted(load_segments(sluggified_name), key=lambda s: s.get('position', 0))

    # Re-evaluate warnings on POST to ensure current state
    event_warnings = []
    if event.get('Status') == 'Past':
        all_matches_data = load_matches(sluggified_name)
        for segment in segments:
            if segment.get('type') == 'Match' and segment.get('match_id'):
                match_id = segment['match_id']
                match = next((m for m in all_matches_data if m.get('match_id') == match_id), None)
                if match and match.get('warnings'):
                    for warning in match['warnings']:
                        event_warnings.append(f"Segment {segment['position']}: {warning}")

    if event_warnings and not request.form.get('acknowledge_warnings'):
        flash('Please acknowledge the warnings before finalizing the event.', 'danger')
        # Redirect back to the edit page, passing the warnings again
        prefs = load_preferences() # Load prefs for template
        return render_template('booker/events/form.html', event=event, segments=segments, status_options=STATUS_OPTIONS, original_name=event_name, event_warnings=event_warnings, prefs=prefs)

    all_tagteams = load_tagteams()
    for segment in segments:
        if segment.get('type') == 'Match' and segment.get('match_id'):
            match = get_match_by_id(_slugify(event_name), segment['match_id'])
            if not match: continue
            all_teams_in_match = _get_all_tag_teams_involved(match.get('sides', []), all_tagteams)
            for team_name in all_teams_in_match:
                team_result = match['team_results'].get(team_name)
                if team_result:
                    update_tagteam_record(team_name, team_result)
                    team_data = get_tagteam_by_name(team_name)
                    if team_data and team_data.get('Members'):
                        for member_name in team_data['Members']: # team_data['Members'] is already a list
                            update_wrestler_record(member_name, 'tag', team_result)
            all_wrestlers_in_match = _get_all_wrestlers_involved(match.get('sides', []))
            match_class = match.get('match_class') # Get match_class once
            for wrestler_name in all_wrestlers_in_match:
                result = match['individual_results'].get(wrestler_name)
                if result:
                    record_match_class = None
                    if match_class == 'singles':
                        record_match_class = 'singles'
                    # For 'tag' matches, individual wrestler records are updated via the tag team processing block.
                    # For 'battle_royal' or 'other' match classes, individual records are not updated here.
                    
                    if record_match_class:
                        update_wrestler_record(wrestler_name, record_match_class, result)
            belt_name = match.get('match_championship')
            if belt_name:
                belt = get_belt_by_name(belt_name)
                winning_side_idx = match.get('winning_side_index', -1)
                if belt and belt['Status'] == 'Active' and winning_side_idx != -1:
                    winning_side = match['sides'][winning_side_idx]
                    winner_name = None
                    if belt['Holder_Type'] == 'Singles' and len(winning_side) == 1:
                        winner_name = winning_side[0]
                    elif belt['Holder_Type'] == 'Tag-Team':
                        winning_teams = _get_all_tag_teams_involved([winning_side], all_tagteams)
                        if winning_teams: winner_name = winning_teams[0]
                    if winner_name and belt.get('Current_Holder') != winner_name:
                        process_championship_change(belt, winner_name, event['Date'])
                    elif winner_name and belt.get('Current_Holder') == winner_name:
                        history = load_history_for_belt(belt['ID'])
                        for reign in history:
                            if reign.get('Champion_Name') == belt['Current_Holder'] and not reign.get('Date_Lost'):
                                reign['Defenses'] = reign.get('Defenses', 0) + 1
                                update_reign_in_history(reign['Reign_ID'], reign)
                                break
    
    # Generate consolidated event summary
    prefs = load_preferences()
    summary_parts = []
    
    for segment in segments:
        # Load match data if it's a match to check visibility settings
        match = None
        if segment.get('type') == 'Match' and segment.get('match_id'):
            match = get_match_by_id(_slugify(event_name), segment['match_id'])
            # Skip if match summary is hidden
            if match and match.get('match_visibility', {}).get('hide_summary'):
                continue # Skip this segment entirely from the summary

        summary_content = load_summary_content(segment.get('summary_file'))
        if segment.get('type') == 'Match':
            summary_parts.append(f"### {segment['header']}\n#### {segment['participants_display']}\n\n{summary_content}")
        elif prefs.get('fan_mode_show_non_match_headers'):
            summary_parts.append(f"### {segment['header']}\n\n{summary_content}")
        else:
            summary_parts.append(summary_content)
            
    final_summary = "\n\n---\n\n".join(summary_parts)
    summary_file_path = save_event_summary(_slugify(event_name), final_summary)
    event['event_summary_file'] = summary_file_path

    event['Finalized'] = True
    update_event(event_name, event)
    flash(f"Event '{event_name}' has been finalized and records updated!", 'success')
    return redirect(url_for('events.edit_event', event_name=event_name))

