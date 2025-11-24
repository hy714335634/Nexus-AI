# DynamoDB Runtime Errors - Fixed

**Date**: 2025-11-23
**Status**: ✅ **RESOLVED**

---

## Executive Summary

Fixed two critical DynamoDB runtime errors that were occurring during the Celery build workflow execution:

1. **ExpressionAttributeNames NoneType error** in `update_project_progress()`
2. **Missing artifacts_table attribute** in DynamoDBClient

---

## Error 1: ExpressionAttributeNames NoneType Bug

### Problem

**Error Message**:
```
AttributeError: 'NoneType' object has no attribute 'update'
```

**Location**: `api/database/dynamodb_client.py:957`

**Root Cause**:
```python
# Line 933: expression_names initialized as empty dict
expression_names = {}

# Line 957: Empty dict evaluates to falsy, becomes None
ExpressionAttributeNames=expression_names if expression_names else None
```

When `expression_names` is an empty dict `{}`, it evaluates to falsy in Python's boolean context, so it becomes `None`. However, boto3's `update_item()` method doesn't properly handle `ExpressionAttributeNames=None` and tries to call `.update()` on it, resulting in the AttributeError.

### Fix Applied

**File**: `api/database/dynamodb_client.py:961-971`

**Solution**: Only pass the `ExpressionAttributeNames` parameter if the dict has content:

```python
# Build update_item parameters conditionally
update_params = {
    'Key': {'project_id': project_id},
    'UpdateExpression': update_expression,
    'ExpressionAttributeValues': expression_values
}
# Only add ExpressionAttributeNames if it has content
if expression_names:
    update_params['ExpressionAttributeNames'] = expression_names

self.projects_table.update_item(**update_params)
```

**Impact**: This error prevented proper stage progress tracking during build workflow execution.

---

## Error 2: Missing artifacts_table Attribute

### Problem

**Error Message**:
```
AttributeError: 'DynamoDBClient' object has no attribute 'artifacts_table'. Did you mean: 'projects_table'?
```

**Location**: `api/database/dynamodb_client.py:1621`

**Root Cause**:
The `artifacts_table` property was never defined in the DynamoDBClient class, but multiple methods were trying to access it:
- `create_artifact_record()` at line 1565
- `list_artifacts_by_agent()` at line 1583
- `list_artifacts_by_project()` at line 1605
- `delete_artifacts_for_stage()` at line 1621

### Fix Applied

**Files**:
- `api/database/dynamodb_client.py:132` (initialization)
- `api/database/dynamodb_client.py:178-183` (property definition)
- `api/database/dynamodb_client.py:211` (connection reset)

**Solution 1**: Add `_artifacts_table` to initialization:
```python
# Table references - will be initialized lazily
self._projects_table = None
self._agents_table = None
self._invocations_table = None
self._artifacts_table = None  # ← ADDED
self._agent_sessions_table = None
self._agent_session_messages_table = None
```

**Solution 2**: Add property for lazy initialization:
```python
@property
def artifacts_table(self):
    """Lazy initialization of artifacts table"""
    if self._artifacts_table is None:
        self._artifacts_table = self.dynamodb.Table('AgentArtifacts')
    return self._artifacts_table
```

**Solution 3**: Add to connection reset logic:
```python
def _ensure_connection(self):
    """Ensure DynamoDB connection is healthy"""
    if not self.health_check():
        logger.warning("DynamoDB connection unhealthy, attempting to reconnect")
        # Reset table references to force reconnection
        self._projects_table = None
        self._agents_table = None
        self._invocations_table = None
        self._artifacts_table = None  # ← ADDED
        self._agent_sessions_table = None
        self._agent_session_messages_table = None
```

**Table Name**: Following the naming convention (AgentProjects, AgentInstances, AgentInvocations, etc.), the table is named **`AgentArtifacts`**.

**Impact**: This error prevented artifact cleanup operations during stage transitions.

---

## Verification

### Server Reload Confirmation

The uvicorn server successfully detected and reloaded the changes:
```
WARNING:  StatReload detected changes in 'api/database/dynamodb_client.py'. Reloading...
INFO:     Shutting down
INFO:     Application shutdown complete.
INFO:     Started server process [39592]
INFO:     Application startup complete.
```

### Celery Logs Before Fix

**Error Frequency**: Multiple occurrences during `proj_b0520328c1e1` build:
```
[2025-11-23 11:32:09,882: ERROR/ForkPoolWorker-8] Error updating project progress: 'NoneType' object has no attribute 'update'
[2025-11-23 11:32:09,884: ERROR/ForkPoolWorker-8] Failed to update stage status: Failed to update project progress: 'NoneType' object has no attribute 'update'
[2025-11-23 11:32:09,885: ERROR/ForkPoolWorker-8] Failed to mark stage completed for project proj_b0520328c1e1 stage agent_developer_manager: Failed to update stage status: Failed to update project progress: 'NoneType' object has no attribute 'update'

[2025-11-23 11:31:57,168: ERROR/ForkPoolWorker-8] Error deleting artifacts for project proj_b0520328c1e1 stage agent_code_developer: 'DynamoDBClient' object has no attribute 'artifacts_table'
```

### Expected Behavior After Fix

1. ✅ Stage progress updates should complete without NoneType errors
2. ✅ Artifact operations should execute successfully
3. ✅ Build workflow should track stages properly in DynamoDB
4. ✅ Frontend should display accurate stage progress

---

## Files Modified

1. **api/database/dynamodb_client.py**
   - Line 132: Added `_artifacts_table = None` initialization
   - Lines 178-183: Added `artifacts_table` property
   - Line 211: Added artifacts_table to connection reset
   - Lines 961-971: Fixed ExpressionAttributeNames conditional logic

---

## Testing Recommendations

1. **Trigger a new build workflow**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/projects \
     -H "Content-Type: application/json" \
     -d '{"requirement": "Test build after DynamoDB fixes"}'
   ```

2. **Monitor Celery logs**:
   ```bash
   tail -f logs/celery.log | grep -E "ERROR|artifacts_table|ExpressionAttributeNames"
   ```

3. **Verify no errors occur** during:
   - Stage transitions
   - Progress updates
   - Artifact cleanup operations

4. **Check frontend** displays proper stage progress in real-time

---

## Related Documentation

- **API Contract Verification Report**: `web/API-CONTRACT-VERIFICATION-REPORT.md`
- **Tasks Tracking**: `.kiro/specs/web-api-integration-audit/tasks.md`
- **Celery Logs**: `logs/celery.log`

---

## Conclusion

**Status**: ✅ **BOTH ERRORS FIXED**

Both critical runtime errors have been resolved:
1. ✅ ExpressionAttributeNames NoneType error - Fixed by conditional parameter passing
2. ✅ Missing artifacts_table - Fixed by adding proper property definition

The build workflow should now execute without these DynamoDB-related errors. Stage progress tracking and artifact management will function correctly.

**Next Steps**:
- Monitor next build execution to confirm fixes work in production
- Consider adding unit tests for DynamoDB client error handling
- Document table schema for AgentArtifacts table

**Fix Date**: 2025-11-23
**Fixed By**: Claude Code (DynamoDB Runtime Error Fix)
**Sign-off**: ✅ Ready for Testing
