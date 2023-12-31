/* 
    This file is used to handle the timeline editing widget. 
    Its html looks like this:
    <table class="timeline">
    {% for entry_form in edit_form %}
    <tr>
        {{ entry_form.id }}
        <td class="date">
        <div>{{ entry_form.day }} {{ entry_form.day.errors }}</div>
        <div>{{ entry_form.month }} {{ entry_form.month.errors }}</div>
        <div>{{ entry_form.year }} {{ entry_form.year.errors }}</div>
        </td>
        <td>
        <div>
            {% if entry_form.instance.id %} {{entry_form.instance.event}} {% endif %}
            {{entry_form.event }} {{ entry_form.event.errors }}
        </div>
        <div>{{entry_form.internal_name }} {{ entry_form.internal_name.errors }}</div>
        </td>
        <td class="event-description">
        <div>{{ entry_form.description }} {{ entry_form.description.errors }}</div>
        </td>
    </tr>
    {% endfor %}
    </table>
    {# Hidden event-date mapping for use in javascript #}
    <div id="event-date-mapping" style="display: none;">
    {% for entry in sheet.timeline.events.all %}
        <div class="event-date-mapping" data-event-id="{{event.id}}" data-year="{{event.year}}" data-month="{{event.month}}" data-day="{{event.day}}"></div>
    {% endfor %}
    </div>

    What we need to do, for new rows only (the last few rows, which start out blank):
    * When the user changes a date (yr/month/day), filter the events select widget to contain only those events that match the fields that are chosen.
    * When the user selects an event, update the date fields to match the event.
    
    Note that there are a bunch of separate entry_forms on the page, with separate ids. Each lives inside an outer <tr> tag, like this:
    <tr>
        <td class="date">
            <div><select class="event-day" name="descriptions-2-day" id="id_descriptions-2-day">…</select></div>
            <div><select class="event-month" name="descriptions-2-month" id="id_descriptions-2-month">…</select></div>
            <div><select class="event-year" name="descriptions-2-year" id="id_descriptions-2-year">…</select></div>
        </td>
        <td>
            <select name="descriptions-1-event" class="event-select" id="id_descriptions-1-event">
                <option value>---------</option>
                <option value="1">Event 1</option>    
                <option value="2">Event 2</option>
            </select>
        </td>
    </tr>
    ...
*/
$(document).ready(function() {
    // Get the event-date mapping
    var event_date_mapping = {};
    $('.event-date-mapping').each(function() {
        var event_id = $(this).data('event-id');
        var year = $(this).data('year');
        var month = $(this).data('month');
        var day = $(this).data('day');
        event_date_mapping[event_id] = {
            'year': year,
            'month': month,
            'day': day
        };
    });

    // Get the event select widgets
    // For each one, store the event select widget and the year/month/day select in an object:
    // {
    //     'event_select': event_select
    //     'day_select': day_select
    //     'month_select': month_select
    //     'year_select': year_select
    // }
    var rows = [];
    $('.event-select').each(function() {
        var event_select = $(this);
        var day_select = $(this).closest('tr').find('.event-day');
        var month_select = $(this).closest('tr').find('.event-month');
        var year_select = $(this).closest('tr').find('.event-year');
        rows.push({
            'event_select': event_select,
            'day_select': day_select,
            'month_select': month_select,
            'year_select': year_select
        });
    });

    // For each event select widget, add a change handler
    rows.forEach(function(row) {
        // When the user changes the event select widget, update the date fields to match the event
        row.event_select.change(function() {
            var event_id = row.event_select.val();
            if (event_id) {
                // if the user selected a non-blank event, update the date fields
                var date = event_date_mapping[event_id];
                row.day_select.val(date.day);
                row.month_select.val(date.month);
                row.year_select.val(date.year);
            } else {
                // if the user selected a blank event, clear the date fields
                // TODO: Not sure what to do here. Should we clear the date fields, or leave them alone?
            }
        }
        );
    });

    // When the user changes the date select widget, filter the event select widget to contain only those events that match the fields that have values.
    // First let's make a function that filters the event select widget based on the date fields
    function filter_event_select(event_select, day_select, month_select, year_select) {
        // Get the values of the date fields
        var day = day_select.val();
        var month = month_select.val();
        var year = year_select.val();
        // Now find all the events that match those values
        // Remember to ignore empty values (e.g. if the user hasn't set the day yet)
        var matching_events = [];
        for (var event_id in event_date_mapping) {
            var date = event_date_mapping[event_id];
            if ((day == '' || day == date.day) && (month == '' || month == date.month) && (year == '' || year == date.year)) {
                matching_events.push(event_id);
            }
        }
        // Now update the event select widget to hide other events
        event_select.find('option').each(function() {
            var option = $(this);
            var event_id = option.val();
            if (matching_events.indexOf(event_id) == -1) {
                option.hide();
            } else {
                option.show();
            }
        });
    }

    // Now let's add a change handler to each date select widget
    rows.forEach(function(row) {
        // When the user changes the date select widget, filter the event select widget to contain only those events that match the fields that have values.
        row.day_select.change(function() {
            filter_event_select(row.event_select, row.day_select, row.month_select, row.year_select);
        });
        row.month_select.change(function() {
            filter_event_select(row.event_select, row.day_select, row.month_select, row.year_select);
        });
        row.year_select.change(function() {
            filter_event_select(row.event_select, row.day_select, row.month_select, row.year_select);
        });
    });
});

