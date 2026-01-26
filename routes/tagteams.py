import html
from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.tagteams import (
    load_tagteams, get_tagteam_by_name, add_tagteam, update_tagteam, 
    delete_tagteam, get_wrestler_names, get_active_members_status,
    _calculate_tagteam_weight
)
from src.wrestlers import update_wrestler_team_affiliation
from src import divisions
from src.prefs import load_preferences # Import load_preferences
from werkzeug.utils import escape

tagteams_bp = Blueprint('tagteams', __name__, url_prefix='/tagteams')

def _sort_key_ignore_the(name):
    """Returns a sort key that ignores a leading 'The '."""
    if name.lower().startswith('the '):
        return name[4:]
    return name

STATUS_OPTIONS = ['Active', 'Inactive', 'Suspended', 'Retired']
ALIGNMENT_OPTIONS = ['Babyface', 'Tweener', 'Heel']

def is_tagteam_deletable(team):
    """Check if a tag team has a non-zero record."""
    return all(int(team.get(key, 0)) == 0 for key in ['Wins', 'Losses', 'Draws'])

def _get_form_data(form):
    """Extracts and processes tag-team data from the form."""
    member_names = [form.get('Member1'), form.get('Member2'), form.get('Member3')]
    members_string = '|'.join(filter(None, member_names))

    member_status_active = get_active_members_status(filter(None, member_names))
    tagteam_status = form.get('Status')
    if tagteam_status == 'Active' and not member_status_active:
        flash("Cannot set tag-team status to 'Active' because one or more members are inactive.", 'warning')
        tagteam_status = 'Inactive'

    # Calculate combined weight based on selected members
    calculated_weight = _calculate_tagteam_weight(filter(None, member_names))

    return {
        "Name": escape(form.get('Name', '')).strip(),
        "Wins": escape(form.get('Wins', '0')),
        "Losses": escape(form.get('Losses', '0')),
        "Draws": escape(form.get('Draws', '0')),
        "Status": tagteam_status,
        "Division": escape(form.get('Division', '')).strip(),
        "Location": escape(form.get('Location', '')).strip(),
        "Weight": calculated_weight, # Use calculated weight
        "Alignment": form.get('Alignment', ''),
        "Music": escape(form.get('Music', '')).strip(),
        "Members": members_string,
        "Faction": escape(form.get('Faction', '')).strip(),
        "Manager": escape(form.get('Manager', '')).strip(),
        "Moves": html.escape(form.get('Moves', '').strip()).replace('\n', '|').replace('\r', ''),
        "Awards": html.escape(form.get('Awards', '').strip()).replace('\n', '|').replace('\r', ''),
        "Hide_From_Fan_Roster": 'hide_from_fan_roster' in form
    }

@tagteams_bp.route('/')
def list_tagteams():
    """Displays a list of all tag-teams, sorted alphabetically, with deletable check."""
    prefs = load_preferences() # Load preferences
    selected_status = request.args.get('status', 'All')
    all_tagteams = sorted(load_tagteams(), key=lambda t: _sort_key_ignore_the(t.get('Name', '')))

    if selected_status != 'All':
        tagteams_list = [t for t in all_tagteams if t.get('Status') == selected_status]
    else:
        tagteams_list = all_tagteams

    for team in tagteams_list:
        team['DivisionName'] = divisions.get_division_name_by_id(team.get('Division', ''))
        team['is_deletable'] = is_tagteam_deletable(team)

    status_options_for_filter = ['All'] + STATUS_OPTIONS
    return render_template('booker/tagteams/list.html',
                           tagteams=tagteams_list,
                           status_options=status_options_for_filter,
                           selected_status=selected_status,
                           prefs=prefs) # Pass preferences to the template

@tagteams_bp.route('/create', methods=['GET', 'POST'])
def create_tagteam():
    """Handles creation of a new tag-team."""
    prefs = load_preferences() # Load preferences
    wrestler_names = get_wrestler_names()
    all_divisions = divisions.get_all_division_ids_and_names()
    if request.method == 'POST':
        tagteam_data = _get_form_data(request.form)
        tagteam_data['Belt'] = '' # New teams don't have belts
        if not tagteam_data['Name']:
            flash('Tag-team Name is required.', 'danger')
        elif not request.form.get('Member1') or not request.form.get('Member2'):
            flash('At least two members are required.', 'danger')
        elif get_tagteam_by_name(tagteam_data['Name']):
            flash(f"A tag-team with the name '{tagteam_data['Name']}' already exists.", 'danger')
        else:
            add_tagteam(tagteam_data)
            # Sync wrestler team fields
            for member_name in tagteam_data.get('Members', '').split('|'):
                if member_name: update_wrestler_team_affiliation(member_name, tagteam_data['Name'])
            flash(f"Tag-team '{tagteam_data['Name']}' created successfully!", 'success')
            return redirect(url_for('tagteams.list_tagteams'))
        return render_template('booker/tagteams/form.html', tagteam=tagteam_data, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, wrestler_names=wrestler_names, divisions=all_divisions, edit_mode=False, prefs=prefs) # Pass preferences
    return render_template('booker/tagteams/form.html', tagteam={}, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, wrestler_names=wrestler_names, divisions=all_divisions, edit_mode=False, prefs=prefs) # Pass preferences

@tagteams_bp.route('/edit/<string:tagteam_name>', methods=['GET', 'POST'])
def edit_tagteam(tagteam_name):
    """Handles editing of an existing tag-team."""
    prefs = load_preferences() # Load preferences
    tagteam = get_tagteam_by_name(tagteam_name)
    if not tagteam:
        flash('Tag-team not found!', 'danger')
        return redirect(url_for('tagteams.list_tagteams'))
    
    wrestler_names = get_wrestler_names()
    all_divisions = divisions.get_all_division_ids_and_names()
    old_members = set(tagteam.get('Members', [])) if tagteam else set()

    if request.method == 'POST':
        # Get processed form data using the helper function
        form_data_processed = _get_form_data(request.form)

        # Start with a copy of the existing tagteam data to preserve non-editable fields
        # (like Wins, Losses, Draws, Belt which are not part of the edit form)
        updated_data = tagteam.copy() 

        # Update fields from the processed form data
        updated_data["Name"] = form_data_processed["Name"]
        updated_data["Status"] = form_data_processed["Status"] # _get_form_data handles status validation and flashing
        updated_data["Division"] = form_data_processed["Division"]
        updated_data["Location"] = form_data_processed["Location"]
        updated_data["Weight"] = form_data_processed["Weight"]
        updated_data["Alignment"] = form_data_processed["Alignment"]
        updated_data["Music"] = form_data_processed["Music"]
        updated_data["Members"] = form_data_processed["Members"]
        updated_data["Faction"] = form_data_processed["Faction"]
        updated_data["Manager"] = form_data_processed["Manager"]
        updated_data["Moves"] = form_data_processed["Moves"]
        updated_data["Awards"] = form_data_processed["Awards"]
        updated_data["Hide_From_Fan_Roster"] = form_data_processed["Hide_From_Fan_Roster"]

        if not updated_data['Name']:
            flash('Tag-team Name is required.', 'danger')
        elif not request.form.get('Member1') or not request.form.get('Member2'):
            flash('At least two members are required.', 'danger')
        elif updated_data['Name'] != tagteam_name and get_tagteam_by_name(updated_data['Name']):
            flash(f"A tag-team with the name '{updated_data['Name']}' already exists.", 'danger')
        else:
            update_tagteam(tagteam_name, updated_data)
            
            # Sync wrestler team fields
            new_members = set(updated_data.get('Members', '').split('|'))
            removed_members = old_members - new_members
            added_members = new_members - old_members
            name_changed = updated_data['Name'] != tagteam_name

            for member in removed_members:
                if member: update_wrestler_team_affiliation(member, '') # Clear team
            for member in added_members:
                if member: update_wrestler_team_affiliation(member, updated_data['Name'])
            if name_changed: # If team name changed, update all current members
                for member in new_members:
                    if member: update_wrestler_team_affiliation(member, updated_data['Name'])

            flash(f"Tag-team '{updated_data['Name']}' updated successfully!", 'success')
            return redirect(url_for('tagteams.list_tagteams'))
        
        # If validation fails, re-render the form with the updated_data (which includes form submissions)
        # and also ensure member fields are split back out for the form.
        members_list_for_form = updated_data.get('Members', '').split('|')
        updated_data['Member1'] = members_list_for_form[0] if len(members_list_for_form) > 0 else ''
        updated_data['Member2'] = members_list_for_form[1] if len(members_list_for_form) > 1 else ''
        updated_data['Member3'] = members_list_for_form[2] if len(members_list_for_form) > 2 else ''
        return render_template('booker/tagteams/form.html', tagteam=updated_data, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, wrestler_names=wrestler_names, divisions=all_divisions, edit_mode=True, prefs=prefs) # Pass preferences
    
    # Pre-fill form for GET request
    # Ensure all fields are present for rendering, defaulting to empty string or appropriate value if missing.
    # Convert stored '|' to '\n' for multi-line text areas for 'Moves' and 'Awards'.
    tagteam['Name'] = tagteam.get('Name', '')
    tagteam['Wins'] = tagteam.get('Wins', '0')
    tagteam['Losses'] = tagteam.get('Losses', '0')
    tagteam['Draws'] = tagteam.get('Draws', '0')
    tagteam['Status'] = tagteam.get('Status', '')
    tagteam['Division'] = tagteam.get('Division', '')
    tagteam['Location'] = tagteam.get('Location', '')
    tagteam['Weight'] = tagteam.get('Weight', '')
    tagteam['Alignment'] = tagteam.get('Alignment', '')
    tagteam['Music'] = tagteam.get('Music', '')
    tagteam['Faction'] = tagteam.get('Faction', '')
    tagteam['Manager'] = tagteam.get('Manager', '')
    tagteam['Moves'] = '\n'.join(tagteam.get('Moves', []))
    tagteam['Awards'] = '\n'.join(tagteam.get('Awards', []))
    tagteam['Hide_From_Fan_Roster'] = tagteam.get('Hide_From_Fan_Roster', False)
    tagteam['Belt'] = tagteam.get('Belt', '') # Ensure 'Belt' is present, though not directly editable here

    members_list = tagteam.get('Members', [])
    tagteam['Member1'] = members_list[0] if len(members_list) > 0 else ''
    tagteam['Member2'] = members_list[1] if len(members_list) > 1 else ''
    tagteam['Member3'] = members_list[2] if len(members_list) > 2 else ''
    return render_template('booker/tagteams/form.html', tagteam=tagteam, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, wrestler_names=wrestler_names, divisions=all_divisions, edit_mode=True, prefs=prefs) # Pass preferences

@tagteams_bp.route('/view/<string:tagteam_name>')
def view_tagteam(tagteam_name):
    """Displays details of a single tag-team."""
    prefs = load_preferences() # Load preferences
    tagteam = get_tagteam_by_name(tagteam_name)
    if not tagteam:
        flash('Tag-team not found!', 'danger')
        return redirect(url_for('tagteams.list_tagteams'))
    tagteam['DivisionName'] = divisions.get_division_name_by_id(tagteam.get('Division', ''))
    return render_template('booker/tagteams/view.html', tagteam=tagteam, prefs=prefs) # Pass preferences

@tagteams_bp.route('/delete/<string:tagteam_name>', methods=['POST'])
def delete_tagteam_route(tagteam_name):
    """Handles deletion of a tag-team."""
    team = get_tagteam_by_name(tagteam_name)
    if team and not is_tagteam_deletable(team):
        flash('Cannot delete a tag team that has a match record.', 'danger')
        return redirect(url_for('tagteams.list_tagteams'))

    # Clear team affiliation from members before deleting
    if team and team.get('Members'):
        for member_name in team['Members']: # Members is already a list
            if member_name: update_wrestler_team_affiliation(member_name, '')
            
    delete_tagteam(tagteam_name)
    flash(f"Tag-team '{tagteam_name}' deleted successfully!", 'success')
    return redirect(url_for('tagteams.list_tagteams'))

