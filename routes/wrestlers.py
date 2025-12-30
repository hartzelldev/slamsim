from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.wrestlers import load_wrestlers, get_wrestler_by_name, add_wrestler, update_wrestler, delete_wrestler
from src import divisions
from src.prefs import load_preferences # Import load_preferences
import html

wrestlers_bp = Blueprint('wrestlers', __name__, url_prefix='/wrestlers')

STATUS_OPTIONS = ['Active', 'Inactive', 'Injured', 'Suspended', 'Retired']
ALIGNMENT_OPTIONS = ['Hero', 'Babyface', 'Anti-hero', 'Tweener', 'Heel', 'Villain']
WRESTLING_STYLES_OPTIONS = ["All-Rounder", "Brawler", "Dirty", "High-Flyer", "Luchador", "Powerhouse", "Striker", "Submission Specialist", "Technical"]

def is_wrestler_deletable(wrestler):
    return all(int(wrestler.get(key, 0)) == 0 for key in ['Singles_Wins', 'Singles_Losses', 'Singles_Draws', 'Tag_Wins', 'Tag_Losses', 'Tag_Draws'])

def _get_form_data(form):
    return {
        "Name": html.escape(form['name'].strip()),
        "Status": html.escape(form.get('status', '').strip()), # Use .get() for robustness
        "Division": html.escape(form.get('division', '').strip()), # Use .get() for robustness
        "Nickname": html.escape(form.get('nickname', '').strip()), "Location": html.escape(form.get('location', '').strip()),
        "Height": html.escape(form.get('height', '').strip()), 
        "Weight": html.escape(form.get('weight', '').strip()), # Weight is now expected to be a number string
        "DOB": html.escape(form.get('dob', '').strip()), "Alignment": html.escape(form['alignment'].strip()),
        "Music": html.escape(form.get('music', '').strip()),
        "Faction": html.escape(form.get('faction', '').strip()), "Manager": html.escape(form.get('manager', '').strip()),
        "Moves": html.escape(form.get('moves', '').strip()).replace('\n', '|').replace('\r', ''),
        "Awards": html.escape(form.get('awards', '').strip()).replace('\n', '|').replace('\r', ''),
        "Real_Name": html.escape(form.get('real_name', '').strip()), "Start_Date": html.escape(form.get('start_date', '').strip()),
        "Salary": html.escape(form.get('salary', '').strip()).replace('\n', '|').replace('\r', ''),
        "Wrestling_Styles": '|'.join(html.escape(s.strip()) for s in form.getlist('wrestling_styles')),
        "Hide_From_Fan_Roster": 'hide_from_fan_roster' in form
    }

@wrestlers_bp.route('/')
def list_wrestlers():
    selected_status = request.args.get('status', 'All')
    all_wrestlers = sorted(load_wrestlers(), key=lambda w: w.get('Name', ''))

    if selected_status != 'All':
        wrestlers_list = [w for w in all_wrestlers if w.get('Status') == selected_status]
    else:
        wrestlers_list = all_wrestlers

    for wrestler in wrestlers_list:
        wrestler['DivisionName'] = divisions.get_division_name_by_id(wrestler.get('Division', ''))
        wrestler['is_deletable'] = is_wrestler_deletable(wrestler)

    prefs = load_preferences() # Load preferences
    status_options_for_filter = ['All'] + STATUS_OPTIONS
    return render_template('booker/wrestlers/list.html',
                           wrestlers=wrestlers_list,
                           status_options=status_options_for_filter,
                           selected_status=selected_status,
                           prefs=prefs) # Pass preferences to the template

@wrestlers_bp.route('/create', methods=['GET', 'POST'])
def create_wrestler():
    prefs = load_preferences() # Load preferences
    all_divisions = divisions.get_all_division_ids_and_names()
    if request.method == 'POST':
        wrestler_data = _get_form_data(request.form)
        wrestler_data['Status'] = 'Inactive' # Set default status for new wrestlers
        wrestler_data['Team'] = '' # Initialize read-only fields
        wrestler_data['Belt'] = '' # Initialize Belt as empty
        wrestler_data.update({'Singles_Wins': '0', 'Singles_Losses': '0', 'Singles_Draws': '0', 'Tag_Wins': '0', 'Tag_Losses': '0', 'Tag_Draws': '0'})
        
        if not wrestler_data.get('Name'): flash('Wrestler Name is required.', 'error')
        elif add_wrestler(wrestler_data):
            flash(f'Wrestler "{wrestler_data["Name"]}" created successfully!', 'success')
            return redirect(url_for('wrestlers.list_wrestlers'))
        else: flash(f'Wrestler with the name "{wrestler_data["Name"]}" already exists.', 'error')
        return render_template('booker/wrestlers/form.html', wrestler=wrestler_data, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, divisions=all_divisions, wrestling_styles_options=WRESTLING_STYLES_OPTIONS, edit_mode=False, prefs=prefs) # Pass preferences
    return render_template('booker/wrestlers/form.html', wrestler={}, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, divisions=all_divisions, wrestling_styles_options=WRESTLING_STYLES_OPTIONS, edit_mode=False, prefs=prefs) # Pass preferences

@wrestlers_bp.route('/edit/<string:wrestler_name>', methods=['GET', 'POST'])
def edit_wrestler(wrestler_name):
    prefs = load_preferences() # Load preferences
    wrestler = get_wrestler_by_name(wrestler_name)
    if not wrestler:
        flash(f'Wrestler "{wrestler_name}" not found.', 'error')
        return redirect(url_for('wrestlers.list_wrestlers'))
    all_divisions = divisions.get_all_division_ids_and_names()
    if request.method == 'POST':
        updated_data = _get_form_data(request.form)
        # Preserve read-only fields from the original data
        for key in ['Team', 'Belt', 'Singles_Wins', 'Singles_Losses', 'Singles_Draws', 'Tag_Wins', 'Tag_Losses', 'Tag_Draws']:
            updated_data[key] = wrestler.get(key, '0')

        if not updated_data.get('Name'): flash('Wrestler Name is required.', 'error')
        elif update_wrestler(wrestler_name, updated_data):
            flash(f'Wrestler "{updated_data["Name"]}" updated successfully!', 'success')
            return redirect(url_for('wrestlers.list_wrestlers'))
        else: flash(f'Failed to update wrestler "{wrestler_name}". New name might already exist.', 'error')
        return render_template('booker/wrestlers/form.html', wrestler=updated_data, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, divisions=all_divisions, wrestling_styles_options=WRESTLING_STYLES_OPTIONS, edit_mode=True, prefs=prefs) # Pass preferences

    wrestler_display = wrestler.copy()

    # Normalize 'Belt' field: if it's '0', treat as empty string
    if wrestler_display.get('Belt') == '0':
        wrestler_display['Belt'] = ''

    # Handle 'Moves', 'Awards', and 'Salary' which might be lists or strings
    for key in ['Moves', 'Awards', 'Salary']:
        value = wrestler_display.get(key, '')
        if isinstance(value, list):
            wrestler_display[key] = '|'.join(value).replace('|', '\n')
        else:
            wrestler_display[key] = value.replace('|', '\n')

    # Handle 'Wrestling_Styles' which might be a list or a pipe-delimited string
    wrestling_styles_data = wrestler_display.get('Wrestling_Styles')
    if isinstance(wrestling_styles_data, list):
        wrestler_display['Wrestling_Styles'] = wrestling_styles_data
    elif isinstance(wrestling_styles_data, str) and wrestling_styles_data:
        wrestler_display['Wrestling_Styles'] = wrestling_styles_data.split('|')
    else:
        wrestler_display['Wrestling_Styles'] = []
    
    # Ensure Weight is just the number for the form input, converting to string first if necessary
    wrestler_display['Weight'] = str(wrestler_display.get('Weight', '')).split(' ')[0]

    return render_template('booker/wrestlers/form.html', wrestler=wrestler_display, status_options=STATUS_OPTIONS, alignment_options=ALIGNMENT_OPTIONS, divisions=all_divisions, wrestling_styles_options=WRESTLING_STYLES_OPTIONS, edit_mode=True, prefs=prefs) # Pass preferences

@wrestlers_bp.route('/view/<string:wrestler_name>')
def view_wrestler(wrestler_name):
    prefs = load_preferences() # Load preferences
    wrestler = get_wrestler_by_name(wrestler_name)
    if not wrestler:
        flash(f'Wrestler "{wrestler_name}" not found.', 'error')
        return redirect(url_for('wrestlers.list_wrestlers'))
    wrestler['DivisionName'] = divisions.get_division_name_by_id(wrestler.get('Division', ''))
    return render_template('booker/wrestlers/view.html', wrestler=wrestler, prefs=prefs) # Pass preferences

@wrestlers_bp.route('/delete/<string:wrestler_name>', methods=['POST'])
def delete_wrestler_route(wrestler_name):
    wrestler = get_wrestler_by_name(wrestler_name)
    if wrestler and not is_wrestler_deletable(wrestler):
        flash('Cannot delete a wrestler who has a match record.', 'danger')
        return redirect(url_for('wrestlers.list_wrestlers'))
    if delete_wrestler(wrestler_name):
        flash(f'Wrestler "{wrestler_name}" deleted successfully!', 'success')
    else:
        flash(f'Failed to delete wrestler "{wrestler_name}".', 'error')
    return redirect(url_for('wrestlers.list_wrestlers'))

