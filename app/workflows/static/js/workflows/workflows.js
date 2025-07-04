$(function() {

  // Setup parent refreshes
  setupRefreshParentsElements(document);
});

// Finds all elements with the custon 'ic-refresh-parents' attribute and sets
// them up to do just that.
function setupRefreshParentsElements(element) {

    // If no element passed, use document
    if ( !element ) element = document;

    // Find all elements with the attribute 'ic-refresh-parents'
    $(element).find("[ic-refresh-parents]").each(function() {
        console.log(`Refresh parent: ${$(this)}`);

        // Get the parent's src
        var parentSrc = $(this).find($(this).attr("ic-refresh-parent")).attr("ic-src");
        if ( parentSrc ) {
            console.log(`Parent src: ${parentSrc}`);

            // Add a handler for the element to trigger refreshes.
            $(this).on("after.success.ic", function(evt, elt, data, textStatus, xhr, requestId) {

                // Refresh parent
                Intercooler.refresh(parentSrc);
            });
        }
    });
}

// This function checks to ensure all of a workflows steps have been loaded
// and rendered fully.
function checkWorkflowStateStepsLoaded(workflowContainer) {

    // For each step-container, ensure there is a step-content element.
    const workflowId = $(workflowContainer).attr("id");
    var isLoaded = true;
    $(workflowContainer).find(".workflow-step-container").each(function() {

        // Ensure a step-content element exists and check the status.
        var stepContent = $(this).find(".step-content").first();
        isLoaded = stepContent !== undefined && stepContent.data("step-state-status") !== undefined;
    });

    if ( isLoaded )
        console.log(`[checkWorkflowStateStepsLoaded][${workflowId}] Is loaded`);

    return isLoaded;
}


// This function checks a workflows steps to see if they're all recently completed
// and updates the workflow accordingly.
function checkWorkflowStateStatus(workflowContainer, stepContainer, completedStatus = "completed") {

    // Ensure workflow is fully loaded and rendered.
    if ( !checkWorkflowStateStepsLoaded(workflowContainer) )
        return;

    // Get statuses
    const workflowId = $(workflowContainer).attr("id");
    const workflowStatus = $(workflowContainer).find(".workflow-content").first().data("workflow-state-status");
    const stepId = $(stepContainer).attr("id");
    const stepStatus = $(stepContainer).find(".step-content").first().data("step-state-status");

    // Only perform check when workflow is not completed.
    if ( workflowStatus === completedStatus ) {
        console.log(`[checkWorkflowStateStatus][${workflowId}] Status: ${workflowStatus}, skipping`);
        return;
    }

    // Only perform check when the current step is complete.
    if ( stepStatus !== completedStatus ) {
        console.log(`[checkWorkflowStateStatus][${stepId}] Status: ${stepStatus}, skipping`);
        return;
    }

    // Check status of steps.
    var workflowCompleted = true;
    $(workflowContainer).find(".step-content").each(function() {

        // Check status
        workflowCompleted = $(this).data("step-state-status") === completedStatus;
    });

    // Update the workflow if completed
    console.log(`[checkWorkflowStateStatus][${workflowId}] Completed: ${workflowCompleted}`);
    if ( workflowCompleted ) {

        // Update the workflow state
        console.log(`[checkWorkflowStateStatus][${workflowId}] Updating`);
        updateWorkflowStateStatus(workflowContainer, completedStatus);
    }
}

function updateWorkflowStateStatus(workflowContainer, status) {

    // Update the form value
    var form = $(workflowContainer).find(".workflow-state-form").first();
    var input = $(form).find(".workflow-state-form-status-input").first();

    // Update the value
    $(input).val(status);

    // Refresh the workflow.
    Intercooler.triggerRequest(form);
}
