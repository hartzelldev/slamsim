import datetime
from flask import Blueprint, render_template, flash, redirect, url_for
from src.prefs import load_preferences
from src.wrestlers import load_wrestlers, get_wrestler_by_name
from src.tagteams import load_tagteams, get_tagteam_by_name
from src.divisions import load_divisions
from src.events import load_events, get_event_by_name, load_event_summary_content, get_event_by_slug
import markdown
from src.segments import load_segments, get_match_by_id, _slugify # Import _slugify for event_slug
from src.belts import load_belts, get_belt_by_id, load_history_for_belt, get_belt_by_name
from src.news import load_news_posts, get_news_post_by_id
from src.date_utils import get_current_working_date # Import the new utility

fan_bp = Blueprint('fan', __name__, url_prefix='/fan')

@fan_bp.route('/champions')
def champions_list():
    """Renders the fan mode champions list page."""
    prefs = load_preferences()
    all_belts = load_belts()
    all_belts.sort(key=lambda b: b.get('Display_Position', 0))
    all_tagteams = load_tagteams()

    for belt in all_belts:
        belt['display_holder'] = belt.get('Current_Holder', '')
        if belt.get('Holder_Type') == 'Tag-Team' and belt.get('Current_Holder'):
            team_name = belt['Current_Holder']
            tagteam = next((tt for tt in all_tagteams if tt['Name'] == team_name), None)
            if tagteam:
                members = [m for m in [tagteam.get('Member1'), tagteam.get('Member2')] if m]
                if members:
                    belt['display_holder'] = f"{team_name} ({', '.join(members)})"
    
    return render_template('fan/champions_list.html', belts=all_belts, prefs=prefs)

@fan_bp.route('/belt/<string:belt_id>')
def belt_history(belt_id):
    """Renders the fan mode belt history page for a specific belt."""
    prefs = load_preferences() # Load preferences for _fan_base.html
    belt = get_belt_by_id(belt_id)
    if not belt:
        flash("Belt not found.", 'danger')
        return redirect(url_for('fan.champions_list'))

    history = load_history_for_belt(belt_id)
    history.sort(key=lambda r: datetime.datetime.strptime(r['Date_Won'], '%Y-%m-%d'), reverse=True)

    current_working_date = get_current_working_date() # Use the new utility function
    
    for reign in history:
        date_won = datetime.datetime.strptime(reign['Date_Won'], '%Y-%m-%d')
        date_lost_str = reign.get('Date_Lost')
        
        if date_lost_str:
            date_lost = datetime.datetime.strptime(date_lost_str, '%Y-%m-%d')
        else:
            # Use current_working_date for active reigns
            date_lost = datetime.datetime.combine(current_working_date, datetime.time.min)
        
        reign['Days'] = (date_lost - date_won).days

    # Add note about game date if applicable
    if prefs.get('game_date_mode') == 'latest-event-date':
        game_date_note = f"As of {current_working_date.strftime('%Y-%m-%d')}"
    else:
        game_date_note = None

    return render_template('fan/belt_history.html', belt=belt, history=history, prefs=prefs, game_date_note=game_date_note)

def _sort_key_ignore_the(name):
    """Returns a sort key that ignores a leading 'The '."""
    if name.lower().startswith('the '):
        return name[4:]
    return name

@fan_bp.route('/home')
def home():
    """Renders the fan home page."""
    prefs = load_preferences()

    # 1. Handle News
    news_posts = []
    if prefs.get('fan_mode_home_show_news') != 'Off':
        all_news = load_news_posts()
        # Sort news posts by date descending (newest first)
        all_news.sort(key=lambda p: datetime.datetime.strptime(p.get('Date', '1900-01-01'), '%Y-%m-%d'), reverse=True)
        
        num_news = int(prefs.get('fan_mode_home_number_news', 5))
        news_posts = all_news[:num_news]

        if prefs.get('fan_mode_home_show_news') == 'Show Full Posts':
            for post in news_posts:
                post['RenderedContent'] = markdown.markdown(post.get('Content', ''))

    # 2. Handle Upcoming Events
    upcoming_events = []
    if prefs.get('fan_mode_show_future_events'):
        all_events = load_events()
        for event in all_events:
            if event.get('Status') == 'Future':
                upcoming_events.append(event)
        # Sort upcoming events by date ascending
        upcoming_events.sort(key=lambda e: datetime.datetime.strptime(e.get('Date', '9999-12-31'), '%Y-%m-%d'))
        num_events = int(prefs.get('fan_mode_home_number_events', 5))
        upcoming_events = upcoming_events[:num_events]

    # 3. Handle Recent Events
    recent_events = []
    if prefs.get('fan_mode_home_show_recent_events'):
        all_events = load_events()
        for event in all_events:
            if event.get('Finalized') == True:
                recent_events.append(event)
        # Sort finalized events by date descending (newest first)
        recent_events.sort(key=lambda e: datetime.datetime.strptime(e.get('Date', '1900-01-01'), '%Y-%m-%d'), reverse=True)
        num_events = int(prefs.get('fan_mode_home_number_events', 5))
        recent_events = recent_events[:num_events]
        # Ensure event_slug is present for linking in the template
        for event in recent_events:
            event['event_slug'] = _slugify(event.get('Event_Name', ''))

    # 4. Handle Champions
    belts = []
    if prefs.get('fan_mode_home_show_champions'):
        belts = load_belts()
        belts.sort(key=lambda b: b.get('Display_Position', 0))
        all_tagteams = load_tagteams()

        for belt in belts:
            belt['display_holder'] = belt.get('Current_Holder', '')
            if belt.get('Holder_Type') == 'Tag-Team' and belt.get('Current_Holder'):
                team_name = belt['Current_Holder']
                tagteam = next((tt for tt in all_tagteams if tt['Name'] == team_name), None)
                if tagteam:
                    members = [m for m in [tagteam.get('Member1'), tagteam.get('Member2')] if m]
                    if members:
                        belt['display_holder'] = f"{team_name} ({', '.join(members)})"

    return render_template(
        'fan/home.html',
        prefs=prefs,
        news_posts=news_posts,
        upcoming_events=upcoming_events,
        recent_events=recent_events,
        belts=belts
    )

@fan_bp.route('/wrestler/<string:wrestler_name>')
def view_wrestler(wrestler_name):
    """Renders the fan view page for a specific wrestler."""
    prefs = load_preferences()
    wrestler = get_wrestler_by_name(wrestler_name)

    if not wrestler:
        flash(f"Wrestler '{wrestler_name}' not found.", 'danger')
        return redirect(url_for('fan.roster'))

    # Add champion_title_display for individual wrestler view
    if wrestler.get('Belt'):
        belt_obj = get_belt_by_name(wrestler['Belt'])
        if belt_obj:
            wrestler['current_champion_title_display'] = belt_obj.get('Champion_Title', 'Champion')
        else:
            wrestler['current_champion_title_display'] = wrestler['Belt'] # Fallback to belt name

    # Calculate total record
    singles_wins = int(wrestler.get('Singles_Wins', 0))
    singles_losses = int(wrestler.get('Singles_Losses', 0))
    singles_draws = int(wrestler.get('Singles_Draws', 0))
    tag_wins = int(wrestler.get('Tag_Wins', 0))
    tag_losses = int(wrestler.get('Tag_Losses', 0))
    tag_draws = int(wrestler.get('Tag_Draws', 0))

    total_record = {
        'wins': singles_wins + tag_wins,
        'losses': singles_losses + tag_losses,
        'draws': singles_draws + tag_draws
    }

    return render_template('fan/wrestler.html', wrestler=wrestler, prefs=prefs, total_record=total_record)

@fan_bp.route('/tagteam/<string:tagteam_name>')
def view_tagteam(tagteam_name):
    """Renders the fan view page for a specific tag team."""
    prefs = load_preferences()
    tagteam = get_tagteam_by_name(tagteam_name)

    if not tagteam:
        flash(f"Tag Team '{tagteam_name}' not found.", 'danger')
        return redirect(url_for('fan.roster'))

    # Add champion_title_display for individual tagteam view
    if tagteam.get('Belt'):
        belt_obj = get_belt_by_name(tagteam['Belt'])
        if belt_obj:
            tagteam['current_champion_title_display'] = belt_obj.get('Champion_Title', 'Champion')
        else:
            tagteam['current_champion_title_display'] = tagteam['Belt'] # Fallback to belt name

    return render_template('fan/tagteam.html', tagteam=tagteam, prefs=prefs)

@fan_bp.route('/event/<string:event_slug>')
def view_event(event_slug):
    """Renders the fan view page for a specific event."""
    prefs = load_preferences()
    event = get_event_by_slug(event_slug) # Use the new function to find by slug

    if not event:
        flash(f"Event '{event_slug}' not found.", 'danger')
        return redirect(url_for('fan.home')) # Redirect to fan home if event not found

    segments = load_segments(_slugify(event_slug))
    segments.sort(key=lambda s: s.get('position', 9999)) # Sort segments by position

    # Iterate through segments to merge match visibility data
    for segment in segments:
        if segment.get('type') == 'Match' and segment.get('match_id'):
            match_data = get_match_by_id(_slugify(event_slug), segment['match_id'])
            if match_data and 'match_visibility' in match_data:
                # Merge visibility flags into the segment dictionary
                segment['on_card'] = not match_data['match_visibility'].get('hide_from_card', False)
                segment['include_in_results'] = not match_data['match_visibility'].get('hide_result', False)
                # Note: hide_summary is handled in the finalize_event process, not directly here for display logic
            else:
                # Default to visible if match data or visibility info is missing
                segment['on_card'] = True
                segment['include_in_results'] = True
        else:
            # Non-match segments are always considered "on card" and "in results" for display purposes
            segment['on_card'] = True
            segment['include_in_results'] = True

    event_summary_content = load_event_summary_content(event.get('event_summary_file'))

    return render_template(
        'fan/event.html',
        event=event,
        segments=segments,
        prefs=prefs,
        event_summary_content=event_summary_content
    )

@fan_bp.route('/roster')
def roster():
    """Renders the fan roster page with sorted wrestlers and tag teams."""
    prefs = load_preferences()
    all_wrestlers_raw = load_wrestlers()
    all_tagteams_raw = load_tagteams()
    all_divisions = load_divisions()

    # Get display preferences for injured wrestlers and suspended roster members
    injured_wrestler_display = prefs.get('fan_mode_injured_wrestler_display', 'Show Normally')
    suspended_roster_display = prefs.get('fan_mode_suspended_roster_display', 'Show Normally')

    # Filter and modify wrestlers based on preferences
    processed_wrestlers = []
    for wrestler in all_wrestlers_raw:
        wrestler['display_status'] = '' # Initialize display status
        if wrestler.get('Hide_From_Fan_Roster', False):
            continue # Always hide if explicitly marked
        
        status = wrestler.get('Status')
        if status == 'Active':
            processed_wrestlers.append(wrestler)
        elif status == 'Injured':
            if injured_wrestler_display == 'Show Normally':
                processed_wrestlers.append(wrestler)
            elif injured_wrestler_display == 'Show with Status':
                wrestler['display_status'] = ' (Injured)'
                processed_wrestlers.append(wrestler)
            # 'Don't Show' means we skip adding it to processed_wrestlers
        elif status == 'Suspended':
            if suspended_roster_display == 'Show Normally':
                processed_wrestlers.append(wrestler)
            elif suspended_roster_display == 'Show with Status':
                wrestler['display_status'] = ' (Suspended)'
                processed_wrestlers.append(wrestler)
            # 'Don't Show' means we skip adding it to processed_wrestlers
        # For other statuses (Inactive, Retired), they are implicitly 'Don't Show' for the fan roster.
    
    # Filter and modify tag teams based on preferences
    processed_tagteams = []
    for tagteam in all_tagteams_raw:
        tagteam['display_status'] = '' # Initialize display status
        if tagteam.get('Hide_From_Fan_Roster', False):
            continue # Always hide if explicitly marked

        status = tagteam.get('Status')
        if status == 'Active':
            processed_tagteams.append(tagteam)
        elif status == 'Suspended':
            if suspended_roster_display == 'Show Normally':
                processed_tagteams.append(tagteam)
            elif suspended_roster_display == 'Show with Status':
                tagteam['display_status'] = ' (Suspended)'
                processed_tagteams.append(tagteam)
            # 'Don't Show' means we skip adding it to processed_tagteams
        # For other statuses (Inactive, Retired), they are implicitly 'Don't Show' for the fan roster.

    # Prepare a dictionary to hold roster data, grouped by division
    # Sort divisions by Display_Position for consistent display
    sorted_divisions = sorted(all_divisions, key=lambda d: d.get('Display_Position', 0))
    
    roster_by_division = {}
    for division in sorted_divisions:
        division_id = division.get('ID')
        division_name = division.get('Name')
        # Store the division type as well for template logic
        roster_by_division[division_name] = {'wrestlers': [], 'tagteams': [], 'type': division.get('Holder_Type')}

        # Add wrestlers to their division
        for wrestler in processed_wrestlers:
            if wrestler.get('Division') == division_id:
                if wrestler.get('Belt'):
                    belt_obj = get_belt_by_name(wrestler['Belt'])
                    if belt_obj:
                        wrestler['current_champion_title_display'] = belt_obj.get('Champion_Title', 'Champion')
                    else:
                        wrestler['current_champion_title_display'] = wrestler['Belt'] # Fallback to belt name
                roster_by_division[division_name]['wrestlers'].append(wrestler)
        
        # Add tag teams to their division
        for tagteam in processed_tagteams:
            if tagteam.get('Division') == division_id:
                if tagteam.get('Belt'):
                    belt_obj = get_belt_by_name(tagteam['Belt'])
                    if belt_obj:
                        tagteam['current_champion_title_display'] = belt_obj.get('Champion_Title', 'Champion')
                    else:
                        tagteam['current_champion_title_display'] = tagteam['Belt'] # Fallback to belt name
                roster_by_division[division_name]['tagteams'].append(tagteam)

    # Filter out divisions that have no active wrestlers or tagteams
    # This needs to be done after sorting and grouping
    filtered_roster_by_division = {
        div_name: data for div_name, data in roster_by_division.items()
        if data['wrestlers'] or data['tagteams']
    }

    # Sorting logic
    sort_order = prefs.get('fan_mode_roster_sort_order', 'Alphabetical')

    # Apply sorting to the filtered data
    for division_name, data in filtered_roster_by_division.items():
        # Sort wrestlers
        if data['type'] == 'Singles': # Only sort wrestlers if the division is Singles
            if sort_order == 'Alphabetical':
                data['wrestlers'].sort(key=lambda w: w.get('Name', ''))
            elif sort_order == 'Total Wins':
                data['wrestlers'].sort(key=lambda w: int(w.get('Singles_Wins', 0)), reverse=True)
            elif sort_order == 'Win Percentage':
                def get_wrestler_win_percentage_key(wrestler):
                    wins = int(wrestler.get('Singles_Wins', 0))
                    losses = int(wrestler.get('Singles_Losses', 0))
                    total_matches = wins + losses
                    # If less than 5 matches or 0-0 record, sort alphabetically at the bottom
                    if total_matches < 5 or (wins == 0 and losses == 0):
                        return (-1.0, wrestler.get('Name', '')) # -1.0 ensures it's at the bottom when sorting descending
                    return (wins / total_matches, wrestler.get('Name', '')) # Win percentage, then name for tie-breaking
                data['wrestlers'].sort(key=get_wrestler_win_percentage_key, reverse=True)

        # Sort tag teams
        if sort_order == 'Alphabetical':
            data['tagteams'].sort(key=lambda tt: _sort_key_ignore_the(tt.get('Name', '')))
        elif sort_order == 'Total Wins':
            data['tagteams'].sort(key=lambda tt: int(tt.get('Wins', 0)), reverse=True)
        elif sort_order == 'Win Percentage':
            def get_tagteam_win_percentage_key(tagteam):
                wins = int(tagteam.get('Wins', 0))
                losses = int(tagteam.get('Losses', 0))
                total_matches = wins + losses
                # If less than 5 matches or 0-0 record, sort alphabetically at the bottom
                if total_matches < 5 or (wins == 0 and losses == 0):
                    return (-1.0, _sort_key_ignore_the(tagteam.get('Name', '')))
                return (wins / total_matches, _sort_key_ignore_the(tagteam.get('Name', '')))
            data['tagteams'].sort(key=get_tagteam_win_percentage_key, reverse=True)

    return render_template('fan/roster.html', roster_data=filtered_roster_by_division, prefs=prefs)

@fan_bp.route('/events')
def events_list():
    """Renders the fan mode events index page."""
    prefs = load_preferences()
    all_events = load_events()

    upcoming_events = []
    if prefs.get('fan_mode_show_future_events'):
        for event in all_events:
            if event.get('Status') == 'Future':
                upcoming_events.append(event)
        # Sort upcoming events by date ascending
        upcoming_events.sort(key=lambda e: datetime.datetime.strptime(e.get('Date', '9999-12-31'), '%Y-%m-%d'))

    finalized_events = []
    for event in all_events:
        if event.get('Finalized') == True:
            finalized_events.append(event)
    # Sort finalized events by date descending (newest first)
    finalized_events.sort(key=lambda e: datetime.datetime.strptime(e.get('Date', '1900-01-01'), '%Y-%m-%d'), reverse=True)

    # Get unique years from finalized events for archive links
    years = sorted(list(set(datetime.datetime.strptime(e.get('Date'), '%Y-%m-%d').year for e in finalized_events if e.get('Date'))), reverse=True)

    return render_template(
        'fan/events_list.html',
        prefs=prefs,
        upcoming_events=upcoming_events,
        finalized_events=finalized_events,
        years=years,
        _slugify=_slugify # Pass _slugify to the template
    )

@fan_bp.route('/events/<int:year>')
def archive_by_year(year):
    """Renders the fan mode events archive page for a specific year."""
    prefs = load_preferences() # Load preferences here
    all_events = load_events()
    archive_events = []

    for event in all_events:
        event_date_str = event.get('Date')
        if event.get('Finalized') == True and event_date_str:
            try:
                event_year = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').year
                if event_year == year:
                    archive_events.append(event)
            except ValueError:
                # Handle cases where date might be malformed, skip such events
                continue
    
    # Sort archive events by date descending (newest first)
    archive_events.sort(key=lambda e: datetime.datetime.strptime(e.get('Date', '1900-01-01'), '%Y-%m-%d'), reverse=True)

    return render_template(
        'fan/events_archive.html',
        year=year,
        events=archive_events,
        prefs=prefs, # Pass prefs to the template
        _slugify=_slugify # Pass _slugify to the template
    )

@fan_bp.route('/news')
def news_list():
    """Renders the fan mode news index page."""
    prefs = load_preferences()
    all_news_posts = load_news_posts()

    # Get unique years from news posts for archive links
    years = sorted(list(set(datetime.datetime.strptime(p.get('Date'), '%Y-%m-%d').year for p in all_news_posts if p.get('Date'))), reverse=True)

    return render_template(
        'fan/news_list.html',
        prefs=prefs,
        news_posts=all_news_posts,
        years=years
    )

@fan_bp.route('/news/<int:year>')
def news_archive_by_year(year):
    """Renders the fan mode news archive page for a specific year."""
    prefs = load_preferences()
    all_news_posts = load_news_posts()
    archive_news_posts = []

    for post in all_news_posts:
        post_date_str = post.get('Date')
        if post_date_str:
            try:
                post_year = datetime.datetime.strptime(post_date_str, '%Y-%m-%d').year
                if post_year == year:
                    archive_news_posts.append(post)
            except ValueError:
                continue
    
    archive_news_posts.sort(key=lambda p: datetime.datetime.strptime(p.get('Date', '1900-01-01'), '%Y-%m-%d'), reverse=True)

    return render_template(
        'fan/news_archive.html',
        year=year,
        news_posts=archive_news_posts,
        prefs=prefs
    )

@fan_bp.route('/news/<string:news_id>')
def view_news(news_id):
    """Renders the fan mode view page for a specific news post."""
    prefs = load_preferences()
    news_post = get_news_post_by_id(news_id)

    if not news_post:
        flash("News post not found.", 'danger')
        return redirect(url_for('fan.news_list'))
    
    news_post['RenderedContent'] = markdown.markdown(news_post.get('Content', ''))

    return render_template(
        'fan/news_view.html',
        news_post=news_post,
        prefs=prefs
    )
