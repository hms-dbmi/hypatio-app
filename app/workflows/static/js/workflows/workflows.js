// This function checks a workflows steps to see if they're all recently completed
// and updates the workflow accordingly.
function checkWorkflowStateStatus(workflowContainer, stepContainer, completedStatus = "completed") {
    console.log(`[checkWorkflowStatus] ${completedStatus}`);

    // Only perform check when workflow is not completed.
    if ( $(workflowContainer).find(".workflow-content").first().data("workflow-state-status") === completedStatus ) {
        console.log("Skipping " + $(workflowContainer).attr("id") + " -> " + $(workflowContainer).find(".workflow-content").first().data("workflow-state-status"));
        return;
    }

    // Only perform check when the current step is complete.
    if ( $(stepContainer).find(".step-content").first().data("step-state-status") !== completedStatus ) {
        console.log("Skipping " + $(stepContainer).attr("id") + " -> " + $(stepContainer).find(".step-content").first().data("step-state-status"));
        return;
    }

    // Check status of steps.
    var workflowCompleted = true;
    $(workflowContainer).find(".step-content").each(function() {
        console.log($(this).attr("id") + ' -> ' + $(this).data("step-state-status"));
        // Check status
        workflowCompleted = $(this).data("step-state-status") === completedStatus;
    });

    // Update the workflow if completed
    if ( workflowCompleted ) {
        console.log("Workflow is completed!");

        // Update the workflow state
        updateWorkflowStateStatus(workflowContainer, completedStatus);

    } else {
        console.log("Workflow is incomplete");
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
