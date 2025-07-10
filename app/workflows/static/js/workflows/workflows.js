$(function() {

  // Setup listener for IC-enabled content added to DOM dynamically
  $(document).on("elementAdded.ic", function(evt) {

    // Setup parent refreshes
    setupRefreshParentElements(evt.target);
  });
});

// Finds all elements with the custon 'ic-refresh-parent' attribute and sets
// them up to do just that.
function setupRefreshParentElements(element) {

    // If no element passed, use document
    if ( !element ) element = document;

    // Find all elements with the attribute 'ic-refresh-parent'
    $(element).find("[ic-refresh-parent]").addBack("[ic-refresh-parent]").each(function() {
        console.log(`[setupRefreshParentElements][${$(this).attr('id')}] Found element that will trigger parent refresh`);

        // Get the parent element
        var parent = $(this).closest(`${$(this).attr("ic-refresh-parent")}[ic-src]`).first();
        if ( parent ) {
            console.log(`[setupRefreshParentElements][${$(this).attr('id')}] Found parent element: ${$(parent).attr('id')}`);

            // Add a handler for the element to trigger refreshes.
            $(this).on("after.success.ic", function(evt, elt, data, textStatus, xhr, requestId) {
                console.log(`[setupRefreshParentElements][${$(this).attr('id')}] Refreshing parent element: ${$(parent).attr('id')}`);

                // Refresh parent
                Intercooler.refresh($(parent).attr("ic-src"));
            });
        } else {
          console.error(`[setupRefreshParentElements][${$(this).attr('id')}]: Could not find parent element with selector '${$(this).attr("ic-refresh-parent")}' and 'ic-src' attribute`);
        }
    });
}

// Returns 'true' when the passed workflow state status is a final one
function workflowStateStatusIsComplete(status) {
    const finalStatuses = ["completed"];
    return finalStatuses.includes(status);
}

// Returns 'true' when the passed step state status is a final one
function stepStateStatusIsComplete(status) {
    const finalStatuses = ["completed", "indefinite"];
    return finalStatuses.includes(status);
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
function checkWorkflowStateStatus(workflowContainer, stepContainer) {

    // Ensure workflow is fully loaded and rendered.
    if ( !checkWorkflowStateStepsLoaded(workflowContainer) )
        return;

    // Get statuses
    const workflowId = $(workflowContainer).attr("id");
    const workflowStatus = $(workflowContainer).find(".workflow-content").first().data("workflow-state-status");
    const stepId = $(stepContainer).attr("id");
    const stepStatus = $(stepContainer).find(".step-content").first().data("step-state-status");

    // Only perform check when workflow is not completed.
    if ( workflowStateStatusIsComplete(workflowStatus) ) {
        console.log(`[checkWorkflowStateStatus][${workflowId}] Status: ${workflowStatus}, skipping`);
        return;
    }

    // Only perform check when the current step is complete.
    if ( !stepStateStatusIsComplete(stepStatus) ) {
        console.log(`[checkWorkflowStateStatus][${stepId}] Status: ${stepStatus}, skipping`);
        return;
    }

    // Check status of steps.
    var workflowCompleted = true;
    $(workflowContainer).find(".step-content").each(function() {

        // Check status
        workflowCompleted = stepStateStatusIsComplete($(this).data("step-state-status"));
    });

    // Update the workflow if completed
    console.log(`[checkWorkflowStateStatus][${workflowId}] Completed: ${workflowCompleted}`);
    if ( workflowCompleted ) {

        // Update the workflow state
        console.log(`[checkWorkflowStateStatus][${workflowId}] Updating`);
        Intercooler.refresh(workflowContainer);
    }
}

function generateRandomString(length) {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  const charactersLength = characters.length;
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
}
