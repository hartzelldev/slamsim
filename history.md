# SlamSim! Development History

This document tracks the major changes, new features, and bug fixes for the 1.0 version of SlamSim!.

---

## v1.0 Beta 6 - Security, SSG, and More (2026-02-11)

This release features the static league site generator, as well as new Fan Mode preferences, a security enhancement, and bug fixes.


### New Feature: Static Site Generator (SSG)
- Introduced full league static site generation capabilities.
- Creates a full web site for uploading and sharing (great for multi-player fantasy leagues operated by a single admin).

### Security enhancement: AI settings
- Moved AI API keys out of prefs.json to .env files to reduce the risk of key exposure.
- Standardized the environment variables to eliminate the risk of key conflict.  

### Enhancement: New Fan Mode preferences
- Implemented a toggle for event card displays (similar to the toggle for Quick Results).  
- Added options to display either wrestler overall records or division records directly on the Fan Roster.  
- Along with new wrestler and tag-team statuses, there are now preferences to determine how these statuses are displayed.

### Bug Fixes
- Improved the Flask exit handling to ensure clean process termination.  
- Resolved multiple issues involving list parsing and string "split" errors.  
- Corrected a bug in the automated calculation of win/loss records.

## v1.0 Beta 5 (2025-12-05)

This release concentrates on enhancements and bug fixes.

### Enhancement: 'Concise' narrative style

- 'Concise' is now one of the options for the narrative style you can choose in the AI match writing assistant.
- This style mimics what you may see on real match summary blogs like CageSideSeats.com or BleacherReport.com.

### Prompt Review
- You can now review your prompt in the AI match writing assistant before submitting it to the AI.
- You can bypass this review by clicking 'Send directly to AI.'

### Enhancement: Weights as Numbers

- Weights are now stored as integers rather than text.
- Combined weights of tag-teams is now automatically calculated.
- You can trigger recalculation of combined weights in Preferences -> Danger Zone.
- Also in Preferences, you can choose either 'Pounds (lb.)' or 'Kilograms (kg.)' as the preferred weight unit used.

### Bug fixes
- Fixed a bug where tagteam data was being deleted when updating that team.
- Fixed a bug (hopefully) where wrestler names and signature moves were not getting passed to the AI for match generation.
- Fixed a bug in Booker Mode where Belt History was not using game_date, always using current_date instead.

## V1.0 Beta 4 (2025-11-22)

This release introduces a new AI tool for quickly creating wrestler rosters.

### New Feature: AI Roster Generator
- A tool that allows bookers to generate a creative roster of up to 30 wrestlers based on a user prompt (e.g., "10 futuristic tag teams" or "15 wrestlers from the 1980s").
- **Creative Mode:** Generates original fictional wrestlers with full creative profiles.
- **Real-World Grounding Mode:** Uses Google Search to find real wrestler data (names, heights, weights, move-sets, and birthdates) for historical or active figures.

## v1.0 Beta 3 - Tools and Data Safety (2025-11-18)

This release focuses on application structure, user experience, and—most importantly—data security. We have introduced a critical Backup and Restore feature to ensure data is protected, and simplified the top-level navigation.

### New Feature: Data Tools

- **Top-Level Navigation:** The new **'Tools'** menu item has been added to the main application navigation bar, providing easy access to vital system functions.
- **Backup & Restore:** Implemented a robust system for data safety:
    * **Backup:** Allows the booker to download a single compressed file (`.zip`) of the entire **`data`** directory, ensuring all events, rosters, and preferences are saved.
    * **Restore:** Allows the booker to upload a backup file. The system implements a critical safety protocol: it renames the current `data` folder (e.g., to `data_old...`) before extracting the backup, ensuring local data is never accidentally deleted during a restore operation.

### New Feature: Game Time
- **Custom Date Toggle:** Added a "Game Date" setting in Preferences, allowing the user to switch between Real Time and Latest Event/News Date.
- **Immersive Booking:** When using the "Latest Event/News Date" mode, all new Event and News item forms in Booker Mode now pre-fill their dates with the current game_date.
- **Date Advancement:** A new checkbox, "Update Game Date," is available on Event and News submission forms, allowing the booker to advance the game_date to the date of the new item upon publishing.
- **Accurate Reign Calculations:** All championship reign durations in Fan Mode are now calculated using the dynamic game_date instead of the system's current date, ensuring accurate reign length and immersive display (e.g., "136 days" instead of "14,381 days"). A note confirms the date used for the calculation ("As of [Date]").

### Enhancement: Champion Titles
- **Champion Title Field:** Added a new text field to the Championship editor in Booker Mode called "Champion Title Name."
- **Improved Narrative Flow:** This field allows the booker to specify the title holder's professional name (e.g., "Champion," "Tag Team Champion," "King of the Mountain").
- **Enhanced Roster Display:** The Fan Mode Roster page now uses the Champion Title Name in wrestler bios, correcting narrative phrasing from "Current World Championship" to the more immersive and grammatically correct "Current World Champion."

### Usability Improvements
- **Top-Level Preferences:** The **'Preferences'** link has been moved from the Booker Mode sub-menu to the **top-level navigation bar**, making global application settings much easier to find and access.

### Bug Fixes
- Fixed a critical bug where editing a wrestler would reset certain field values to 0 or null.
- Fixed a bug in event archive by year that was causing 404 errors.
- Fixed a bug where the default position for a division is 0, but the system required a number > 0.
- Fixed a bug in calculating tagteam records for wrestlers.
- Added missing 'awards' and 'moves' in tagteam profiles in Fan Mode.

## v1.0 Beta 2 - The AI Match Writer (2025-10-22)

This beta release introduces the first iteration of the AI Assistant, focused specifically on generating match summaries. It also includes configuration options for managing AI providers and a new quality-of-life feature for roster management.

### New Feature: AI Match Writing Assistant

- **Integration:** Added a "Generate with AI Assistant" button to the Segment Editor, visible only for segments of type "Match".
- **Context-Aware Prompts:** The backend now automatically gathers a rich "context packet" for each match, including event details, participant dossiers (alignment, styles, belts, affiliations, moves, stats), and sends this along with user-provided creative direction to the selected AI model.
- **User Control:** The AI Assistant modal provides options to guide the generation:
    - **Creative Direction:** Fields for "Feud/Storyline Summary" and "Key Story Beats & Desired Outcome".
    - **Output Style:** Dropdowns for "Level of Detail" (Brief, Detailed, Play-by-Play), "Narrative Style" (Standard, Dirt Sheet, Cinematic), and "Commentary Level" (None, Some, A lot).
    - **Entrances:** Checkbox to include ring entrance descriptions.
- **Two-Stage Workflow:** The modal presents the AI-generated text in an editable textarea, allowing the user to review, modify, regenerate, or accept the text before applying it to the main segment summary.

### New Feature: AI Configuration

- Added a new "AI Assistant Configuration" section to the Preferences page.
- Allows users to select an AI provider (Google or OpenAI).
- Allows users to specify the model name to use (e.g., `gemini-2.5-flash`, `gpt-4.0`).
- Includes fields to securely input API keys for Google and OpenAI.
- The UI dynamically updates the available models and the correct API key field based on the selected provider.

### New Feature: Roster Visibility Control

- Added a "Hide from Fan Mode Roster" checkbox to the Wrestler and Tag Team editor forms in Booker Mode.
- Wrestlers and Tag Teams marked with this flag will still appear in Booker Mode lists and dropdowns but will be excluded from the public-facing Fan Mode roster page.


## v1.0 Beta 1 (2025-10-14)

This first official beta has two new features and several bug fixes. Next, I'll start working on the AI match writer.

### New Features

- In Booker Mode, you can now filter out events, wrestlers, and tag-teams by status (Inactive, Active, etc. for wrestlers and tag-teams, Past, Future, and Canceled for events).
- In Booker Mode, before you finalize an event, warnings about inconsistancies (unequal sides, incorrectly tagged winners or losers, etc.) are displayed for your attention. You can either go back and fix them or choose to ignore them and publish anyhow.

### Bug Fixes

- Fixed a bug in the fan route that was preventing viewing of belts.
- Fixed a bug where match_result_display changes were not being saved.
- Fixed a sorting bug on the fan.roster page.
- Fixed a bug where match_class was not being updated dynamically in the segments builder.
- Fixed a bug in the segments builder where participants_display was not showing tag-teams and individual wrestlers correctly in multi-person matches.
- Fixed a couple of bad url_for strings in fan.home.

## v1.0 Alpha 4 - Fan Mode Completion & Engine Overhaul (2025-10-01)

This is the final and largest alpha release, preparing the application for its beta phase. This version introduces the complete "Fan Mode," a full-featured, read-only view of the promotion designed for an audience. It also includes a major overhaul of the core booking engine, focusing on data integrity, narrative control, and professional-grade administrative tools.

### New Features: The Complete Fan Mode

The application now has a fully realized "Fan Mode," a complete front-end experience for the wrestling promotion.

- Homepage: A customizable homepage that aggregates content, including latest news, upcoming/recent events, and a list of current champions.
- Championship Section: A dedicated champions list page that displays all belts and their current holders (with tag team members expanded). Each championship links to a detailed, chronological history page showing every title reign.
- News System: A complete news section with a main page for recent articles and yearly archives, allowing fans to follow the narrative of the promotion.

### Booking Engine & Data Integrity Overhaul

- **Match Finish System:** The segment editor has been completely overhauled. It now includes a detailed "Match Finish & Presentation" section with options for "Method of Victory" (Pinfall, Submission, etc.) and a comprehensive "Match Outcome" dropdown that properly handles draws and no contests.

- **Narrative Control:** The match_result string is now an intelligent, narrative-driven sentence that correctly reports on title changes (e.g., "...to become the new World Champion") and successful defenses.

- **Conditional Deletion:** Deletion logic has been hardened across the entire application. Entities that are part of the historical record (e.g., a wrestler with a match, a belt with a reign history, a finalized event) can no longer be deleted, protecting data integrity.

- **Architectural Improvements:** Added a Display_Position to Divisions and Belts for custom sorting and a Division_Type to Divisions to enforce correct entity assignment.

### Bug Fixes

- Critical Fix: Corrected the event finalization logic to ensure individual wrestlers' Tag_Wins and Tag_Losses are properly updated when their tag team competes in a match.
- Resolved multiple critical bugs related to file generation, template rendering, and JavaScript functionality that were causing application crashes and a

## v1.0 Alpha 3 - Introducing Fan Mode (2025-09-23)

This release marks the official debut of "Fan Mode," providing the first public-facing views of the promotion. This version establishes the architectural foundation for the fan experience and introduces the initial Roster and Events pages. Additionally, this version includes critical bug fixes to the core simulation engine, ensuring greater data integrity for wrestler and tag team records.

### New Features: The Fan Mode Experience

* **Architectural Foundation:** Implemented a new two-tiered base template system (`_booker_base.html`, `_fan_base.html`) to create a distinct look and feel for each mode while maintaining a shared core structure and navigation.
* **Fan Mode Roster Page:** Created the initial Fan Mode Roster page (`/fan/roster`), which correctly groups active wrestlers and tag teams by their assigned division. The page fully implements all user-configurable sorting options: Alphabetical, Total Wins, and Win Percentage (with a 5-match minimum qualifier).
* **Fan Mode Events Pages:** Built the main Fan Mode Events Index (`/fan/events`), which displays "Upcoming Events" and "Recent Results" sections based on user preferences.
* **Yearly Event Archives:** The Events Index now links to new yearly archive pages (e.g., `/fan/events/2025`) to provide a clean, organized view of the promotion's history.

### Bug Fixes & Stability Improvements

* **Critical Fix:** Corrected the event finalization logic to ensure individual wrestlers' `Tag_Wins` and `Tag_Losses` are properly updated when their tag team competes in a match.
* Resolved an issue where tag teams were not being sorted correctly in the Booker Mode participant builder.
* Further hardened the application by making win/loss records read-only in the UI and implementing conditional deletion logic to protect historical data.
* Improved data integrity by adding a "Division Type" (Singles/Tag-Team) to divisions, ensuring entities can only be assigned to the correct type of division.

## v1.0 Alpha 2 - Championship Update (2025-09-08)

This is a major feature release that moves SlamSim! from a collection of CLI scripts to a fully functional web dashboard. This release also introduces a complete, automated championship tracking system and numerous quality-of-life improvements. The application now functions as a true wrestling simulator, where match outcomes have a direct and permanent impact on statistics and title lineages.

### New Features & Major Changes

* **Web Dashboard:**

* Created a web UI using Python's Flask and Jinja2 modules for a complete menu-driven dashboard of features.
* All data is now created in the dashboard instead of manually needing to generate JSON files.

* **Championships (Belts) Management:**
    * Added a full CRUD (Create, Read, Update, Delete) interface for managing championships.
    * Belts can be designated for "Singles" or "Tag-Team" holders.
    * The current champion can be assigned directly from the Belts editor.

* **Championship History Tracking:**
    * The application now maintains a permanent record of all championship reigns in `data/belt_history.json`.
    * A "History" page for each belt displays a chronological list of every champion, including dates won/lost, reign length in days, and successful defenses.
    * Reign history can be manually created, edited, and deleted for full control over a title's lineage.

* **Event Finalization ("The Event Runner"):**
    * Introduced a new "Finalize Event" process for events with a "Past" status.
    * Finalizing an event is an irreversible action that locks the event card and automatically updates all official records.
    * **Automatic Record Updates:** The runner processes all match results, updating win/loss/draw records for every wrestler and tag team involved. It correctly distinguishes between singles and tag match records for individual wrestlers.
    * **Automatic Title Changes:** The runner automatically processes championship matches, updating the `Current_Holder` on the belt, writing new entries to the title's history log, and updating the `Belt` field on the wrestler/tag team's profile.
    * **Successful Defenses:** The runner automatically increments the "Defenses" count for a champion who successfully retains their title.

### UI/UX Improvements

* The "Belt" field in the Wrestler and Tag Team editors has been replaced with a dynamic dropdown menu populated by active championships.
* The Segment Editor's match builder now displays the current champion when a title is selected.
* The Events list is now sorted in reverse chronological order (most recent first).
* The Wrestlers and Tag Teams lists are now sorted alphabetically.
* The Tag Teams list has been streamlined to remove win/loss stats for a cleaner look.
* Added an "Exit" option to the main menu that leads to a goodbye page.

### Bug Fixes

* Resolved numerous critical bugs in the Segment Editor's JavaScript, restoring full functionality to the dynamic participant builder and results sections.
* Corrected data loading issues that prevented newly created entities from appearing in lists.
* Fixed various structural and logical errors in backend routes and templates.

## v1.0 Alpha 1 (2025-04-29)

This is the initial alpha release of SlamSim!, a wrestling league simulator. 

* Static web pages can be generated for wrestlers, tag-teams, divisions, events, matches, and news.
* Web pages include roster lists, events list, and upcoming events, as well as detailed wrestler and tag-team biographies.

## Future Plans

* Bring back publishing of static web pages.
* AI match and segment writer.
* AI match booking assistance.
* The ability to handle multiple leagues.

