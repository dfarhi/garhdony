/*
 * I'm going to try to make a Jquerything
 * by copying the notebook file
 */

(function($, d, w){
    var setup = {
        set_edit_lock_cache: function(){
            // Caches the ID of the current edit_lock, so that if we recover from the cache we know what edit lock we had.
            localStorage.setItem(utils.storage_name()+":editlock", $('#id_edit_lock').val());
        }
    }
    var utils = {
        storage_name: function(){
            // The key of the localStorge dictionary to use for this sheet.
            // Uses the sheet's name.
            var sheetNameh1 = $('#sheet-name');
            return  sheetNameh1.html().trim();
        },
        callback_if_storage: function(callback){
            //Make sure there is storage on the browser, then do callback()
            if(typeof(Storage)!=="undefined"){return callback();}
        }
    }

    var cache = {
        set: function(){
            // Sets the cache to the current content.
            var content_div = $('#id_content .editor');
            var contents = content_div.html();
            localStorage.setItem(utils.storage_name(), contents);
        },

        set_last_save: function(){
            // Marks that this cache was sent to the serve for saving.
            var content_div = $('#id_content .editor');
            var contents = content_div.html();
            localStorage.setItem(utils.storage_name()+":last_saved", contents);
        },

        clear: function(){
            // Clears the cache.
            // We need to do this whenever the page closes;
            // Opening the page and finding a cache is interpreted as "the browser crashed or something"
            localStorage.removeItem(utils.storage_name());
        },

        get: function(){
            // Read the cache (return its value)
            return localStorage.getItem(utils.storage_name());
        },

        get_last_save: function() {
            // Read the last save request we send.
            return localStorage.getItem(utils.storage_name()+":last_saved");
        }
    }

    var saving = {
        send: function(form, action) {
            cache.set_last_save();
            LOADING_WHEEL_ON("Contacting Server");
            $.ajax({
                url:"presave/",
                type: "GET",
                success: saving.received,
                error: saving.error,
                timeout: 3000, // Apparently in firefox this doesn't cancel it or something.
            })
        },
        received: function(json){
            var status = json.status
            if (status=="OK") {
                $("#main-form").unbind("submit", saving.submit);
                $(window).unbind('beforeunload');
                LOADING_WHEEL_ON("Saving");
                $("[clicked=true]").click();
            } else {
                saving.failed(status,"OK")
            }
        },
        failed: function(errorThrown, textStatus, responseText){
            LOADING_WHEEL_OFF()
            var text = "Saving failed!";
            if (textStatus) {text = text + "\n\nConnection: " + textStatus}
            if (errorThrown) {text = text + "\n\nError: " + errorThrown}
            if (responseText) {
                text = text + "\n\nresponseText: " + responseText
            }
            if (textStatus=="error"){
                text = text + "\n\nPerhaps double check your internet and login status in another tab and then try again."
            }
            alert(text);
        },
        error: function(xhr, textStatus, errorThrown){
            saving.failed(errorThrown, textStatus, xhr.responseText)
        },
        submit: function(event){
            var action = $("[clicked=true]").val()
            if(action =='Save' || action =='Override' || action =='MergeKeepMine' || action =='Automerge' ){
                event.preventDefault();
                saving.send($("#main-form"), action);
            }
            //Do nothing special: Cancel, Break
        }
    }

    $.fn.last_save_data = function() {
        return utils.callback_if_storage(function(){
            return cache.get_last_save();
        });
    }

    $.fn.load_cache = function(original_text){
        //  Upon loading the page, if there's a storage system, check for a cache
        // If there is a cache, the previous browser must have exploded, so restore it.
        utils.callback_if_storage(function(){
            var cached = cache.get();
            if (cached && (cached!=original_text)) {
                //TODO Make this a choice?
                alert("It seems that you were editing this sheet earlier and didn't leave cleanly. I'm going to restore what I have from that edit. If you don't like it, just press Cancel.");
                var content_div = $('#id_content .editor');
                content_div.html(cached);

                // If we're recovering from a previous editlock, put it in recovered_edit_lock.
                // The view will then do the right thing wrt edit conficts.
                $('#id_recovered_edit_lock').val(localStorage.getItem(utils.storage_name()+":editlock"));
            } else {
            // We're free to edit normally.
            // Cache our lock, in case our browser crashes and someone else needs to recover it.
            setup.set_edit_lock_cache();
            }
        })
    }

    $.fn.cache_sheet_edits = function(original_text){
        // Setup the automatic caching, if there's a storage system.
        utils.callback_if_storage(function(){
            // cache whenever it changes.
            var editor = $('#id_content .editor');
            editor.on('input', function(){
                cache.set();
            })

            var turn_off_recover_last_save = function() {
                $('.editor-button.recover').hide();
                editor.unbind('input', turn_off_recover_last_save);
            }
            editor.on('input', turn_off_recover_last_save);

            /*
            //When the cancel button is pressed, clear the cache.
            var clearing_buttons = $("button.big_button[value='Cancel']");
            clearing_buttons.click(
                function(){
                    // Suppress the unsaved changes warning, since the window is about to close.
                    // The actual clearing happens in window.unload().
                    $(window).unbind('beforeunload');
                }
            )
            */

            $("#main-form").on('submit', saving.submit)

            $("form button.big_button").click(function() {
                $("form button.big_button").removeAttr("clicked");
                $(this).attr("clicked", "true");
            });


            $(window).bind('beforeunload', function(){
                // beforeunload is a built-in thing.
                // If it returns a string, then it shows the browser's default 'unsaved changes' warning.
                var cached = cache.get();
                if(cached && (cached.trim() != original_text.trim())){
                    return "You have unsaved changes!";
                }
            })

            $(window).unload(function(){
                // This happens if they pushed through the beforeunload warning
                // Or they pressed Save or Cancel.
                // Either way, they want to forget these changes, so we clear the cache.
                cache.clear();
            })


        })
    }
})(jQuery, document, window);

$(document).ready(function() {
    var original_text = $('#id_content .editor').html();

    $.fn.load_cache(original_text)

    $.fn.cache_sheet_edits(original_text);
})