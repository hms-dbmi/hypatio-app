/**
 * Checks if a DOM element has "refresh-step" in its "hx-trigger" attribute.
 *
 * @param {Element} element - The DOM element to inspect.
 * @returns {boolean} - True if "refresh-step" is present, false otherwise.
 */
function hasRefreshStepTrigger(element) {
    if (!(element instanceof Element)) {
        throw new Error("Provided input is not a valid DOM element.");
    }

    const triggerAttr = element.getAttribute("hx-trigger");
    if (!triggerAttr) {
        return false;
    }

    return triggerAttr
        .split(',')
        .map(s => s.trim())
        .includes("refresh-step");
}

/**
 * Returns a string identifier for an element.
 * Uses `id` if present, otherwise builds a CSS-like path.
 *
 * @param {Element} element - The DOM element to identify.
 * @returns {string} - A string identifier.
 */
function getElementIdentifier(element) {
    if (!(element instanceof Element)) {
        throw new Error("Provided input is not a valid DOM element.");
    }

    if (element.id) {
        return `#${element.id}`;
    }

    const parts = [];
    let el = element;

    while (el && el.nodeType === Node.ELEMENT_NODE) {
        let part = el.tagName.toLowerCase();

        if (el.className) {
            const classList = [...el.classList].filter(c => !!c);
            if (classList.length) {
                part += '.' + classList.join('.');
            }
        }

        parts.unshift(part);

        el = el.parentElement;
    }

    return parts.join(' > ');
}

/**
 * Triggers a refresh on a workflow step element and optionally updates its dependents.
 *
 * This function checks if the given DOM element is part of a `.workflow-step-container` and,
 * based on the provided flags, triggers an `htmx` event to refresh the step itself and/or
 * invokes `PathDeps.refresh()` to update dependent steps.
 *
 * @param {Element} element - The DOM element within the workflow step to refresh.
 * @param {boolean} [refreshStep=true] - Whether to trigger a refresh of the current step.
 * @param {boolean} [refreshDependents=true] - Whether to refresh dependent steps based on the `hx-get` path.
 *
 * @throws {Error} Throws if the provided input is not a valid DOM `Element`.
 *
 * @example
 * const el = document.getElementById("step-1");
 * refreshStep(el); // Refreshes the step and its dependents
 *
 * @example
 * refreshStep(el, true, false); // Only refreshes the step, not its dependents
 */
function refreshStep(element, refreshStep = true, refreshDependents = true) {
    if (!(element instanceof Element)) {
        throw new Error("Provided input is not a valid DOM element");
    }
    const stepContainer = element.closest('.workflow-step-container');
    if (!stepContainer) {
        console.error(`[workflows][refreshStep] Element '${element.getAttribute('id')}' has no parent with class 'workflow-step-container'`);
        return;
    }

    // Get the identifier
    const stepContainerIdentifier = getElementIdentifier(stepContainer);

    // Trigger a refresh on the step itself
    if (refreshStep) {

        // Ensure step container listens to 'refresh-step'
        if (!hasRefreshStepTrigger(stepContainer)) {
            console.error(`[workflows][refreshStep] Element '${stepContainerIdentifier}' does not specify 'refresh-step' in its 'hx-trigger' attribute, cannot refresh`);
        } else {
            console.debug(`[workflows][refreshStep] Refresh: ${stepContainerIdentifier}`);
            htmx.trigger(stepContainer, "refresh-step");
        }
    }

    // Trigger a dependency update
    if (refreshDependents) {

        // Ensure step container has 'hx-get'
        if (!stepContainer.getAttribute("hx-get")) {
            console.error(`[workflows][refreshStep] Element '${stepContainerIdentifier}' has no 'hx-get' attribute, cannot refresh`);
        } else {
            console.debug(`[workflows][refreshStep] Refresh dependencies for: ${stepContainerIdentifier}/${stepContainer.getAttribute("hx-get")}`);
            PathDeps.refresh(stepContainer.getAttribute("hx-get"));
        }
    }
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

    // Needs an ID
    if (!workflowId) {
        return;
    }

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
        htmx.trigger(workflowContainer[0], "refresh-workflow");
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
