# Daria Interview Tool - Release Notes

## Release Candidate 2 (RC2) - May 6, 2025

### Fixed Issues
- Fixed LangChain compatibility errors that were preventing interviews from starting
- Resolved Text-to-Speech integration issues causing TTS to fail during interviews
- Fixed template errors when handling missing interviewee information
- Added missing analysis functionality to properly generate insights after interviews
- Improved conversation context handling to reduce repetitive questions

### Improvements
- Enhanced prompt handling for more natural interview flow
- Added better error handling and fallbacks throughout the application
- Improved compatibility with newer versions of LangChain
- Enhanced system feedback during interview sessions

### Known Issues
- Monitor Interview link leads to a 404 page
- LangChain imports generate deprecation warnings

### Installation
See README_RC2.md for detailed installation and usage instructions 

### May, 28,  2025

Absolutely! Here’s a detailed documentation of all the new backend features and endpoints you’ve added in these six steps, followed by an explanation of the “3,M” you see in Cursor, and how to address any problems in `run_interview_api.py`.

---

# 🚀 DARIA Interview Tool: Backend Feature & Endpoint Documentation

## 1. **Advanced Export Features**

### **Export as JSON**
- **Endpoint:** `/api/research_session/<session_id>` (GET)
  - Returns the full session as JSON.
- **Endpoint:** `/api/session/<session_id>/export` (GET)
  - Returns a structured export of the session (with transcript, messages, analysis, etc.).
  - Add `?download=true` to force a file download.

### **Export as CSV**
- **Endpoint:** `/api/session/<session_id>/export_csv` (GET)
  - Query param: `fields` (comma-separated list of fields to export)
  - Example: `/api/session/abc123/export_csv?fields=title,project,analysis`
  - Returns a CSV file with the selected fields.

### **Batch Export as CSV**
- **Endpoint:** `/api/sessions/export_csv` (POST)
  - Body: `{ "session_ids": [ ... ], "fields": [ ... ] }`
  - Returns a CSV file with the selected fields for all specified sessions.

---

## 2. **Annotation Features**

### **Save Annotation**
- **Endpoint:** `/api/annotation` (POST)
  - Body: `{ "session_id": "...", "chunk_id": "...", "annotation": { "user": "...", "tag": "...", "comment": "...", "code": "...", "timestamp": "..." } }`
  - Appends the annotation to the list for the given chunk in `data/interviews/sessions/<session_id>_annotations.json`.

### **Get Annotations**
- **Endpoint:** `/api/annotations/<session_id>` (GET)
  - Returns all annotations for the session, grouped by chunk.

### **Export Annotated Data**
- Use the above endpoints to fetch and merge transcript and annotations for export.

---

## 3. **Researcher Collaboration**

### **Shared Tagging**
- The annotation structure supports multiple users annotating the same chunk, with attribution.

### **Consensus/Disagreement Views**
- **Endpoint:** `/api/annotations/<session_id>/consensus` (GET)
  - Returns, for each chunk, a count of how many users assigned each tag.
  - Example response:
    ```json
    {
      "chunk_id_1": { "Pain Point": 2, "Insight": 1 },
      "chunk_id_2": { "Opportunity": 1 }
    }
    ```

---

## 4. **Download/Share Features**

### **Download Buttons**
- Use the above export endpoints to allow users to download session/analysis data as JSON or CSV.

### **Shareable Links**
- The URLs for session/analysis detail pages can be used as shareable links.
- You can add a “Copy Link” button in the frontend.

---

## 5. **Quality-of-Life Improvements**

### **Error Reporting**
- All endpoints return error messages in a consistent format (e.g., `{ "success": false, "error": "..." }`).
- LLM parsing errors are surfaced in the `parsing_error` field of analysis responses.

### **Admin Tools**
- **List All Annotations:** `/api/annotations/<session_id>/all` (GET)
- **Edit/Delete Annotation:** `/api/annotation/<session_id>/<chunk_id>/<int:index>` (PUT/DELETE)
- **Delete Analysis:** `/api/analysis/<session_id>` (DELETE)

---

## 6. **Other Notable Endpoints**

- **Export Clusters:** `/api/export_clusters` (POST)
  - Returns embeddings and metadata for a session (for visualization/export).
- **Save Annotation (ChromaDB):** `/api/save_annotation` (POST)
  - (Demo only; real update support depends on ChromaDB capabilities.)

---

# 🟢 What does “3,M” mean in Cursor?

- **3**: There are 3 linter or static analysis problems (errors or warnings) in the file.
- **M**: The file is “Modified” (has unsaved or uncommitted changes in your git working directory).

**What to do:**
- Click on the “3” in Cursor to see the list of problems. They may be syntax errors, unused imports, or other issues flagged by your linter.
- If you want, I can review the file for you and suggest or make fixes for those 3 problems.

---

## ✅ Next Steps

- Let me know if you want to see a sample React component for any of these features.
- If you want me to review and fix the 3 problems in `run_interview_api.py`, just say so and I’ll do it right away!

Would you like to proceed with the React UI, or should I address the linter problems in your backend file first?
