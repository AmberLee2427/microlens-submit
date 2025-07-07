## Submission Dossier: Dashboard Design

**Goal:** Generate a static HTML dashboard (`index.html`) that provides an overview of the participant's submission, key statistics, and links to detailed event pages. This page should be visually appealing, responsive, and use the specified color palette.

**Assumptions for Generation:**

-   The generating agent has access to a `Submission` object (Python `microlens_submit.Submission` instance) which contains all project data.

-   The agent can generate simple image placeholders for plots (e.g., using `https://placehold.co/`).

-   The agent can read and render basic Markdown for notes (though not directly on the dashboard, it's a general capability).

-   The agent uses Tailwind CSS via CDN and the "Inter" font.


### 1\. Overall Page Structure & Styling

-   **HTML5 Boilerplate:** Standard `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`.

-   **Viewport Meta Tag:** `<meta name="viewport" content="width=device-width, initial-scale=1.0">` for responsiveness.

-   **Tailwind CSS:** Load via CDN in `<head>`: `<script src="https://cdn.tailwindcss.com"></script>`

-   **Custom Colors (Tailwind Configuration):** Define the following custom colors within the `<script>` tag that loads Tailwind, so they can be used as Tailwind classes (e.g., `text-rtd-secondary`, `bg-rtd-accent`):

    ```php-template
    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              'rtd-primary': '#dfc5fa',
              'rtd-secondary': '#361d49',
              'rtd-accent': '#a859e4',
              'rtd-background': '#faf7fd',
              'rtd-text': '#000',
            },
            fontFamily: {
              inter: ['Inter', 'sans-serif'],
            },
          },
        },
      };
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    ```

-   **Font:** Apply `font-inter` to the `<body>` tag.

-   **Background:** `bg-rtd-background` applied to `<body>`.

-   **Main Container:** A `div` to wrap all content.

    -   `max-w-7xl mx-auto p-6 lg:p-8` (for centering and padding).

    -   `bg-white shadow-xl rounded-lg` (for a card-like appearance).


### 2\. Header Section

-   **Logo:** An image at the top, centered.

    -   `src="./assets/rges-pit_logo.png"` (placeholder, assume `assets` directory in dossier output).

    -   `alt="RGES-PIT Logo"`

    -   `w-48 mx-auto mb-6`

-   **Main Title:** "Microlensing Data Challenge Submission Dossier"

    -   `text-4xl font-bold text-rtd-secondary text-center mb-2`

-   **Subtitle:** "Team: `[submission.team_name]` | Tier: `[submission.tier]`"

    -   `text-xl text-rtd-accent text-center mb-8`


### 3\. Submission Summary Section (`<section class="mb-10">`)

-   **Heading:** "Submission Overview"

    -   `text-2xl font-semibold text-rtd-secondary mb-4`

-   **Stats Grid:** A responsive grid for key numbers.

    -   `grid grid-cols-1 md:grid-cols-3 gap-6`

    -   Each stat in a `div` with: `bg-rtd-primary p-6 rounded-lg shadow-md text-center`

        -   **Total Events Submitted:**

            -   `text-sm font-medium text-rtd-secondary`

            -   `text-4xl font-bold text-rtd-accent mt-2` (Value: `len(submission.events)`)

        -   **Total Active Solutions:**

            -   `text-sm font-medium text-rtd-secondary`

            -   `text-4xl font-bold text-rtd-accent mt-2` (Value: `sum(len(event.get_active_solutions()) for event in submission.events.values())`)

        -   **Hardware Information:**

            -   `text-sm font-medium text-rtd-secondary`

            -   `text-lg text-rtd-text mt-2` (Value: `submission.hardware_info` formatted as a readable string, e.g., "CPU: Intel Xeon, RAM: 32GB")


### 4\. Overall Progress & Compute Time (`<section class="mb-10">`)

-   **Heading:** "Challenge Progress & Compute Summary"

    -   `text-2xl font-semibold text-rtd-secondary mb-4`

-   **Progress Bar (Hardcoded Total):**

    -   **Total Challenge Events:** `const TOTAL_CHALLENGE_EVENTS = 293;` (Hardcoded value)

    -   **Calculated Progress:** `(len(submission.events) / TOTAL_CHALLENGE_EVENTS) * 100`

    -   **Display:** A `div` for the bar container (`w-full bg-gray-200 rounded-full h-4 mb-4`) with an inner `div` for the progress (`bg-rtd-accent h-4 rounded-full` with `width: [Calculated Progress]%`).

    -   **Text:** `text-sm text-rtd-text text-center` (e.g., "`[len(submission.events)]` / `TOTAL_CHALLENGE_EVENTS` Events Processed (`[Calculated Progress]%.`)")

-   **Compute Time Summary:**

    -   Calculate `total_cpu_hours` and `total_wall_time_hours` by summing `sol.compute_info.get('cpu_hours', 0)` and `sol.compute_info.get('wall_time_hours', 0)` across all solutions.

    -   `text-lg text-rtd-text mb-2`

    -   **Total CPU Hours:** `[total_cpu_hours:.2f]`

    -   **Total Wall Time Hours:** `[total_wall_time_hours:.2f]`

    -   **Note for Participants:** `text-sm text-gray-500 italic` (e.g., "Note: Comparison to other teams' compute times is available in the Evaluator Dossier.")


### 5\. Event List (`<section class="mb-10">`)

-   **Heading:** "Submitted Events"

    -   `text-2xl font-semibold text-rtd-secondary mb-4`

-   **Table Structure:**

    -   `w-full text-left table-auto border-collapse`

    -   `<thead>` with `bg-rtd-primary text-rtd-secondary uppercase text-sm`

        -   `<th>Event ID</th>`

        -   `<th>Active Solutions</th>`

        -   `<th>Model Types Submitted</th>`

    -   `<tbody>` with `text-rtd-text`

        -   Iterate through `submission.events.values()`, sorted by `event.event_id`.

        -   Each `<tr>` with `border-b border-gray-200 hover:bg-gray-50`

            -   **Event ID:** `<td>`

                -   `font-medium text-rtd-accent hover:underline`

                -   `<a href="events/[event.event_id].html">`\[event.event\_id\]`</a>`

            -   **Active Solutions:** `<td>`

                -   `len(event.get_active_solutions())`

            -   **Model Types Submitted:** `<td>`

                -   A comma-separated string of unique `sol.model_type` values for active solutions within this event.


### 6\. Aggregate Parameter & Physical Parameter Distributions (Placeholders)

-   **Heading:** "Aggregate Parameter Distributions"

    -   `text-2xl font-semibold text-rtd-secondary mb-4`

-   **Note for Participants:** `text-sm text-gray-500 italic mb-4` (e.g., "Note: These plots show distributions from _your_ submitted solutions. Comparisons to simulation truths and other teams' results are available in the Evaluator Dossier.")

-   **Plot Placeholders:**

    -   **Einstein Crossing Time (tE) Distribution:**

        -   `![tE Distribution](https://placehold.co/600x300/dfc5fa/361d49?text=tE+Distribution+from+Your+Solutions)`

        -   `Caption: Histogram of Einstein Crossing Times (tE) from your active solutions.`

    -   **Impact Parameter (u0) Distribution:**

        -   `![u0 Distribution](https://placehold.co/600x300/dfc5fa/361d49?text=u0+Distribution+from+Your+Solutions)`

        -   `Caption: Histogram of Impact Parameters (u0) from your active solutions.`

    -   _(Repeat for other key parameters like `s`, `q` if applicable and enough data exists.)_

    -   **Lens Mass (M\_L) Distribution:**

        -   `![M_L Distribution](https://placehold.co/600x300/dfc5fa/361d49?text=Lens+Mass+Distribution+from+Your+Solutions)`

        -   `Caption: Histogram of derived Lens Masses (M_L) from your active solutions.`

    -   **Lens Distance (D\_L) Distribution:**

        -   `![D_L Distribution](https://placehold.co/600x300/dfc5fa/361d49?text=Lens+Distance+Distribution+from+Your+Solutions)`

        -   `Caption: Histogram of derived Lens Distances (D_L) from your active solutions.`


### 7\. Footer

-   **Text:** "Generated by microlens-submit v`[version]` on `[Current Date/Time]`"

    -   `text-sm text-gray-500 text-center pt-8`
