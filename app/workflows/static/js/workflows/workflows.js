$(function() {

  // Setup listener for IC-enabled content added to DOM dynamically
  $(document).on("htmx:load", function(evt) {

    // Setup parent refreshes
    setupRefreshParentElements(evt.target);
  });
});

// Finds all elements with the custon 'data-workflows-refresh-parent' attribute and sets
// them up to do just that.
function setupRefreshParentElements(element) {

    // If no element passed, use document
    if ( !element ) element = document;

    // Find all elements with the attribute 'data-workflows-refresh-parent'
    document.querySelectorAll('[data-workflows-refresh-parent]').forEach(function(element) {
        console.log(`[setupRefreshParentElements][${element.id}] Found element that will trigger parent refresh`);

        const selector = element.getAttribute('data-workflows-refresh-parent') + '[hx-get]';
        const parent = element.closest(selector);

        if (parent) {
            console.log(`[setupRefreshParentElements][${element.id}] Found parent element: ${parent.id}`);

            // Custom event listener equivalent to jQuery's "after.success.ic"
            element.addEventListener('htmx:afterRequest', function(evt) {

                // Check if it was a success or not
                if (!evt.detail.success) {
                    return;
                }

                // Refresh parent
                console.log(`[setupRefreshParentElements][${element.id}] Refreshing parent element: ${parent.id}`);
                PathDeps.refresh(parent.getAttribute('hx-get'));
            });
        } else {
            console.error(`[setupRefreshParentElements][${element.id}]: Could not find parent element with selector '${selector}' and 'hx-get' attribute`);
        }
    });
}

/**
 * Finds the closest parent element that matches the specified CSS selector and has the 'hx-get' attribute
 * and issues a refresh for its path dependencies using 'PathDeps.refresh()'.
 *
 * @param {Element} element - The DOM element from which to start searching upward.
 * @param {string} selector - A CSS selector used to identify the desired parent element.
 *
 * @throws {Error} If the provided element is not a valid DOM Element.
 *
 * @example
 * workflowsRefreshParent(document.getElementById("child"), "[data-parent]");
 */
function workflowsRefreshParent(element, selector) {
    if (!(element instanceof Element)) {
        throw new Error("Provided element is not a valid DOM Element");
    }

    // Find the nearest parent element with the passed selector and 'hx-get' attribute
    let current = element;
    while (current) {
        current = current.parentElement;
        if (current && current.matches(selector) && current.hasAttribute('hx-get')) {

            // Found the parent element to refresh, trigger the refresh.
            PathDeps.refresh(current.getAttribute('hx-get'));
            return;
        }
    }

    console.error(`[workflowsRefreshParent][${element.id}]: Could not find parent element with selector '${selector}' and 'hx-get' attribute`);
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
        PathDeps.refresh($(workflowContainer).attr("hx-get"));
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
