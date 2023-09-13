
/**
 * Finds all 'button' elements contained in a form and toggles their 'disabled' proeprty.
 * @param  {String} formSelector  The jQuery selector of the form to disable buttons for.
 */
function toggleFormButtons(formSelector) {

    // Toggle disabled state of all buttons in form
    $(formSelector).find("button").each(function() {
        $(this).prop("disabled", !$(this).prop("disabled"));
    });
}
