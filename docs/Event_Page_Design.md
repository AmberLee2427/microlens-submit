## Submission Dossier: Event Page Design

**Goal:** Generate a static HTML page (`events/[event_id].html`) for each submitted event, providing detailed information about the event and a comprehensive list of its associated solutions.

**Assumptions for Generation:**

-   The generating agent has access to a specific `Event` object and its parent `Submission` object.
    
-   The `Event` object _may optionally_ have an `event_data_path` attribute pointing to the raw lightcurve/astrometry data file(s) for the event.
    
-   The agent uses Tailwind CSS via CDN and the "Inter" font, with the same custom color palette as the dashboard.
    
-   The agent can generate simple image placeholders.
    
-   The agent can read and render Markdown for notes (for solution pages).
    

### 1\. Overall Page Structure & Styling

-   **HTML5 Boilerplate:** Standard `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`.
    
-   **Viewport Meta Tag:** `<meta name="viewport" content="width=device-width, initial-scale=1.0">` for responsiveness.
    
-   **Tailwind CSS & Custom Colors:** Same setup as `index.html` (copy the `<script>` block for `tailwind.config` and the `link` to Inter font).
    
-   **Background:** `bg-rtd-background` applied to `<body>`.
    
-   **Main Container:** A `div` to wrap all content.
    
    -   `max-w-7xl mx-auto p-6 lg:p-8`
        
    -   `bg-white shadow-xl rounded-lg`
        

### 2\. Header & Navigation Section

-   **Logo & Titles:**
    
    -   `img src="../assets/rges-pit_logo.png"` (note `../assets` for relative path from `events/` directory).
        
    -   `h1`: "Event Dossier: `[event.event_id]`" (`text-4xl font-bold text-rtd-secondary text-center mb-2`)
        
    -   `p`: "Team: `[submission.team_name]` | Tier: `[submission.tier]`" (`text-xl text-rtd-accent text-center mb-4`)
        
-   **Navigation Links:**
    
    -   A simple navigation bar at the top (e.g., `flex justify-center space-x-4 mb-8`).
        
    -   Link back to the Dashboard: `<a href="../index.html" class="text-rtd-accent hover:underline">← Back to Dashboard</a>`
        
    -   _(Optional: Add a "Print" button for convenience)_
        

### 3\. Event Summary/Metadata (`<section class="mb-10">`)

-   **Heading:** "Event Overview" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Basic Event Details:**
    
    -   `p`: "This page provides details for microlensing event `[event.event_id]`." (`text-rtd-text`)
        
    -   **Optional: Raw Data Link:** If `event.event_data_path` exists:
        
        -   `p`: "Raw Event Data: `<a href="[event.event_data_path]" class="text-rtd-accent hover:underline">Download Data</a>`" (`text-rtd-text`)
            
        -   _(Note: The link should be relative to the dossier's `events/` directory, so `event.event_data_path` would need to be adjusted if it's not already relative to the project root.)_
            
    -   _(Future thought: If event coordinates, field IDs, etc., are added to the `Event` model, display them here.)_
        

### 4\. Solutions for This Event (`<section class="mb-10">`)

-   **Heading:** "Solutions for Event `[event.event_id]`" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Table Structure:**
    
    -   `w-full text-left table-auto border-collapse`
        
    -   `<thead>` with `bg-rtd-primary text-rtd-secondary uppercase text-sm`
        
        -   `<th>Solution ID</th>`
            
        -   `<th>Model Type</th>`
            
        -   `<th>Status</th>`
            
        -   `<th>Log-Likelihood</th>`
            
        -   `<th>N Data Points</th>`
            
        -   `<th>Relative Probability</th>`
            
        -   `<th>Notes Snippet</th>`
            
    -   `<tbody>` with `text-rtd-text`
        
        -   **Iteration Order:** Iterate through `event.solutions.values()`, **sorted first by `is_active` (active first), then by `relative_probability` (descending, with `None` values appearing last), and finally by `solution_id` (alphabetically) as a tie-breaker.**
            
        -   Each `<tr>` with `border-b border-gray-200 hover:bg-gray-50`
            
            -   **Solution ID:** `<td>`
                
                -   `font-medium text-rtd-accent hover:underline`
                    
                -   `<a href="solutions/[solution.solution_id].html">`\[solution.solution\_id\[:8\]\]`...</a>` (Truncate ID for display, link to full ID).
                    
            -   **Model Type:** `<td>` `[solution.model_type]`
                
            -   **Status:** `<td>` `[solution.is_active ? '<span class="text-green-600">Active</span>' : '<span class="text-red-600">Inactive</span>']` (using Tailwind `text-green-600` or `text-red-600`)
                
            -   **Log-Likelihood:** `<td>` `[solution.log_likelihood:.2f]` or "N/A"
                
            -   **N Data Points:** `<td>` `[solution.n_data_points]` or "N/A"
                
            -   **Relative Probability:** `<td>` `[solution.relative_probability:.3f]` or "N/A" (If multiple active solutions, this should be the normalized value from `Submission.export`'s calculation, or 1.0 if only one active solution, or N/A if no data to calculate.)
                
            -   **Notes Snippet:** `<td>` `[solution.notes[:50]]...` (Truncate long notes, `text-gray-600 italic`)
                

### 5\. Event-Specific Data Visualizations (Evaluator-Only Placeholders)

-   **Heading:** "Event Data Visualizations (Evaluator-Only)" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Note for Participants:** `text-sm text-gray-500 italic mb-4` (e.g., "Note: These advanced plots, including comparisons to simulation truths and other teams' results, are available in the Evaluator Dossier.")
    
-   **Raw Lightcurve & Astrometry Plot:**
    
    -   `![Raw Data Plot](https://placehold.co/800x450/dfc5fa/361d49?text=Raw+Lightcurve+and+Astrometry+Data+(Evaluator+Only))`
        
    -   `Caption: Raw lightcurve and astrometry data for Event [event.event_id], with true model overlaid (Evaluator View).`
        
    -   _(This plot would utilize the `event.event_data_path` if available, and overlay the truth model in `--rtd-color-secondary`.)_
        
-   **Mass vs. Distance Scatter Plot:**
    
    -   `![Mass vs Distance Plot](https://placehold.co/600x400/dfc5fa/361d49?text=Mass+vs+Distance+Scatter+Plot+(Evaluator+Only))`
        
    -   `Caption: Derived Lens Mass vs. Lens Distance for solutions of Event [event.event_id]. Points colored by Relative Probability (Evaluator View).`
        
    -   _(This plot would use `solution.physical_parameters.M_L` and `solution.physical_parameters.D_L`. Each solution's point would be colored by its `solution.relative_probability` using a gradient from light `--rtd-accent` to darker `--rtd-accent` or a separate color scale, with higher probability being more prominent. Truth values would be in `--rtd-color-secondary`.)_
        
-   **Proper Motion N vs. E Plot:**
    
    -   `![Proper Motion Plot](https://placehold.co/600x400/dfc5fa/361d49?text=Proper+Motion+N+vs+E+Plot+(Evaluator+Only))`
        
    -   `Caption: Proper Motion North vs. East components for solutions of Event [event.event_id]. Points colored by Relative Probability (Evaluator View).`
        
    -   _(This plot would use `solution.parameters.piEN` and `solution.parameters.piEE` (or similar proper motion parameters if different names are used). Coloring by `solution.relative_probability` would be applied similarly to the Mass vs. Distance plot. Truth values would be in `--rtd-color-secondary`.)_
        

### 6\. Footer

-   **Text:** "Generated by microlens-submit v`[version]` on `[Current Date/Time]`"
    
    -   `text-sm text-gray-500 text-center pt-8 border-t border-gray-200 mt-10`
        

**Minion's Task:**

Generate an HTML file for each event in the `submission.events` dictionary, named `events/[event_id].html` within the `output_dir/events/` subdirectory. Populate the dynamic fields using data from the `Event` and `Submission` objects, paying close attention to the new sorting requirements for solutions and the detailed plot placeholders. Ensure correct relative paths for assets and links.