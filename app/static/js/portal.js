/**
 * Notification event handler. Listens for notification events passed via
 * response headers and displays the notification accordingly.
 * Note: This is only valid from HTMX requests. Vanilla responses from the
 * server will not trigger this event.
 */
window.addEventListener("showNotification", function(event) {

    // Get notification details
    const level = event.detail.level;
    const icon = event.detail.icon;
    const message = event.detail.message;

    // Show the notification.
    notify(level, message, icon);
});

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

function notify(type, message, icon) {
    $.notify({
        // options
        icon: 'glyphicon glyphicon-' + icon,
        message: message,
    },{
        // settings
        type: type,
        allow_dismiss: true,
        newest_on_top: false,
        showProgressbar: false,
        placement: {
            from: "top",
            align: "center"
        },
        offset: {
            x: 0,
            y: 80
        },
        spacing: 10,
        z_index: 1031,
        delay: 2000,
        timer: 500,
        animate: {
            enter: 'animated fadeInDown',
            exit: 'animated fadeOutUp'
        }
    });
}

$( document ).ready(function() {
    $('.collapse').on('show.bs.collapse', function() {
        var icon = $( this ).closest('.panel-default' ).find( '.step-icon' )[0]

        // Find the control.
        $( icon ).addClass('glyphicon-collapse-up').removeClass('glyphicon-collapse-down');
    });

    $('.collapse').on('hide.bs.collapse', function() {
        var icon = $( this ).closest('.panel-default' ).find( '.step-icon' )[0]

        // Check if completed.
        var collapsedClass = 'glyphicon-collapse-down'
        if( $( icon ).hasClass('filled_out_already') ) {
            collapsedClass = 'glyphicon-check'
        }

        // Find the control.
        $( icon ).addClass(collapsedClass).removeClass('glyphicon-collapse-up');
    });
});

// Fetches the CSRF token from cookies for sending along with AJAX requests.
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

// Add XSRF headers to HTMX requests
document.addEventListener('htmx:configRequest', function(evt) {

    // Check origin
    const requestUrl = new URL(evt.detail.path, window.location.origin);
    if (requestUrl.origin !== window.location.origin) {
        console.warn('Blocked cross-origin request to:', requestUrl.href);
        evt.preventDefault(); // Cancels the HTMX request
    }

    // Add the CSRF token.
    if (!csrfSafeMethod(evt.detail.verb)) {
        evt.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
});

/* Manage scripts */
$( document ).ready(function() {
    $("#manage-collapse-panels-button").on("click", function(event) {
        $('.panel-collapse').collapse('hide');
    });
    $("#manage-show-panels-button").on("click", function(event) {
        $('.panel-collapse').collapse('show');
    });
    $(".manage-reload-page-button").on("click", function(event) {
        window.location.reload();
    });
});

/* Clipboard */
$(document).ready(function(){

    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();

    // Reset tooltips
    $('[data-toggle="tooltip"][data-tooltip-title]').on('hidden.bs.tooltip', function(){
        $(this).attr('data-original-title', $(this).attr('data-tooltip-title'));
    });

    // Setup copy button
    var clipboards = new ClipboardJS(".clipboard-copy");
    clipboards.on('success', function(e) {

        // Update tooltip
        $(e.trigger).attr('data-original-title', "Copied!")
            .tooltip('fixTitle')
            .tooltip('setContent')
            .tooltip('show');

        e.clearSelection();
    });

    clipboards.on('error', function(e) {

        // Update tooltip
        $(e.trigger).attr('data-original-title', "Error!")
            .tooltip('fixTitle')
            .tooltip('setContent')
            .tooltip('show');

        // Log it
        console.log('Copy error:' + e.toString());

        e.clearSelection();
    });
});
