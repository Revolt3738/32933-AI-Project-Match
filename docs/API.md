# API Documentation

## Base Information

*   **Base URL:** Assumed to be `http://localhost:5000` during development.
*   **Authentication:** Uses Flask-Login session cookies managed by the browser. API calls intended for authenticated users must be made within an active browser session where the user is logged in. There is no separate API token authentication.
*   **Content-Type:** Requests with a JSON body should use `Content-Type: application/json`.

## Endpoints

---

### 1. AI Chat & Project Matching

#### Send Chat Message & Get Recommendations

*   **Method:** `POST`
*   **Path:** `/api/chat`
*   **Auth Required:** Yes (Student Role)
*   **Description:** Takes a student's natural language query, analyzes it using the AI to extract fields, keywords, features, and skills, then calls the AI again to rank existing projects based on these requirements. Returns a list of relevant projects.
*   **Request Body:**
    ```json
    {
        "message": "string" // The student's query (e.g., "I know Python and want an AI project")
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
        "projects": [
            {
                "id": integer,          // Project ID
                "name": string,         // Project Name
                "description": string,  // Project Description
                "field": string,        // Project Field/Domain
                "skill_requirements": string, // Required skills (comma-separated or description), or ""
                "teacher_email": string // Email of the supervising teacher
            }
            // ... more projects if matched
        ]
    }
    ```
    *Note: If no suitable projects are found based on the AI ranking score threshold (currently >= 3), the `projects` list will be empty.*
*   **Error Responses:**
    *   `403 Forbidden`: If the logged-in user is a teacher. Returns `{"error": "Unauthorized"}`.
    *   `405 Method Not Allowed`: If requested via GET. Returns `{"message": "Only POST method is supported"}`.

---

### 2. Project Management (Teacher Only)

#### Create New Project via API

*   **Method:** `POST`
*   **Path:** `/api/projects`
*   **Auth Required:** Yes (Teacher Role)
*   **Description:** Allows a logged-in teacher to create a new project. This endpoint seems primarily used by the modal form on the teacher dashboard.
*   **Request Body:**
    ```json
    {
        "name": "string",           // Required
        "description": "string",    // Required
        "field": "string",          // Required
        "skill_requirements": "string" // Optional, defaults to ""
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": integer,
        "name": string,
        "description": string,
        "field": string,
        "skill_requirements": string // or ""
    }
    ```
*   **Error Responses:**
    *   `403 Forbidden`: If the logged-in user is not a teacher. Returns `{"error": "Unauthorized"}`.
    *   `400 Bad Request`: If required fields (`name`, `description`, `field`) are missing. Returns `{"error": "Project Name, Description, and Field are required."}`.

---

### 3. Student Project Interest

#### Express Interest in a Project

*   **Method:** `POST`
*   **Path:** `/student_interest/<int:project_id>`
*   **Auth Required:** Yes (Student Role)
*   **Description:** Allows a logged-in student to select a project by expressing interest. A student can only select one project at a time.
*   **URL Parameters:**
    *   `project_id` (integer): The ID of the project the student is interested in.
*   **Request Body:** None
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Interest expressed successfully!"
    }
    ```
*   **Error Responses:**
    *   `403 Forbidden`: If the logged-in user is a teacher. Returns `{"error": "Teachers cannot express interest"}`.
    *   `400 Bad Request`:
        *   If the student has already selected this specific project. Returns `{"message": "You have already selected this project."}`.
        *   If the student has already selected a *different* project. Returns `{"message": "You have already selected another project. Please cancel your previous selection first."}`.

#### Cancel Interest in a Project

*   **Method:** `POST` (Note: The backend route also accepts GET for browser redirects, but the API interaction is likely POST)
*   **Path:** `/cancel_interest/<int:project_id>`
*   **Auth Required:** Yes (Student Role)
*   **Description:** Allows a logged-in student to cancel their previously expressed interest in a project.
*   **URL Parameters:**
    *   `project_id` (integer): The ID of the project to cancel interest in.
*   **Request Body:** None
*   **Success Response (200 OK):**
    ```json
    {
        "message": "Selection cancelled."
    }
    ```
*   **Error Responses:**
    *   `403 Forbidden`: If the logged-in user is a teacher (results in a redirect with a flash message, not a JSON error).
    *   `404 Not Found`: If no interest record exists for the current student and the specified `project_id`.

---

## Error Handling

API endpoints generally return appropriate HTTP status codes to indicate success or failure:

*   **2xx (e.g., 200 OK, 201 Created):** Success
*   **400 Bad Request:** Client error (e.g., missing required parameters)
*   **403 Forbidden:** Authentication successful, but user lacks permission for the action.
*   **404 Not Found:** The requested resource (e.g., project) could not be found.
*   **405 Method Not Allowed:** The HTTP method used is not supported for the endpoint.

When an error occurs (4xx or 5xx status codes), the response body typically contains a JSON object with an `error` or `message` key providing details about the error. 

*Example Error Response:*
```json
{
    "error": "Descriptive error message (e.g., Unauthorized)"
}
```
*or*
```json
{
    "message": "Descriptive error message (e.g., You have already selected this project.)"
}
```

*Note: The exact structure is not strictly standardized across all error responses. Some non-API related errors or redirects might result in HTML responses with flashed messages instead of JSON.*
