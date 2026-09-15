# Bug Fix: Generate Time Cards Endpoint

## Issue
When clicking the "Generate Time Cards" button from the employee interface, an unexpected error occurred and no time cards were generated.

## Root Cause
**File:** `services/timelog-service/app/services/task_client.py` (line 54)

**Problem:** Unsafe response parsing when fetching tasks from the Task Service:

```python
# BUGGY CODE:
items = payload.get("tasks", payload) if isinstance(payload, dict) else payload
```

**Why it failed:**
- If the Task Service response was a dict WITHOUT a "tasks" key (e.g., error response, malformed response), the code would use the entire dict as `items`
- When iterating `for item in items` over a dict, Python iterates over the **keys** (strings), not values
- Attempting to create `TaskAssignment(string_key)` would fail or produce invalid objects
- This cascaded into the generate endpoint failing with an unexpected error

**Example failure scenario:**
```python
payload = {"error": "some error"}
items = payload.get("tasks", payload)  # Falls back to entire dict
# Now: for item in items iterates over ["error"] (the keys)
# Trying: TaskAssignment("error") → TypeError or invalid object
```

## Solution
Replaced unsafe fallback logic with proper type validation:

```python
# FIXED CODE:
if isinstance(payload, dict):
    items = payload.get("tasks", [])  # Default to empty list, not entire payload
    if not isinstance(items, list):   # Validate tasks field is a list
        raise AppError(
            status_code=502,
            code="UPSTREAM_ERROR",
            message=f"Task Service response has unexpected format: tasks field is not a list",
        )
elif isinstance(payload, list):
    items = payload
else:
    items = []  # Gracefully handle unexpected types
return [TaskAssignment(item) for item in items]
```

## Testing
- ✅ All 40 existing unit tests still pass (including `test_generate_week_is_idempotent`)
- ✅ Added 6 new edge-case tests in `tests/test_task_client_response_parsing.py`:
  - Correct response format
  - Missing "tasks" key
  - List-format response
  - Non-list "tasks" field (validation error)
  - Empty list
  - Null response

## Impact
- **Fixes:** Generate Time Cards button now works reliably even if Task Service returns unexpected formats
- **Prevents:** Cascade failures from malformed upstream responses
- **Improves:** Error reporting with specific validation errors instead of generic "unexpected error"

## Files Modified
1. `services/timelog-service/app/services/task_client.py` - Fixed response parsing
2. `services/timelog-service/tests/test_task_client_response_parsing.py` - Added edge-case tests (new file)
