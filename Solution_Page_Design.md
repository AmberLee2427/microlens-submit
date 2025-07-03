## Submission Dossier: Solution Page Design

**Goal:** Generate a static HTML page (`events/[event_id]/solutions/[solution_id].html`) for each submitted solution, providing all detailed information, plots, and metadata.

**Assumptions for Generation:**

-   The generating agent has access to a specific `Solution` object, its parent `Event` object, and the grandparent `Submission` object.
    
-   The agent uses Tailwind CSS via CDN and the "Inter" font, with the same custom color palette as the dashboard.
    
-   The agent can generate simple image placeholders.
    
-   The agent can read and render Markdown for the `solution.notes` field.
    

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
    
    -   `img src="../../assets/rges-pit_logo.png"` (note `../../assets` for relative path from `events/[event_id]/solutions/` directory).
        
    -   `h1`: "Solution Dossier: `[solution.solution_id[:8]]...`" (`text-4xl font-bold text-rtd-secondary text-center mb-2`)
        
    -   `p`: "Event: `[event.event_id]` | Team: `[submission.team_name]` | Tier: `[submission.tier]`" (`text-xl text-rtd-accent text-center mb-4`)
        
-   **Navigation Links:**
    
    -   A simple navigation bar at the top (e.g., `flex justify-center space-x-4 mb-8`).
        
    -   Link back to the Event Page: `<a href="../[event.event_id].html" class="text-rtd-accent hover:underline">← Back to Event [event.event_id]</a>` (note `../` for relative path from `solutions/` directory).
        
    -   Link back to the Dashboard: `<a href="../../index.html" class="text-rtd-accent hover:underline">← Back to Dashboard</a>`
        

### 3\. Solution Overview & Notes (`<section class="mb-10">`)

-   **Heading:** "Solution Overview & Notes" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Key Fit Parameters Table:**
    
    -   A table displaying `solution.parameters` and `solution.parameter_uncertainties`.
        
    -   `w-full text-left table-auto border-collapse`
        
    -   `<thead>` with `bg-rtd-primary text-rtd-secondary uppercase text-sm`
        
        -   `<th>Parameter</th>`
            
        -   `<th>Value</th>`
            
        -   `<th>Uncertainty</th>`
            
    -   `<tbody>` with `text-rtd-text`
        
        -   Iterate through `solution.parameters.items()`.
            
        -   For each parameter, look up its uncertainty in `solution.parameter_uncertainties`. Handle single value vs. `[lower, upper]` format.
            
        -   `<tr>` with `border-b border-gray-200 hover:bg-gray-50`
            
            -   `<td>` `[Parameter Name]` `</td>`
                
            -   `<td>` `[Parameter Value]` `</td>`
                
            -   `<td>` `[Formatted Uncertainty, e.g., ±0.1 or +0.1/-0.05]` or "N/A" `</td>`
                
-   **Higher-Order Effects Modeled:**
    
    -   `p`: "Higher-Order Effects: `[Comma-separated list of solution.higher_order_effects]`" (`text-rtd-text mt-4`)
        
-   **Participant Notes:**
    
    -   `h3`: "Participant's Detailed Notes" (`text-xl font-semibold text-rtd-secondary mt-6 mb-2`)
        
    -   A `div` where `solution.notes` (Markdown content) will be rendered into HTML.
        
        -   `bg-gray-50 p-4 rounded-lg shadow-inner text-rtd-text prose max-w-none` (Tailwind `prose` for basic markdown styling).
            

### 4\. Lightcurve & Lens Plane Visuals (`<section class="mb-10">`)

-   **Heading:** "Lightcurve & Lens Plane Visuals" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Plot Containers:** `grid grid-cols-1 md:grid-cols-2 gap-6`
    
    -   **Lightcurve Plot:**
        
        -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md"`
            
        -   `img src="[solution.lightcurve_plot_path]" alt="Lightcurve Plot" class="w-full h-auto rounded-md mb-2"` (Note: `solution.lightcurve_plot_path` would need to be relative to the `solutions/` directory, e.g., `[solution_id]/lightcurve.png`).
            
        -   `p class="text-sm text-rtd-secondary"`: `Caption: Lightcurve fit for Solution [solution.solution_id[:8]]...`
            
    -   **Lens Plane Plot:**
        
        -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md"`
            
        -   `img src="[solution.lens_plane_plot_path]" alt="Lens Plane Plot" class="w-full h-auto rounded-md mb-2"` (Note: `solution.lens_plane_plot_path` would need to be relative to the `solutions/` directory, e.g., `[solution_id]/lens_plane.png`).
            
        -   `p class="text-sm text-rtd-secondary"`: `Caption: Lens plane geometry for Solution [solution.solution_id[:8]]...`
            
-   **Optional: Posterior Samples Link:**
    
    -   If `solution.posterior_path` exists:
        
        -   `p class="text-rtd-text mt-4 text-center"`: "Posterior Samples: `<a href="[solution.posterior_path]" class="text-rtd-accent hover:underline">Download Posterior Data</a>`" (Note: `solution.posterior_path` would need to be relative to the `solutions/` directory, e.g., `[solution_id]/posterior.h5`).
            

### 5\. Fit Statistics & Data Utilization (`<section class="mb-10">`)

-   **Heading:** "Fit Statistics & Data Utilization" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Stats Grid:** `grid grid-cols-1 md:grid-cols-2 gap-6`
    
    -   **Log-Likelihood:** `div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center"`
        
        -   `p class="text-sm font-medium text-rtd-secondary"`: "Log-Likelihood"
            
        -   `p class="text-4xl font-bold text-rtd-accent mt-2"`: `[solution.log_likelihood:.2f]` or "N/A"
            
    -   **N Data Points Used:** `div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center"`
        
        -   `p class="text-sm font-medium text-rtd-secondary"`: "N Data Points Used"
            
        -   `p class="text-4xl font-bold text-rtd-accent mt-2"`: `[solution.n_data_points]` or "N/A"
            
-   **Data Utilization Ratio (Infographic Placeholder):**
    
    -   `h3`: "Data Utilization Ratio" (`text-xl font-semibold text-rtd-secondary mt-6 mb-2`)
        
    -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md"`
        
    -   `img src="https://placehold.co/600x100/dfc5fa/361d49?text=Data+Utilization+Infographic" alt="Data Utilization" class="w-full h-auto rounded-md mb-2"`
        
    -   `p class="text-sm text-rtd-secondary"`: `Caption: Percentage of total event data points utilized in this solution's fit.`
        

### 6\. Compute Performance (`<section class="mb-10">`)

-   **Heading:** "Compute Performance" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Compute Info Table:**
    
    -   `w-full text-left table-auto border-collapse`
        
    -   `<thead>` with `bg-rtd-primary text-rtd-secondary uppercase text-sm`
        
        -   `<th>Metric</th>`
            
        -   `<th>Your Solution</th>`
            
        -   `<th>Same-Team Average</th>`
            
        -   `<th>All-Submission Average</th>`
            
    -   `<tbody>` with `text-rtd-text`
        
        -   `<tr>` for CPU Hours: `<td>CPU Hours</td>` `<td>[solution.compute_info.cpu_hours:.2f]</td>` `<td>N/A for Participants</td>` `<td>N/A for Participants</td>`
            
        -   `<tr>` for Wall Time Hours: `<td>Wall Time (Hrs)</td>` `<td>[solution.compute_info.wall_time_hours:.2f]</td>` `<td>N/A for Participants</td>` `<td>N/A for Participants</td>`
            
        -   _(Optional: Add rows for `dependencies` and `git_info` if desired, formatted for display.)_
            
-   **Note for Participants:** `text-sm text-gray-500 italic mt-4` (e.g., "Note: Comparison to other teams' compute times is available in the Evaluator Dossier.")
    

### 7\. Parameter Accuracy vs. Truths (Evaluator-Only) (`<section class="mb-10">`)

-   **Heading:** "Parameter Accuracy vs. Truths (Evaluator-Only)" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Note for Participants:** `p class="text-sm text-gray-500 italic mb-4"`: "You haven't fucked up. This just isn't for you. Detailed comparisons of your fitted parameters against simulation truths are available in the Evaluator Dossier."
    
-   **Comparison Table Placeholder:**
    
    -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md"`
        
    -   `img src="https://placehold.co/800x300/dfc5fa/361d49?text=Parameter+Comparison+Table+(Evaluator+Only)" alt="Parameter Comparison Table" class="w-full h-auto rounded-md mb-2"`
        
    -   `p class="text-sm text-rtd-secondary"`: `Caption: A table comparing fitted parameters to true values (Evaluator View).`
        
-   **Parameter Difference Distributions Plot Placeholder:**
    
    -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6"`
        
    -   `img src="https://placehold.co/800x400/dfc5fa/361d49?text=Parameter+Difference+Distributions+(Evaluator+Only)" alt="Parameter Difference Distributions" class="w-full h-auto rounded-md mb-2"`
        
    -   `p class="text-sm text-rtd-secondary"`: `Caption: Distributions of (True - Fit) for key parameters across all challenge submissions (Evaluator View).`
        

### 8\. Physical Parameter Context (Evaluator-Only) (`<section class="mb-10">`)

-   **Heading:** "Physical Parameter Context (Evaluator-Only)" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Note for Participants:** `p class="text-sm text-gray-500 italic mb-4"`: "You haven't fucked up. This just isn't for you. Contextual plots of derived physical parameters against population models are available in the Evaluator Dossier."
    
-   **Derived Physical Parameters Table:**
    
    -   `w-full text-left table-auto border-collapse`
        
    -   `<thead>` with `bg-rtd-primary text-rtd-secondary uppercase text-sm`
        
        -   `<th>Parameter</th>`
            
        -   `<th>Value</th>`
            
    -   `<tbody>` with `text-rtd-text`
        
        -   Iterate through `solution.physical_parameters.items()`.
            
        -   `<tr>` with `border-b border-gray-200 hover:bg-gray-50`
            
            -   `<td>` `[Parameter Name]` `</td>`
                
            -   `<td>` `[Parameter Value]` `</td>`
                
-   **Physical Parameter Distribution Plot Placeholder:**
    
    -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6"`
        
    -   `img src="https://placehold.co/600x400/dfc5fa/361d49?text=Physical+Parameter+Distribution+(Evaluator+Only)" alt="Physical Parameter Distribution" class="w-full h-auto rounded-md mb-2"`
        
    -   `p class="text-sm text-rtd-secondary"`: `Caption: Your solution's derived physical parameters plotted against a simulated test set (Evaluator View).`
        

### 9\. Source Properties & CMD (Evaluator-Only) (`<section class="mb-10">`)

-   **Heading:** "Source Properties & CMD (Evaluator-Only)" (`text-2xl font-semibold text-rtd-secondary mb-4`)
    
-   **Note for Participants:** `p class="text-sm text-gray-500 italic mb-4"`: "You haven't fucked up. This just isn't for you. Source color and magnitude diagrams are available in the Evaluator Dossier."
    
-   **Derived Source Color Details:**
    
    -   `p class="text-rtd-text"`: `[Filter 1] - [Filter 2]` Color: `[Value]`
        
    -   `p class="text-rtd-text"`: `[Filter 1]` Magnitude: `[Value]`
        
-   **Color-Magnitude Diagram Plot Placeholder:**
    
    -   `div class="text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6"`
        
    -   `img src="https://placehold.co/600x400/dfc5fa/361d49?text=Color-Magnitude+Diagram+with+Source+(Evaluator+Only)" alt="Color-Magnitude Diagram" class="w-full h-auto rounded-md mb-2"`
        
    -   `p class="text-sm text-rtd-secondary"`: `Caption: Color-Magnitude Diagram for the event's field with source marked (Evaluator View).`
        

### 10\. Footer

-   **Text:** "Generated by microlens-submit v`[version]` on `[Current Date/Time]`"
    
    -   `text-sm text-gray-500 text-center pt-8 border-t border-gray-200 mt-10`
        

**Minion's Task:**

Generate an HTML file for each solution, named `events/[event_id]/solutions/[solution_id].html` within the `output_dir/events/[event_id]/solutions/` subdirectory. Populate the dynamic fields using data from the `Solution`, `Event`, and `Submission` objects, paying close attention to formatting, relative paths for assets/links, and the explicit "Evaluator-Only" notes.