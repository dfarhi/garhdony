/*
 * jQuery Notebook 0.5
 *
 * Copyright (c) 2014
 * Raphael Cruzeiro - http://raphaelcruzeiro.eu/
 * Otávio Soares
 *
 * Released under the MIT License
 * http://opensource.org/licenses/MIT
 *
 * Github https://github.com/raphaelcruzeiro/jquery-notebook
 * Version 0.5
 *
 * Some functions of this plugin were based on Jacob Kelley's Medium.js
 * https://github.com/jakiestfu/Medium.js/
 */

//This bit has to be a global variable so that the popup window can call it.
var highlightedimage;
function modifyImageClosePopup(popupwindow, url, id, changeall){
    //The popup window to change an image has been closed and url is the new url that hgihlightedimage should point to.
    // if changeall is "true", then we should change all instances of this
    if(changeall=="true"){
        var currentsrc = highlightedimage.attr('src');
        var allimages = $('img').filter(function(index, img){
            return $(img).attr('src')==currentsrc
        });
        allimages.attr('src', url);
        allimages.attr('data-id', id);
    } else {
        highlightedimage.attr('src', url);
        highlightedimage.attr('data-id', id);
    }


    popupwindow.close();
};

(function($, d, w) {
    /*
     * This module deals with the CSS transforms. As it is not possible to easily
     * combine the transform functions with JavaScript this module abstract those
     * functions and generates a raw transform matrix, combining the new transform
     * with the others that were previously applied to the element.
     */

     /* All transform  stuff has moved to pronoun_editor_storytellernotes.js since it is needed in non-edit mode also. */


    var isMac = w.navigator.platform == 'MacIntel',
        mouseX = 0,
        mouseY = 0,
        cache = {
            command: false,
            shift: false,
            isSelecting: false
        },
        modifiers = {
            //This is a dict of keynumber:action. When you press Cmd+keynumber (Ctrl on non-Mac), you get the action.
            // This gets passed to isModifier, and then calls events.commands[$ACTION]
            66: 'bold', //Cmd-b
            73: 'italic', //Cmd-i
	        190: 'flip', //Cmd-.
            85: 'underline', //Cmd-u
            112: 'h1', // Cmd-F1
            113: 'h2', // Cmd-F2
            114: 'h3', // Cmd-F3
            0o0: 'image',//No shortcut for image
            // 76: 'alignImageLeft',//Cmd-L
            // 82: 'alignImageRight',//Cmd-R
            // 67: 'alignImageCenter',//Cmd-C
            122: 'undo', //Cmd-Z
            71: 'gender', //Cmd-g
            56:'sectionBreak', //Cmd-8
            189:'dash',//Cmd-- inserts an em-dash.
            83:'save',//Cmd-s
            38:'scrollToTop'//Cmd-uparrow
            // Cmd-C, Cmd-V are browser-level copy-paste
        },
        raw_modifiers = {'flip':true},//The keys are the things that it recognizes when in raw html mode. The values are meaningless.
        options, //gets overwritten by the main function call or something like that?
        utils = {
            keyboard: {
                isCommand: function(e, callbackTrue, callbackFalse) {
                    if (isMac && e.metaKey || !isMac && e.ctrlKey) {
                        callbackTrue();
                    } else {
                        callbackFalse();
                    }
                },
                isShift: function(e, callbackTrue, callbackFalse) {
                    if (e.shiftKey) {
                        callbackTrue();
                    } else {
                        callbackFalse();
                    }
                },
                isModifier: function(e, callback) {
                    // Checks if event e was a valid keyboard shortcut
                    // (so CMD is pressed and the key pressed is in modifiers)
                    var key = e.which,
                        cmd = modifiers[key];
                    if (cmd && cache.command) {
                        callback.call(this, cmd);
                    }
                },
                isEnter: function(e, callback) {
                    //Does callback() if event e was enter being pressed.
                    if (e.which === 13) {
                        callback();
                    }
                },
                isTab: function(e, callback) {
                    //Does callback() if event e was enter being pressed.
                    if (e.which === 9) {
                        callback();
                    }
                },
                isArrow: function(e, callback) {
                    if (e.which >= 37 || e.which <= 40) {
                        callback();
                    }
                }
            }, // keyboard utils
            html: {
                addTag: function(elem, tag, focus, editable) {
                    // Adds a new element defined by tag to the end of the elem.
                    // elem should be a jqquery object.
                    // If focus is true, moves the cursor there.
                    // if editable, sets it to contenteditable=True
                    var newElement = $(d.createElement(tag));
                    if(editable){newElement.attr('contentEditable', 'true');}
                    newElement.append(' ');
                    elem.append(newElement);
                    if (focus) {
                        cache.focusedElement = elem.children().last();
                        utils.cursor.set(elem, 0, cache.focusedElement);
                    }
                    return newElement;
                }
            }, // html utils
            cursor: {
                set: function(editor, pos, elem) {
                    //Probably puts the cursor in elem at position pos?
                    var range;
                    if (d.createRange) {
                        range = d.createRange();
                        var selection = w.getSelection(),
                            lastChild = editor.children().last(),
                            length = lastChild.html().length - 1,
                            toModify = elem ? elem[0] : lastChild[0],
                            theLength = typeof pos !== 'undefined' ? pos : length;
                        range.setStart(toModify, theLength);
                        range.collapse(true);
                        selection.removeAllRanges();
                        selection.addRange(range);
                    } else {
                        range = d.body.createTextRange();
                        range.moveToElementText(elem);
                        range.collapse(false);
                        range.select();
                    }
                },
                parent: function() {
                //This must be very important.
                },
                offsetParent: function() {
                },
            }, // cursor utils
            selection: {
                save: function() {
                    //I think maybe this returns a range object corresponding to teh selection
                    // from which the selection can be recreated using restore?
                    if (w.getSelection) {
                        var sel = w.getSelection();
                        if (sel.rangeCount > 0) {
                            return sel.getRangeAt(0);
                        }
                    } else if (d.selection && d.selection.createRange) { // IE
                        return d.selection.createRange();
                    }
                    return null;
                },
                restore: function(range) {
                    // I think maybe this restores a selection based on the output of a previous call to save().
                    if (range) {
                        if (w.getSelection) {
                            var sel = w.getSelection();
                            sel.removeAllRanges();
                            sel.addRange(range);
                        } else if (d.selection && range.select) { // IE
                            range.select();
                        }
                    }
                },
                getText: function() {
                    // Gets the text of te selection
                    var txt = '';
                    if (w.getSelection) {
                        txt = w.getSelection().toString();
                    } else if (d.getSelection) {
                        txt = d.getSelection().toString();
                    } else if (d.selection) {
                        txt = d.selection.createRange().text;
                    }
                    return txt;
                },
                clear: function() {
                    // Makes nothing selected.
                    if (window.getSelection) {
                        if (window.getSelection().empty) { // Chrome
                            window.getSelection().empty();
                        } else if (window.getSelection().removeAllRanges) { // Firefox
                            window.getSelection().removeAllRanges();
                        }
                    } else if (document.selection) { // IE?
                        document.selection.empty();
                    }
                },
                getContainer: function(sel) {
                    // Returns the element containing the selection? Not used.
                    if (w.getSelection && sel && sel.commonAncestorContainer) {
                        return sel.commonAncestorContainer;
                    } else if (d.selection && sel && sel.parentElement) {
                        return sel.parentElement();
                    }
                    return null;
                },
                getSelection: function() {
                    // just gets the selection as appropriate for the browser.
                    if (w.getSelection) {
                        return w.getSelection();
                    } else if (d.selection && d.selection.createRange) { // IE
                        return d.selection;
                    }
                    return null;
                },
        		wrapSelection: function(elem) {
        		    // Takes the selection and wraps it inside of element elem.
        		    // Aborts if the selection crosses a writers-bubble boundary.
	        	    var selection = getSelection();
		            var range = selection.getRangeAt(0);


		            // Check that the start and end are inside the same writers-bubble.
		            var end = range.endContainer;
    		        var start = range.startContainer;

    	    	    var end_unbreakable = $(end).closest('.writers-bubble')[0];
	    	        var start_unbreakable = $(start).closest('.writers-bubble')[0];
		            if (end_unbreakable || start_unbreakable){
    		    	if(start_unbreakable != end_unbreakable ){return;}
	    	        }
		    
    		        var contents = range.extractContents();
	    	        elem.appendChild(contents);
    	    	    range.insertNode(elem);
	    	    }
            }, // selection utils
            validation: {
                isUrl: function(url) {
                    return (/^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/).test(url);
                }
            } // validation utils
        }, // utils
        writersBubble = {
            create: function(classname, title, selection_goes_in_outer, selection_goes_in_inner){
                // Makes a new writers bubble at the selection.
                // Writers bubbles have two parts; the outer part, which appears normal except for a colored background
                // and the inner part which only appears on mouseove.
                //
                // The selection_goes_in_* argument determines whether the selected text goes in the outer (display) part of the bubble,
                // like for stnote, and whether it goes in the inner part, like for Hidden Text. The alternative (if it's false) is the title.
                //
                // Makes the following tree:
                // <span data-larp-action=classname class='writers-bubble classname' contentEditable='false'>
                //      <span contentEditable='true'>
                //          outer text; either selection or title depending on  contentEditable='false'
                //      </span>
	            //          <span data-larp-action='writers-bubble-inner' class='writers-bubble-inner'>
	            //              <table class='classname triangle-pointer' contentEditable='true'>
	            //                  [see addInner]
	            //              </table>
	            //      </span>
                // </span>
                var outer = document.createElement('span');
                outer.setAttribute("data-larp-action", classname)
                outer.classList.add('writers-bubble');
                outer.classList.add(classname);
                outer.setAttribute('contentEditable', 'false');

                var outer_text = document.createElement('span');
                outer_text.setAttribute('contentEditable', 'true');

                // This gets the contents of the current selection.
                // Whenever we put them in, we clone them (using .cloneNode(true)),
                // lest we accidentally put the same node in two places.
                var range = utils.selection.getSelection().getRangeAt(0);
                var contents = range.extractContents();

                if (selection_goes_in_outer){
                    outer_text.appendChild(contents.cloneNode(true));
                }else{
                    outer_text.innerHTML = title;
                };

                outer.appendChild(outer_text);
                range.insertNode(outer);

                var contenttd
                if(selection_goes_in_inner){
                    contenttd = document.createElement('td');
                    contenttd.appendChild(contents.cloneNode(true));
                }else{
                    contenttd = null;
                }

                // Making the inner bubble and setting up the mouseover actions are both exciting;
                // separate them out into other functions.
                writersBubble.addInner($(outer), classname, title, contenttd);
                $.fn.setupHoverActions($(outer), true);

                //We want to add an extra &nbsp; surrounding the actual textafter it, to allow moving the cursor to after the note.
                $(outer).append("&nbsp;");
                $(outer).prepend("&nbsp;");
                return $(outer)
            },

	        addInner: function(elem, classname, title, contenttd){
	            // Makes the inner part of the writers-bubble; the actual bubble-y bit that appears and disappears
	            //
	            // elem should be a jquery object (the outer bubble). classname and title are strings,
	            // contenttd is a DOM td element (or None for the default content)
	            //
	            // The tree looks like this:
	            //
	            // <span data-larp-action='writers-bubble-inner' class='writers-bubble-inner'>
	            //      <table class='classname triangle-pointer' contentEditable='true'>
	            //          <tr>
	            //              <th colspan='2'> title </th>
	            //              <th class='button-cell' style='text-align:right'></th>
	            //                  The delete button goes in the button-cell td while in edit mode.
	            //                  But it doesn't live there by default, since then you would delete while not in edit mode.
                //          </tr>
                //          <tr>
                //              <td colspan='3'>
                //                  Main text content here. This td can be passed as an argument to the function.
                //              </td>
                //          </tr>
                //          <tr>
	            //              <th> author </th>
	            //              <th width=40></th>
	            //              <th style='text-align:right'> timestamp </th>
                //          </tr>
	            //      </table>
	            // </span>

		        if (contenttd==null){
		            contenttd = document.createElement('td');
		            contenttd.innerHTML = "I am a new "+title;
		        }
		        contenttd.setAttribute('colspan','3');
		        contenttd.classList.add('writers-bubble-content');

		        var inner_bubble = utils.html.addTag(elem, 'span', false, false)
		        inner_bubble.attr('data-larp-action','writers-bubble-inner');
		        inner_bubble.addClass('writers-bubble-inner');

		        // TODO: Make the rest of this use jquery and addTag, rather than switching to DOM objects at this stage.
		        // Probably doing so would allow us to set focus inside the stnote.
		        var table = document.createElement('table');
		        table.classList.add(classname);
		        table.setAttribute('contentEditable', 'true');
		        table.classList.add('triangle-pointer');
		        inner_bubble[0].appendChild(table);

		        var toprow = document.createElement('tr');
		        table.appendChild(toprow);
		        toprow.innerHTML = "<th colspan='2'>" + title + "</th><th class='button-cell' style='text-align:right'></th>";

		        var midrow = document.createElement('tr')
		        table.appendChild(midrow)
		        midrow.appendChild(contenttd)

		        var bottomrow = document.createElement('tr')
		        table.appendChild(bottomrow)
		        var date = new Date();
		        var datestring = date.toDateString();
		        bottomrow.innerHTML = "<th>" + options.username + "</th><th width='40'></th><th style='text-align:right'>" + datestring + "</th>"
	        },
    	},
        bubble = {
            eventInBubble: function(e, bubble_obj){
                // Is event e inside bubble bubble_obj?
                // bubble_obj is expected to be a DOM object although it gets $ed immediately.
                // if it's not present, we find all bubbles in the document.
		        if (bubble_obj){
                    var bubbleTag = $(bubble_obj);
		        }else{
		            var bubbleTag = $(document).find('.bubble');
		        };
		        var scrollTop = $(document).scrollTop();
		        if (bubbleTag.length) {
                    var bubbleRect = bubbleTag[0].getBoundingClientRect();
                    if (e.pageX > bubbleRect.left && e.pageX < bubbleRect.right &&
			                    e.pageY > bubbleRect.top+scrollTop && e.pageY < bubbleRect.bottom+scrollTop) {
                        return true;
                    };
                };
		        return false;
	        },
            updatePosBetter: function(caller, elem, bySelection) {
                // This is called to position the bubble above the selection.
                // caller: Jquery object of the thing to center it on
                // elem: Jquery object of the bubble itself.
                // bySelection: boolean of whether to center on the selection within caller, or just on caller itself.
                // if this is true, caller is ignored.
		        var parent = elem.offsetParent(); // This is the editor_bag
		        var parents_offset =  parent.offset(); // This is the editor_bag's offset relative to the document.


                // The next chunk sets boundary, which is a rectangle bounding the things we're trying to center on.
                // Either the selection or the caller
		        if(bySelection) {
		            var scrollTop = $(document).scrollTop();
                    var sel = w.getSelection(), //TODO: Use utils.selection tools for better cross-browser-ness?
                        range = sel.getRangeAt(0),
		                boundary = range.getBoundingClientRect();
		            var sel_jq = $(sel.anchorNode);
		            var containing_writers_bubbles = sel_jq.parents('.writers-bubble-inner');
		        } else {
		            var scrollTop = 0; //For some reason we don't want to add scrolltop in this case, so we make it 0.
		            var boundary = $.extend({}, $(caller).offset(), {
                                    width: $(caller).outerWidth(),
                                    height: 0
                    });
		            var containing_writers_bubbles = $(caller).parents('.writers-bubble-inner')
                }
                var bubbleWidth = elem.outerWidth(),
                    bubbleHeight = elem.height(),
                    // x and y are going to be positions relative to the parent (editor_bag);
                    // i.e. it will wind up at (parent_offset.left+x, parent_offset.top+y) wrt the document.

                    // We need the right edge to be on the screen, so the window's width has to be more than x+parents_offset+bubble's width
		            maxX = w.innerWidth-bubbleWidth-parents_offset.left,
		            // We need the left edge to be on the screen, so 0 has to be less than parents_offset+x
                    minX = -parents_offset.left,
                    // To center it properly, we want the bubble's center wrt document (x+parent_offset.left+bubblewidth/2) to equal
                    // the boundary's center (boundaryleft+boundarywidth/2)
                    idealX = (boundary.left + boundary.width/2) - (bubbleWidth / 2)-parents_offset.left,
		            pos = {
		                // x should be idealX but capped by minX, maxX
                        x: Math.min(maxX, Math.max(minX, idealX)),
                        // we want the bottom of the bubble to be 8 pixels (the height of the little triangle) above the boundary
                        // parent_offset.top+y is the top of the bubble, so parent_offset.top+y+bubbleHeight+8=boundary.top
                        // But there's also the issue that we might be scrolled down the page, so we include scrollTop.
                        y: boundary.top - bubbleHeight - 8 + scrollTop - parents_offset.top
                    };
		
                elem.translate(pos.x, pos.y)
        		containing_writers_bubbles.addClass('has-active-bubble')
            },

            updateState: function(editor, elem) {
               /*
                * Updates the bubble to set the active formats for the current selection.
                * For instance if the text is bold, the bold button gets highlighted.
                */
                elem.find('button').removeClass('active');// Remove the highlights that were there before.
                var sel = w.getSelection(),//TODO: Use utils.selection instead?
                    formats = [];
                if (sel.isCollapsed) {
                    return;
                }
                bubble.checkForFormatting(sel.focusNode, formats);
                var formatDict = {
                    'b': 'bold',
                    'i': 'italic',
                    'u': 'underline',
                    'h1': 'h1',
                    'h2': 'h2',
                    'h3': 'h3',
                    'a': 'anchor',
                    'ul': 'ul',
                    'ol': 'ol',
                    'g': 'gender'
                };
                for (var i = 0; i < formats.length; i++) {
                    var format = formats[i];
                    elem.find('button.' + formatDict[format]).addClass('active');
                }
            },

            checkForFormatting: function(currentNode, formats) {
                /*
                * Recursively navigates upwards in the DOM to find all the format
                * tags enclosing the selection.
                */
                var validFormats = ['b', 'i', 'u', 'h1', 'h2', 'h3', 'ol', 'ul', 'li', 'a'];
                if (currentNode.nodeName === '#text' ||
                    validFormats.indexOf(currentNode.nodeName.toLowerCase()) != -1) {
                    if (currentNode.nodeName != '#text') {
                        formats.push(currentNode.nodeName.toLowerCase());
                    }
                    bubble.checkForFormatting(currentNode.parentNode, formats);
                }
            },
            buildMenu: function(editor, elem) {
                // Builds the bubble menu
                //editor: ???
                //elem: Jquery bubble object
                //
                // Final tree looks like this:
                // TODO: FILL THIS IN.
                var ul = utils.html.addTag(elem, 'ul', false, false);
                for (var cmd in options.modifiers) {
                    var li = utils.html.addTag(ul, 'li', false, false);
                    var btn = utils.html.addTag(li, 'button', false, false);
                    btn.attr('editor-command', options.modifiers[cmd]);
                    btn.addClass(options.modifiers[cmd]);

                    btn.click(function(e) {
                        e.preventDefault();
                        var command = $(this).attr('editor-command');
                        events.commands[command].call(editor, e);
                    });
                }
                /* Moved this into the previous for loop.
                elem.find('button').click(function(e) {
                    e.preventDefault();
                    var cmd = $(this).attr('editor-command');
                    events.commands[cmd].call(editor, e);
                });

                */
                /* We've disabled links.
                var linkArea = utils.html.addTag(elem, 'div', false, false);
                linkArea.addClass('link-area');
                var linkInput = utils.html.addTag(linkArea, 'input', false, false);
                linkInput.attr({
                    type: 'text'
                });
                */
                
                var genderArea = utils.html.addTag(elem, 'div', false, false);
                genderArea.addClass('gender-area');
                var topRow = utils.html.addTag(genderArea, 'div', false, false);
                var characterDropdown = utils.html.addTag(topRow, 'select', false, false);
                characterDropdown.addClass('character-dropdown');
                var currentGenderPronounSpan = utils.html.addTag(topRow, 'span', false, false);
                currentGenderPronounSpan.addClass('current-gender-pronoun');
                var pronounDropdown = utils.html.addTag(topRow, 'select', false, false);
                pronounDropdown.addClass('pronoun-dropdown');
                var secondRow = utils.html.addTag(genderArea, 'div', false, false);
                secondRow.attr('id', 'secondRow');
                var flipCheckbox = utils.html.addTag(secondRow, 'input', false, false);
                flipCheckbox.attr('type', 'checkbox');
                flipCheckbox.attr('id', 'flipCheckbox');
                flipCheckbox.attr('title', "Check this box if the word refers to someone of the opposite gender from the relevant character (for example, their spouse)."); 
                var flipCheckboxLabel = utils.html.addTag(secondRow, 'span', false, false);
                flipCheckboxLabel.append('gender-reversed');
                flipCheckboxLabel.addClass('small-text');
                var hiddenRow = utils.html.addTag(genderArea, 'div', false, false);
                hiddenRow.attr('id', 'hiddenRow');
                hiddenRow.addClass('wide');
                var clearButton = utils.html.addTag(hiddenRow, 'button', false, false);
                clearButton.append("CLEAR");
                clearButton.attr('title', "Is the above information wrong?  This button clears all gender formatting on the word, making it as though you'd just typed it in.  When you next press save, if the server thinks it's a gendered word, it'll turn red and you'll be prompted to fix it again.");
                clearButton.addClass('clearGenderButton');
                clearButton.addClass('genderButton');
                var staticButton = utils.html.addTag(hiddenRow, 'button', false, false);
                staticButton.append("STATIC");
                staticButton.attr('title', "Set this word to STATIC immediately. The server will not reprocess it.");
                staticButton.addClass('staticGenderButton');
                staticButton.addClass('genderButton');
                hiddenRow.hide();


                var imageArea = utils.html.addTag(elem, 'div', false, false);
                imageArea.addClass('image-area');
                var list = utils.html.addTag(imageArea, 'ul', false, false);
                var leftli = utils.html.addTag(list, 'li', false, false);
                var leftbtn = utils.html.addTag(leftli, 'button', false, false);
                leftbtn.addClass('left-align');
                leftbtn.attr("title", "Left Align");
                leftbtn.click(function(e) {
                        e.preventDefault();
                        events.commands['alignImageLeft'].call(editor, e);
                });
                var centerli = utils.html.addTag(list, 'li', false, false);
                var centerbtn = utils.html.addTag(centerli, 'button', false, false);
                centerbtn.addClass('center-align');
                centerbtn.attr("title", "Centered");
                centerbtn.click(function(e) {
                        e.preventDefault();
                        events.commands['alignImageCenter'].call(editor, e);
                });
                var inlineli = utils.html.addTag(list, 'li', false, false);
                var inlinebtn = utils.html.addTag(inlineli, 'button', false, false);
                inlinebtn.addClass('inline-align');
                inlinebtn.attr("title", "Inline");
                inlinebtn.click(function(e) {
                        e.preventDefault();
                        events.commands['alignImageInline'].call(editor, e);
                });
                var rightli = utils.html.addTag(list, 'li', false, false);
                var rightbtn = utils.html.addTag(rightli, 'button', false, false);
                rightbtn.addClass('right-align');
                rightbtn.attr("title", "Right Align");
                rightbtn.click(function(e) {
                        e.preventDefault();
                        events.commands['alignImageRight'].call(editor, e);
                });

                var modifyImageLI = utils.html.addTag(list, 'li', false, false);
                var modifybtn = utils.html.addTag(modifyImageLI, 'button', false, false);
                modifybtn.addClass('modify-image');
                modifybtn.attr("title", "Change Image");
                modifybtn.click(function(e) {
                        e.preventDefault();
                        actions.modifyImageOpenPopup(true);
                });

                var deleteImageLI = utils.html.addTag(list, 'li', false, false);
                var deletebtn = utils.html.addTag(deleteImageLI, 'button', false, false);
                deletebtn.addClass('delete-image');
                deletebtn.attr("title", "Delete Image");
                deletebtn.click(function(e) {
                        e.preventDefault();
                        events.commands['deleteImage'].call(editor, e);
                });
                /* More links stuff. We don't use links.
                var closeBtn = utils.html.addTag(linkArea, 'button', false, false);
                closeBtn.click(function(e) {
                    e.preventDefault();
                    var editor = $(this).closest('.editor');
                    $(this).closest('.link-area').hide();
                    $(this).closest('.gender-area').hide();
                    $(this).closest('.bubble').find('ul').show();
                });
                */
            },
            show: function() {
                var tag = $(this).parent().find('.bubble');
                if (!tag.length) {
                    tag = utils.html.addTag($(this).parent(), 'div', false, false);
                    tag.addClass('jquery-notebook bubble triangle-pointer');
                }
                tag.empty();
                bubble.buildMenu(this, tag);
                tag.show();
                bubble.updateState(this, tag);
                if (!tag.hasClass('active')) {
                    tag.addClass('jump');
                } else {
                    tag.removeClass('jump');
                }
                if($(this).hasClass('editor')) {
                    bubble.updatePosBetter($(this), tag, true);
                }
                tag.addClass('active');
            },
            update: function() {
                //Calls updateState on the relevant bubble (the one near the caller).
                var tag = $(this).parent().find('.bubble');
                bubble.updateState(this, tag);
            },
            clear: function(event) {
                // Destroy all bubbles everywhere.
                // And mark everything as not having a bubble inside it.
                $('.has-active-bubble').removeClass('has-active-bubble');
                var elem = $(document).find('.bubble');

		        elem.remove()

                /*
		        var editor = elem.closest('.editor');
                elem.removeClass('active');
                bubble.hideLinkInput.call(editor);
                elem.find('.gender-area').hide();
		          elem.removeClass('gender');
                bubble.showButtons.call(editor);
                setTimeout(function() {
                    if (elem.hasClass('active')) return;
                    elem.hide();
                }, 500);
                */
            },
            genderAreaShowing: function() {
                // Is the gender portion of the bubble currently showing?
                // If there are accidentally multiple bubbles, returns true if any of the have visible gender area.
                return $(document).find('.bubble').find('.gender-area').is(":visible");
            },
            hideButtons: function() {
                // Hides the buttons of the bubble.
                // Looks for a bubble inside the parent of teh thing that calls this.
                // So if you do bubble.hideButtons.call([something]), it will find bubbles inside of [something]'s parent.
                $(this).parent().find('.bubble').find('ul').hide();
            },
            showButtons: function() {
                // See hidebuttons above.
                // Unused.
                $(this).parent().find('.bubble').find('ul').show();
            },
            showImageControls: function(image){
                bubble.show.call(image);
                var thebubble = image.closest('.editor').find('.bubble');
                bubble.hideButtons.call(thebubble);
                thebubble.find('.image-area').show();
                thebubble.find('.image-area').find('ul').show();
                bubble.updatePosBetter(image, thebubble)
            },

	        /*  We don't allow links, so comment out next chunk.

            showLinkInput: function(selection) {
                bubble.hideButtons.call(this);
                var editor = this;
                var elem = $(this).parent().find('.bubble').find('input[type=text]');
                var hasLink = elem.closest('.jquery-notebook').find('button.anchor').hasClass('active');
                elem.unbind('keydown');
                elem.keydown(function(e) {
                    var elem = $(this);
                    utils.keyboard.isEnter(e, function() {
                        e.preventDefault();
                        var url = elem.val();
                        if (utils.validation.isUrl(url)) {
                            e.url = url;
                            events.commands.createLink(e, selection);
                            bubble.clear.call(editor);
                        } else if (url === '' && hasLink) {
                            events.commands.removeLink(e, selection);
                            bubble.clear.call(editor);
                        }
                    });
                });
                elem.bind('paste', function(e) {
                    var elem = $(this);
                    setTimeout(function() {
                        var text = elem.val();
                        if (/http:\/\/https?:\/\//.test(text)) {
                            text = text.substring(7);
                            elem.val(text);
                        }
                    }, 1);
                });
                var linkText = 'http://';
                if (hasLink) {
                    var anchor = $(utils.selection.getContainer(selection)).closest('a');
                    linkText = anchor.prop('href') || linkText;
                }
                $(this).parent().find('.link-area').show();
                elem.val(linkText).focus();
            },
            hideLinkInput: function() {
                $(this).parent().find('.bubble').find('.link-area').hide();
            }
	        */
        },
        actions = {
            execCommandIgnoringContenteditable: function(command){
                var inside_uneditable_divs = $('.editor').find('span[contenteditable=false]');
                inside_uneditable_divs.attr('contenteditable', 'true');
                d.execCommand(command, false);
                inside_uneditable_divs.attr('contenteditable', 'false');
            },
	        insert: function(elem){
	            var sel = utils.selection.getSelection();
	            var range = sel.getRangeAt(0);
	            range.insertNode(elem)
	        },
	        insertHTML: function(html){
	            // execCommand('insertHTML') doesn't work inside bubbles due to some combination of the outer bubble
	            // being contenteditable='false' and the inner span being display:inline;
	            // It tries to break up some of the spans into two spans in a terrible way.

                // Solve the problem by finding the selection's container, and temporarily setting the display to block,
                // then setting it back.
                // I don't pretend to fully understand why that works, but basically I think that insertHTML is happy to
                // split up an inline tag, because it thinks it's just formatting
                // (like "<i> stuff </i>" can become "<i> stu</i> INSERTED STUFF <i>ff</i>)
                // But it doesn't like splitting up display:block things.

	            var sel = utils.selection.getSelection();
                var range = sel.getRangeAt(0);
                var container = range.startContainer;
                var editable_container = $(container).closest("[contenteditable='true']");
                var editable_containers_parent = editable_container.parent();

                if (editable_containers_parent.attr("contenteditable")=='false'){
                    // If we're inside the visible part of a writers-bubble,
                    // Do the hack with temporarily making it display:block, then restoring it.

                    var editable_container_display = editable_container[0].style.display;
                    editable_container.css("display", "block");
                    document.execCommand('insertHTML', false, html);
                    editable_container.css("display", editable_container_display);
                } else {
                    // Otherwise just insertHTML as normal
	                document.execCommand('insertHTML', false, html);
	            }
	        },
	        insertSectionBreak: function() {
	            //TODO: Might be nice to let this be an abstract markup tag whose appearance we can change later in a clean abstract way.
	            var sectionbreak = String.fromCharCode(13)+String.fromCharCode(13)+"<br><br><center>* * *</center><br>"+String.fromCharCode(13)+String.fromCharCode(13);
	            actions.insertHTML(sectionbreak);
	        },
	        insertImage: function(){
	            var image_url = '/static/garhdony_app/blank_photo.png',
	                image = $('<img style="float:right" data-id="" src='+image_url+'>');
	            actions.insert(image.get(0));
	            highlightedimage = image;
	            actions.setupImage(image);
	            actions.modifyImageOpenPopup(false);
	        },
	        insertPagebreak: function(){
	            var pagebeak = $('<div class="pagebreak"></div>');
	            actions.insert(pagebeak.get(0));
	        },
	        modifyImageOpenPopup: function(replacing){
	            var href;
	            if(replacing){
	                href = "new_image/replace";
	            }else{
	                href = "new_image/new"
	            }
                var popupwindow = window.open(href, name, 'height=500,width=600,resizable=yes');
                popupwindow.focus();
	        },
	        alignHighlightedImage: function(alignment){
	            //align 'left', 'right', 'center', or 'inline'
	            if(alignment=='left'){
	                highlightedimage.css('float', 'left');
	            } else if (alignment == 'right'){
	                highlightedimage.css('float', 'right');
	            } else {
	                highlightedimage.css('float', '');
	            }
	            if(alignment=='center'){
	                highlightedimage.css('display', 'block');
	                highlightedimage.css('margin', 'auto');
	            } else{
	            highlightedimage.css('display', '');
	                highlightedimage.css('margin', '');
	            }
	            bubble.updatePosBetter(highlightedimage, highlightedimage.closest('.editor').find('.bubble'));
	        },
	        deleteHighlightedImage: function(){
	            highlightedimage.remove();
	        },
	        insertSpell: function(){
	            //TODO: Dream about doing this.
	            alert("Oh man, wouldn't it be cool if you could input (fire/<D:day>) and have it autogenerate a diagram for you? Probably not going to happen though.")
	        },
	        setupImage: function(img){
	            img.each(function(index, image){
                    image.onclick = function(e){
                        bubble.showImageControls($(image));
                    };
                    $(image).attr("draggable", "true");
                });
            },
	        setupForm: function(elem){
		        var form = elem.closest("form")[0]; // probably that [0] should be removed.
		        form.onsubmit = function(){
		            $('.bubble').remove(); // Probably not necessary, but we don't want there to be any bubbles.
		            var editors = $('.editor:visible');
		            if (editors.length>0) {actions.flipToRawHTML(editors, true)};
		        };
	        },
	        setupControlPanel: function(elem){
	            /*
	            Sets up the black bar at the top, which is an editor-control-bar,
	            containing lots of things that are variously editor-menus (for dropdowns),
	            editor-buttons (highlight on mouseover)
	            and editor-button-labels (text styling).
	            */
		        var control_panel = $('<div class="editor-control-bar"></div>');
		        elem.closest('.editor_bag').css('padding','25 0 0 0')

        		var flip_button = $('<div class="editor-button raw-button"><div class="editor-button-label">Mode: WYSIWYG</div></div>');
		        flip_button.on('click', actions.flip);
        		flip_button.attr('title','Press Cmd+. to flip between modes.')
		        control_panel.append(flip_button);

        		var insert_menu = $('<div class="editor-menu insert-menu"><div class="editor-button-label">Insert</div></div>');
		        control_panel.append(insert_menu)

        		var insert_menu_buttons = $('<ul></ul>');
                insert_menu.append(insert_menu_buttons);

        		var section_break_button = $('<li class="editor-button editor-button-label">***</li>');
		        section_break_button.on('click', actions.insertSectionBreak);
		        section_break_button.attr('title','Press Cmd+8 or Cmd+Shift+8 to insert section break.')
        		insert_menu_buttons.append(section_break_button);

                var image_button = $('<li class="editor-button editor-button-label">image</li>');
                image_button.on('click', actions.insertImage);
		        insert_menu_buttons.append(image_button);

                var pagebreak_button = $('<li class="editor-button editor-button-label">pagebreak</li>');
                pagebreak_button.on('click', actions.insertPagebreak);
		        insert_menu_buttons.append(pagebreak_button);

        		var spell_button = $('<li class="editor-button editor-button-label">spell</li>');
                spell_button.on('click', actions.insertSpell);
        		insert_menu_buttons.append(spell_button);

		        var next_fix_button = $('<div class="editor-button next-fix-button"><div class="editor-button-label" style="color:red;">Fix Markup</div></div>');
		        next_fix_button.on('click', function(){genders.nextFixGender(elem)});
        		next_fix_button.attr('title','Jump to first markup to fix.')
		        control_panel.append(next_fix_button);

                var last_save = $.fn.last_save_data(); // Defined in edit_caching.js
                var content = $('#id_content .editor').html();
                if (last_save && (last_save.trim() != content.trim())) {
                    var recover_last_save = $('<div class="editor-button recover"><div class="editor-button-label" style="color:red;">Recover Last Save</div></div>');
                    recover_last_save.on('click', function(){
                        $('#id_content .editor').html(last_save);
                        recover_last_save.hide();
                    })
                    recover_last_save.attr('title','Restore the data that you sent in your last Save.')
                    control_panel.append(recover_last_save);
		        }

		        var save_button = $('<div class="editor-button right"><div class="editor-button-label">Save</div></div>');
		        save_button.on('click', events.commands.save);
        		save_button.attr('title','Cmd+S to save');
		        control_panel.append(save_button);

                var top_button = $('<div class="editor-button right"><div class="editor-button-label">Top</div></div>');
		        top_button.on('click', events.commands.scrollToTop);
        		top_button.attr('title','Cmd+uparrow to scroll to top.');
		        control_panel.append(top_button);

		        var shortcuts = $('<div class="editor-menu right"><div class="editor-button-label">Shortcuts</div></div>')
		        shortcuts.append($('<ul><li class="editor-button-label"><table><tr><td>Cmd+</td><td> Effect</td></tr><tr><td>B</td><td> Bold</td></tr><tr><td>I</td><td> Italic</td></tr><tr><td>U</td><td> Underline</td></tr><tr><td>S</td><td> Save</td></tr><tr><td>Z</td><td> Undo</td></tr><tr><td>8</td><td> ***</td></tr><tr><td>-</td><td> Emdash</td></tr><tr><td>.</td><td> raw</td></tr><tr><td>[up]</td><td> top</td></tr><tr><td>G</td><td> genderswitch</td></tr><tr><td>F2</td><td> h2</td></tr><tr><td>F3</td><td> h3</td></tr></table></li></ul>')); // <tr><td>L</td><td> imageleft</td></tr><tr><td>C</td><td> imagecenter</td></tr><tr><td>R</td><td> imageright</td></tr>
                control_panel.append(shortcuts);

		        control_panel.insertBefore(elem);

                // Call our custom function to make it float to the top of the screen when you scroll down.
                // (This is a custom function because we want it to float to the top of the editor_bag, not the top of the screen.)
                control_panel.floatToTopOfParent();

		    },
	        flip: function(){
		        var editor_div = $(this).closest('.editor-bag').children('.editor');
		        if (editor_div.is(':visible')) {
		            actions.flipToRawHTML(editor_div);
        		} else {actions.flipToEditor(editor_div);};},
    	    flipToRawHTML: function(editor_div, saving){
	        	var editor_bag = editor_div.closest('.editor-bag');
		        var editor_shadow = editor_bag.children('.editor-shadow');
		        //editor_div is a jquery thingamajig, and might have several entries
		        editor_div.each(function(index){
		            $(editor_shadow[index]).val(editor_div[index].innerHTML.trim());
		            });
		        $('.bubble').remove();
		        if (saving) {
		            return
        		    //We're saving the form, so no need to redisplay the text area.
		        } else {
		            // Do all the stuff for actually redisplaying the textarea
		            editor_div.hide();
		            editor_shadow.show();
		            var editor_raw_button_label = editor_bag.find('.raw-button').children('.editor-button-label');
		            editor_raw_button_label.html('Mode: &ltraw html&gt');
		        };
	        },
    	    flipToEditor: function(editor_div){
	        	var editor_bag = editor_div.closest('.editor-bag');
		        var editor_shadow = editor_bag.children('.editor-shadow');
		        //editor div had better be a jquery with only 1 entry.
		        var value = editor_shadow[0].value;
		        editor_div[0].innerHTML = value;
		        editor_div.show();
		        editor_shadow.hide();
		        var editor_raw_button_label = editor_bag.find('.raw-button').children('.editor-button-label');
		        editor_raw_button_label.html('Mode: WYSIWYG');

        		actions.setEventListeners();
	        },
            bindEvents: function(elem) {
                elem.keydown(rawEvents.keydown);
		        var shadows = elem.closest('.editor-bag').find('.editor-shadow');
		        shadows.keydown(rawEvents.shadowKeydown);
		    
                elem.keyup(rawEvents.keyup);
                elem.focus(rawEvents.focus);
                elem.bind('paste', events.paste);
                //elem.mousedown(rawEvents.mouseClick);
                elem.mouseup(rawEvents.mouseUp);
                $(document).mousedown(rawEvents.mouseClick);
                //$(document).mouseup(rawEvents.mouseUp);
                elem.mousemove(rawEvents.mouseMove);
                $('body').mouseup(function(e) {
                    if (e.target == e.currentTarget && cache.isSelecting) {
                        rawEvents.mouseUp.call(elem, e);
                    }
                });
            },
            preserveElementFocus: function() {
                var anchorNode = w.getSelection() ? w.getSelection().anchorNode : d.activeElement;
                if (anchorNode) {
                    var current = anchorNode.parentNode,
                        diff = current !== cache.focusedElement,
                        children = this.children,
                        elementIndex = 0;
                    if (current === this) {
                        current = anchorNode;
                    }
                    for (var i = 0; i < children.length; i++) {
                        if (current === children[i]) {
                            elementIndex = i;
                            break;
                        }
                    }
                    if (diff) {
                        cache.focusedElement = current;
                        cache.focusedElementIndex = elementIndex;
                    }
                }
            },
            setContentArea: function(elem) {
                var id = $('body').find('.jquery-editor').length + 1;
                elem.attr('data-jquery-notebook-id', id);
                var body = $('body');
                contentArea = $('<textarea></textarea>');
                contentArea.css({
                    position: 'absolute',
                    left: -1000
                });
                contentArea.attr('id', 'jquery-notebook-content-' + id);
                $(elem).parent().append(contentArea);
                //body.append(contentArea);
            },
	        setEventListeners: function() {
		        $('.broken-gender-switch').mousedown(function(e) {
		            e.preventDefault();
		            e.stopPropagation();
		            // Do not gaze too hard into the abyss
		            $().fixgender(e.currentTarget);
		        });
		        $('.gender-switch').mousedown(function(e) {
		            e.preventDefault();
		            e.stopPropagation();
		            // Do not gaze too hard into the abyss
		            $().showClearDialog(e.currentTarget);
		        });
		        $('.gender-static').mousedown(function(e) {
		            e.preventDefault();
		            e.stopPropagation();
		            // Do not gaze too hard into the abyss
		        $().showClearDialog(e.currentTarget);
		    });
            /*
            $('.writers-bubble-delete-button').mousedown(function(e) {
                writersBubble.delete.call(this)
            });
            $('.unhide-button').mousedown(function(e) {
                writersBubble.unhide.call(this)
            });
            $('.writers-bubble').hover(
                writersBubble.mouseOn,
                //function(e){writersBubble.showInner(this)},
                writersBubble.mouseOff
                //function(e){writersBubble.hideInner(this)}
            );
            */
		    $.fn.setupHoverActions($('.writers-bubble'), true);
	        },
            prepare: function(elem, customOptions) {
                options = customOptions;
                //actions.setContentArea(elem);
        		if (elem.closest('.editor-bag').attr('data-control-panel') || options.hasControlPanel) {
		            actions.setupControlPanel(elem);
        		};
		        actions.setupForm(elem);
		        actions.setupImage(elem.find('img'));
		        elem.attr('editor-mode', options.mode);
                elem.attr('contenteditable', true);
                elem.css('position', 'relative');
                elem.addClass('jquery-notebook editor');
		        actions.setEventListeners();
                actions.preserveElementFocus.call(elem);
		
		       /*
                *if (options.autoFocus === true) {
                *    var firstP = elem.find('p:not(.placeholder)');
                *    utils.cursor.set(elem, 0, firstP);
                *}
                */
            }
        },
        rawEvents = {
	        shadowKeydown: function(e){
                utils.keyboard.isCommand(e, function() {
                    cache.command = true;
                }, function() {
                    cache.command = false;
                });
                utils.keyboard.isModifier.call(this, e, function(modifier) {
                    if (raw_modifiers[modifier]) {
                        events.commands[modifier].call(this, e);
                    }
                });
	        },
            keydown: function(e) {
                var elem = this;
                if (cache.command && e.which === 65) { // Cmd-a. A guess to show the bubble after selecting all?
                    setTimeout(function() {
                        bubble.show.call(elem);
                    }, 50);
                }
                utils.keyboard.isCommand(e, function() {
                    cache.command = true;
                }, function() {
                    cache.command = false;
                });
                utils.keyboard.isShift(e, function() {
                    cache.shift = true;
                }, function() {
                    cache.shift = false;
                });
                utils.keyboard.isModifier.call(this, e, function(modifier) {
                        events.commands[modifier].call(this, e);
                });

                if (cache.shift) {
                    utils.keyboard.isArrow.call(this, e, function() {
                        setTimeout(function() {
                            var txt = utils.selection.getText();
                            if (txt !== '') {
                                bubble.show.call(elem);
                            } else {
                                bubble.clear.call(elem);
                            }
                        }, 100);
                    });
                } else {
                    utils.keyboard.isArrow.call(this, e, function() {
                        bubble.clear.call(elem);
                    });
                }

                if (e.which === 13) {// Enter key
                    events.enterKey.call(this, e);
                }
                if (e.which === 27) {//Escape
                    bubble.clear.call(this);
                }
                if (e.which === 86 && cache.command) {//Cmd-V for paste
                    events.paste.call(this, e);
                }
                if (e.which === 90 && cache.command) {//Cmd-Z for Undo
                    events.commands.undo.call(this, e);
                }
            },
            keyup: function(e) {
                utils.keyboard.isCommand(e, function() {
                    cache.command = false;
                }, function() {
                    cache.command = true;
                });
                actions.preserveElementFocus.call(this);

                events.change.call(this);
            },
            focus: function(e) {
                cache.command = false;
                cache.shift = false;
            },
            mouseClick: function(e) {
                // Close the editing bubble.
                cache.isSelecting = true;
                var visible_bubble = $(document).find('.bubble:visible');
                //Don't need to close it if there isn't one or the event was in it.
                if (visible_bubble.length==0){return;}
		        if (bubble.eventInBubble(e)){return;}


                    //Need to close bubble and any writers-bubbles that contained the bubble.
                    bubble.clear(e);

	    	        var all_writers_bubbles = $('.writers-bubble');
		            all_writers_bubbles.each(function(index){
		                //Hide all bubbles that are visible and the event wasn't in them.
		                // TODO: eventInBubble doesn't do what you think it does. If inner is a list, it just looks at the first one.
		                var inner=$(this).find('.writers-bubble-inner');
    		            if(inner.is(':visible')&&(!(bubble.eventInBubble(e, $(this))||bubble.eventInBubble(e, $(this).children('.writers-bubble-inner'))))){
	    		            $(this).trigger('mouseleave', e);
		                };
    		        });


    		    /*
		        var bubbleTag = $(document).find('.bubble:visible');
        		var scrollTop = $(document).scrollTop();
                if (bubbleTag.length) {
                        var bubbleRect = bubbleTag[0].getBoundingClientRect();
                    if (e.pageX > bubbleRect.left && e.pageX < bubbleRect.right &&
                        e.pageY > bubbleRect.top+scrollTop && e.pageY < bubbleRect.bottom+scrollTop) {
                            return;
                    } else {
			            bubble.clear.call(bubbleTag.closest('.editor'));
		            }
                } */
            },
            mouseUp: function(e) {
                var elem = $(e.target).closest('.editor');
                var wasSelecting = cache.isSelecting
                cache.isSelecting = false;

                //if(!bubble.genderAreaShowing()) {
                    setTimeout(function() {
                        var s = utils.selection.save();
                        if (s && wasSelecting) {
                            if (s.collapsed) {
				            //I think we don't need this anymore if we're clearing on mouse*down* instead.
                            //bubble.clear.call(elem);
                            } else {
                                bubble.show.call(elem);
                                e.preventDefault();
                            }
                        }
                    }, 50);
            },
            mouseMove: function(e) {
                mouseX = e.pageX;
                mouseY = e.pageY;
            }
        },
        events = {
            commands: {
                stNote: function(e){
                    e.preventDefault();
                    writersBubble.create('stnote', 'Storyteller Note', true, false);
                    bubble.clear();
                            events.change.call(this);
                },
                toDo: function(e){
                    e.preventDefault();
                    writersBubble.create('todo', 'To Do', true, false);
                    bubble.clear();
                            events.change.call(this);
                },
                hidden: function(e){
                    e.preventDefault();
                    var outer = writersBubble.create('hidden', 'Hidden Text', false, true);
                    var inner = outer.lastChild;
                    var delbutton = $(inner).find('.writers-bubble-delete-button');
                    //Not the most straightforwardly organized code. It uses the existing create function to make a bubble, then replaces the delete button with an unhide button.
                    delbutton.before("<span class='unhide-button'><img src='/static/garhdony_app/trash.png' height='15'></span>");
                    delbutton.remove();
                    $('.unhide-button').mousedown(function(e) {
                    writersBubble.unhide.call(this)
                    });

                    bubble.clear();
                            events.change.call(this);
                },
                sectionBreak: function(e){
                    e.preventDefault();
                    e.stopPropagation();
                    actions.insertSectionBreak()
                    events.change.call(this);
                },
                dash: function(e){
                    e.preventDefault();
                    actions.insertHTML("—");
                    events.change.call(this);
                },
                scrollToTop: function(e){
                    e.preventDefault();
                    $(d).scrollTop(0);
                },
                save: function(e){
                    e.preventDefault();
                    e.stopPropagation();
                    var saveBtn = $(".big_button[value='Save']").first();
                    saveBtn.click();
                },
                removeFormat: function(e){
                    e.preventDefault();
                    d.execCommand('removeFormat',false);
                    bubble.update.call(this);
                            events.change.call(this);
                },
                flip: function(e) {
                    actions.flip.call(this);
                    },
                bold: function(e) {
                    e.preventDefault();
                    actions.execCommandIgnoringContenteditable('bold');
                    bubble.update.call(this);
                    events.change.call(this);
                },
                italic: function(e) {
                    e.preventDefault();
                    actions.execCommandIgnoringContenteditable('italic')
                    bubble.update.call(this);
                    events.change.call(this);
                },
                underline: function(e) {
                    e.preventDefault();
                    actions.execCommandIgnoringContenteditable('underline');
                    bubble.update.call(this);
                    events.change.call(this);
                },
                alignImageLeft: function(e){
                    e.preventDefault();
                    actions.alignHighlightedImage('left');
                },
                alignImageRight: function(e){
                    e.preventDefault();
                    actions.alignHighlightedImage('right');
                },
                alignImageCenter: function(e){
                    e.preventDefault();
                    actions.alignHighlightedImage('center');
                },
                alignImageInline: function(e){
                    e.preventDefault();
                    actions.alignHighlightedImage('inline');
                },
                deleteImage: function(e){
                    actions.deleteHighlightedImage();
                    bubble.clear();
                },
                gender: function(e) {
                    // Make a complex gender switch.
                    // These are writers bubbles,
                    // Except the bottom row is replaced by character choices.

                    e.preventDefault();

                    var thebubble = writersBubble.create('gender', 'Complex Gender Switch', true, true);


                    var inner_table = thebubble.find('table');
                    inner_table.attr('contentEditable', false);
                    var altGenderContentTd = inner_table.find(".writers-bubble-content");
                    altGenderContentTd.wrapInner("<span contentEditable='true' data-larp-action='alt-gender'></span>");
                    var lastRow = inner_table.children().last();
                    var character_th = lastRow.children().first();
                    var other_last_row_cells = lastRow.children().not(character_th);
                    other_last_row_cells.remove();

                    character_th.attr('colspan', 3);
                    character_th.addClass('complex-gender-character-select');

                    character_th.empty();
                    character_th.html("If <select class='character-dropdown'></select> were ");

                    var characterDropdown = character_th.find('.character-dropdown');
                    characterDropdown.change(e, function(){
                        var new_character = genders.cycleCharacters(characterDropdown);
                        genders.assign_character(thebubble, new_character);
                    })

                    //TODO: Some way to swap which version is where?

                    // Default to characters[0], which is the previous one used.
                    // Maybe we should do something different? But I don't want to bother making a "undecided" state for this.
                    genders.assign_character(thebubble, options.characters[0]);

                    bubble.update.call(this);
                    events.change.call(this);
                },
                anchor: function(e) {
                    e.preventDefault();
                    var s = utils.selection.save();
                    bubble.showLinkInput.call(this, s);
                    events.change.call(this);
                },
                createLink: function(e, s) {
                    utils.selection.restore(s);
                    d.execCommand('createLink', false, e.url);
                    bubble.update.call(this);
                    events.change.call(this);
                },
                removeLink: function(e, s) {
                    var el = $(utils.selection.getContainer(s)).closest('a');
                    el.contents().first().unwrap();
                    events.change.call(this);
                },
                h1: function(e) {
                    e.preventDefault();
                    var theh1 = $(utils.selection.getSelection().anchorNode).closest("h1");
                    if(theh1.length) {
                        theh1.contents().unwrap(); //Turns out that what you think is unwrap() is actually contents().unwrap()
                    } else {
                        utils.selection.wrapSelection(document.createElement("h1"));
                    }
                    bubble.update.call(this);
                    events.change.call(this);
                },
                h2: function(e) {
                    e.preventDefault();
                    var theh2 = $(utils.selection.getSelection().anchorNode).closest("h2");
                    if(theh2.length) {
                        theh2.children().first().unwrap(); //Turns out that what you think is unwrap() is actually children().first().unwrap()
                    } else {
                        utils.selection.wrapSelection(document.createElement("h2"));
                    }
                    bubble.update.call(this);
                    events.change.call(this);
                },
                h3: function(e) {
                    e.preventDefault();
                    var theh3 = $(utils.selection.getSelection().anchorNode).closest("h3");
                    if(theh3.length) {
                        theh3.contents().unwrap(); //Turns out that what you think is unwrap() is actually contents().unwrap()
                    } else {
                        utils.selection.wrapSelection(document.createElement("h3"));
                    }
                    bubble.update.call(this);
                    events.change.call(this);
                },
                ul: function(e) {
                    e.preventDefault();
                    d.execCommand('insertUnorderedList', false);
                    bubble.update.call(this);
                    events.change.call(this);
                },
                ol: function(e) {
                    e.preventDefault();
                    d.execCommand('insertOrderedList', false);
                    bubble.update.call(this);
                    events.change.call(this);
                },
                undo: function(e) {
                    e.preventDefault();
                    d.execCommand('undo', false);
                    var sel = w.getSelection(),
                        range = sel.getRangeAt(0),
                        boundary = range.getBoundingClientRect();
                    $(document).scrollTop($(document).scrollTop() + boundary.top);
                    events.change.call(this);
                }
            },
            enterKey: function(e) {
                if ($(this).attr('editor-mode') === 'inline') {
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }
                //Insert <br><br>. the Char(13) is a newline in the html, which doesn't display but makes raw html mode readable.
                actions.insertHTML(String.fromCharCode(13)+String.fromCharCode(13)+'<br><br>');


                //Don't do whatever else the enter key would have done by default.
                e.preventDefault();
                e.stopPropagation();

                // Some stuff from the original code about LI tags, which we don't use.
                //var elem = $(sel.focusNode.parentElement);
                //var nextElem = elem.next();
                //if(!nextElem.length && elem.prop('tagName') != 'LI') {
                //    var tagName = elem.prop('tagName');
                //    if(tagName === 'OL' || tagName === 'UL') {
                //        var lastLi = elem.children().last();
                //        if(lastLi.length && lastLi.text() === '') {
                //            lastLi.remove();
                //        }
                //    }
                //    utils.html.addTag($(this), 'p', true, true);
                //}
                events.change.call(this);
            },
            paste: function(e) {
                var elem = $(this),
                    id = 'jqeditor-temparea',
                    range = utils.selection.save(),
                    tempArea = $('#' + id);
                if (tempArea.length < 1) {
                    var body = $('body');
                    tempArea = $('<textarea></textarea>');
                    tempArea.css({
                        position: 'absolute',
                        left: -1000
                    });
                    tempArea.attr('id', id);
                    body.append(tempArea);
                }
                //tempArea.focus(); // I removed this unilaterally, because it was causing focus to move to the bottom of the edit window for mysterious reasons.

                setTimeout(function() {
                    var clipboardContent = '',
                        paragraphs = tempArea.val().split('\n');
                    for(var i = 0; i < paragraphs.length; i++) {
                        //Add br tags between paragraphs.
                        clipboardContent += paragraphs[i]
                        if(i < paragraphs.length-1){
                            clipboardContent += String.fromCharCode(13)+String.fromCharCode(13)+'<br><br>';
                        }
                    }
                    tempArea.val('');
                    utils.selection.restore(range);
                    actions.insertHTML(clipboardContent);
                    events.change.call(this);
                }, 500);
            },
            change: function(e) {
                // This used to keep the editor-shadow up to date, but is no longer used. Now we just copy things into the editor-shadow before saving.
//                var contentArea = $('#jquery-notebook-content-' + $(this).attr('data-jquery-notebook-id'));
//                contentArea.val($(this).html());
//                var content = contentArea.val();
//                var changeEvent = new CustomEvent('contentChange', { 'detail': { 'content' : content }});
//                this.dispatchEvent(changeEvent);
            }
        };
        genders = {
            fillCharacterDropdown: function(dropdown, bothGenders, gender, useSpecials, default_character_id, allowed_character_ids){
                // dropdown is a jq object to be filled with characters.
                // bothGenders is a boolean; false only includes guy of gender gender, true includes both.
                // if useSpecials is false, it will remove STATIC and IGNORE.
                // if default_character_id is not null, it gets set as the current value.
                dropdown.empty();
                var chars_list
                options.characters.forEach(function(character, index) {
                    if (bothGenders || character.gender == gender) {
                        // If they match gender
                        if (useSpecials || !(character.special)){
                            // If we're including specials, or they aren't special.
                            if (character.special || !allowed_character_ids || allowed_character_ids.indexOf(character.id)>-1){
                                // If it's special (and thus always allowed), or there's no restricted list, or it's on the list.
                                var option = utils.html.addTag(dropdown, 'option', false, false);
                                option.attr('value', character.id);
                                option.append(character.name);
                            }
                        }
                    }
                });
                if (default_character_id){
                    dropdown.val(default_character_id)
                }

            },
            cycleCharacters: function(characterDropdown){
                // Cycles the options.characters list so that the one selected in charaterDropdown is [0]
                // and returns that character.
                // characterDropdown should be a jquery object of the <select>.
                var chosen_index=0;
                for(var i = 0; i < options.characters.length; i++) {
                    if (options.characters[i].id == characterDropdown.val()) {
                        chosen_index = i;
                        break;
                    }
                }
                var removed = options.characters.splice(chosen_index, 1);
                options.characters.unshift(removed[0]);
                return options.characters[0]
            },
            otherGender: function(g){
                if(g=="M"){return "F";}
                else if (g=="F"){return "M";}
                else {return null;}
            },
            assign_character: function(thebubble, character){
                // This function sets the character assigned to the bubble (a complex gender switch) to character.
                // It is stupidly copied both here and in storytellernotes.js
                // Because it needs to be used here (when a new gender-switch is made and a default character set)
                // and there (when an old one is changed).
                thebubble.attr('data-character', character.id);
                thebubble.attr('data-default-gender', character.gender);
                var character_th = thebubble.find('.complex-gender-character-select')
                var lastText = character_th.contents().last();
                var othergender
                if (character.gender=="M"){othergender="Female"}
                if (character.gender=="F"){othergender="Male"}
                lastText.replaceWith(" were "+othergender);
            },
            nextFixGender: function(editor){
                // Find broken gender switches, then go to the next one.
                var broken_gender_switches = editor.find('.broken-gender-switch');

                if(broken_gender_switches.length) {
                    $.fn.fixgender(broken_gender_switches[0]); // TODO ideally it would go the one after the cursor.
                } else {
                    // No more broken gender switches; clear the bubble.
		            bubble.clear.call(editor);
		            editor.parent().find('.next-fix-button').hide();
                }
            }
        }

    $.fn.notebook = function(options) {
        options = $.extend({}, $.fn.notebook.defaults, options);
        actions.prepare(this, options);
        actions.bindEvents(this);
        return this;
    };


    $.fn.updateGenderArea = function(bspan) {
        var flipCheckbox = $('.bubble').find('#flipCheckbox');
        flipCheckbox.unbind('click');
        flipCheckbox.bind('click', function(e) {
            $.fn.updateGenderArea(bspan);
        });
        
        var alt_possibility_span = $(bspan).children("[data-larp-action='alt-gender']")[0];
        var alt_possibility_words = $(alt_possibility_span).children("[data-larp-action='alt-possibility']").map(
                function(index, element) {
                    return element.innerHTML;
                });
        var characterDropdown = $('.bubble').find('.character-dropdown');
        var gender = (flipCheckbox.is(':checked') ? genders.otherGender($(bspan).attr("data-default-gender")) : $(bspan).attr("data-default-gender"));
        genders.fillCharacterDropdown(characterDropdown, false, gender, true);
        
        var currentPronounText = "";
        $(bspan).contents().each(function(index, node) {
            if (node.nodeType == 3) {
                currentPronounText = node.textContent;
                return;
            }
        });
        var currentPronoun = $('.bubble').find('.current-gender-pronoun');
        var pronounDropdown = $('.bubble').find('.pronoun-dropdown');
        pronounDropdown.empty();
        if ($(bspan).attr('data-names')){
            // We're doing the special names-only selector, by character rather than by pronoun.
            // Not sure this code goes logically here, but whatever.
            // data-names is like '13.15-17.23' if it could be character 13, keyword 15 or character 17, keyword 23'
            pronounDropdown.attr('disabled', 'true');
            pronounDropdown.attr('hidden', 'true');
            currentPronoun.attr('hidden', 'true');
            var allowed_character_ids_with_word_ids = $(bspan).attr('data-names').split('-'),
                allowed_character_ids = $.map(allowed_character_ids_with_word_ids, function(str, index){
                    return str.split('.')[0]
                })
            genders.fillCharacterDropdown(characterDropdown, false, gender, true, null, allowed_character_ids);
        }
        if(alt_possibility_words.length > 1) {
            currentPronoun.html(currentPronounText + "/");
            var nullOption = utils.html.addTag(pronounDropdown, 'option', false, false);
            nullOption.attr('value', 'null');
            nullOption.append('---');
        } else if (alt_possibility_words.length == 1){
            pronounDropdown.attr('disabled', 'true');
            pronounDropdown.attr('hidden', 'true');
            currentPronoun.html(currentPronounText + "/"+alt_possibility_words[0])
        } else {
            //no alt_possibilities.
            //This can happen when this function is called to prepare a clearing bubble on a static thing.
            currentPronoun.html(currentPronounText)
        }
        //Now populate the pronoun dropdown. Do this outside the above if/else if, b/c need to do it if there's 1 or more.
        for(var i = 0; i < alt_possibility_words.length; i += 1) {
            var option = utils.html.addTag(pronounDropdown, 'option', false, false);
            option.attr('value', alt_possibility_span.children[i].getAttribute('data-keyword'));
            option.append(alt_possibility_words[i]);
        }
    }

    $.fn.showClearDialog = function(bspan) {
        bubble.clear();
        bubble.show.call(bspan);
        $.fn.updateGenderArea(bspan);
        $('.bubble').addClass('gender');
        var characterDropdown = $('.bubble').find('.character-dropdown');
        var pronounDropdown = $('.bubble').find('.pronoun-dropdown');
        var characterName
        if (bspan.getAttribute('data-character')){
            characterName = options.characters.filter(function(character, index) {
                return bspan.getAttribute('data-character') == character.id;
            })[0].name;
            pronounDropdown.replaceWith("/"+$(bspan).find('[data-larp-action=alt-gender]')[0].innerHTML.trim());

        } else if (bspan.getAttribute('data-larp-action')=='gender-static'){
            characterName="STATIC";
            pronounDropdown.replaceWith("");
            //var currentPronoun = $('.bubble').find('.current-gender-pronoun');
        }
        else {
            // Should get here only if it's temporary-ignore.
            characterName="IGNORE";
            pronounDropdown.replaceWith("");
        }
        characterDropdown.replaceWith(characterName + ':  ');



        $('.bubble').find('#secondRow').remove();

        var clearButton = $('.bubble').find('.clearGenderButton');
        clearButton.click(function(e) {
            $('.bubble').removeClass('gender');
            $(bspan).parent().find('.bubble').remove();
            $(bspan).unbind('mousedown');
            $(bspan).find('.alt-gender').remove();
            $(bspan).replaceWith(bspan.innerHTML);
        });

        var staticButton = $('.bubble').find('.staticGenderButton');
        if ($(bspan).attr('data-larp-action')=='gender-static'){
            staticButton.hide();
        } else {
            staticButton.click(function(e) {
                $('.bubble').removeClass('gender');
                $(bspan).parent().find('.bubble').remove();
                $(bspan).unbind('mousedown');
                $(bspan).find('.alt-gender').remove();
                $(bspan).removeClass('gender-switch');
                $(bspan).addClass('gender-static');
                $(bspan).attr('data-larp-action', 'gender-static');
                $(bspan).removeAttr('contentEditable');
                $(bspan).removeAttr('data-keyword');
                $(bspan).removeAttr('data-character');
                $(bspan).mousedown(function(e) {
                    e.stopPropagation();
                    $.fn.showClearDialog(e.currentTarget);
                });
            });
        }
                          
        var elem = $('.bubble').find('select, input');
        elem.unbind('keydown');
        elem.keydown(function(e) {
            e.stopPropagation();
            if(e.which === 8)
                e.preventDefault();
            if(e.which === 27){
                bubble.clear();
            }
            var elem = $(this);
            utils.keyboard.isEnter(e, function() {
                e.preventDefault();
                bubble.clear();
            });
        });
        
        $('.bubble').find('.gender-area').show();
        $('.bubble').find('#hiddenRow').show();
        bubble.hideButtons.call(bspan);
        bubble.updatePosBetter($(bspan), $(bspan).closest('.editor').find('.bubble'), false);
    }
    
    $.fn.fixgender = function(bspan) {
	    bubble.clear();
        bubble.show.call(bspan);
        $.fn.updateGenderArea(bspan);
        $('.bubble').addClass('gender');
        
        var characterDropdown = $('.bubble').find('.character-dropdown');
        var pronounDropdown = $('.bubble').find('.pronoun-dropdown');
        var flipCheckbox = $('.bubble').find('#flipCheckbox');
        var alt_possibility_span = $(bspan).children("[data-larp-action='alt-gender']")[0];
        var alt_possibility_words = $(alt_possibility_span).children("[data-larp-action='alt-possibility']").map(
                function(index, element) {
                    return element.innerHTML;
                });
        var currentPronounText = "";
        $(bspan).contents().each(function(index, node) {
            if (node.nodeType == 3) {
                currentPronounText = node.textContent;
                return;
            }
        });
        
        var elem = $(bspan).parent().find('.bubble').find('select, input');
        elem.unbind('keydown');
        elem.keydown(function(e) {
            e.stopPropagation();
            if(e.which === 8) // Backspace
                e.preventDefault();
            if(e.which === 27){ //Escape
                bubble.clear();
	        }
            var elem = $(this);
            var bspan_jq = $(bspan);

            var submit = function() {
                // This function is called right after its declaration via utils.keyboard.isEnter
                // which just means just means "do this if they pressed enter."
                // So this function saves what they put in.
                e.preventDefault();
                if(characterDropdown.val() == 'SM' || characterDropdown.val() == 'SF') {
                    // The static 'character', added in main.js
                    // Mark is a gender-static
                    bspan_jq.empty();
                    bspan_jq.removeClass('broken-gender-switch');
                    bspan_jq.addClass('gender-static');
                    bspan_jq.attr('data-larp-action', 'gender-static');
                    bspan_jq.append(currentPronounText);
                    bspan_jq.removeAttr('contenteditable'); // Since it was false, this restores it to inheriting from the editor, namely true. That's because you can edit static things.
                } else if (characterDropdown.val() == 'IM' || characterDropdown.val() == 'IF'){
                    // The "ignore for now character", added in main.js
                    // We mark it as a temporary-ignore span, which the span_parser ignores genders inside of
                    // and removes upon saving to the database.
                    bspan_jq.empty()
                    bspan_jq.append(currentPronounText);
                    bspan_jq.removeClass('broken-gender-switch')
                    bspan_jq.attr('data-larp-action', 'temporary-ignore')
                    bspan_jq.removeAttr('contenteditable'); // Since it was false, this restores it to inheriting from the editor, namely true. That's because you can edit this if you want.
                } else {
                    // Regular character was chosen
                    if ($(bspan).attr('data-names')){
                        //If we're in special names-only mode, we need to set the pronoun based on the character.
                        var character_id = characterDropdown.val();
                        var allowed_character_ids_with_word_ids = $(bspan).attr('data-names').split('-'),
                        // That's a list like {'13.15', '17.23'}; character_id is like '17', and we need to set pronoun to '23'
                         match = $.grep(allowed_character_ids_with_word_ids, function(str, index){
                            //TODO what if there's no match somehow?
                            return str.split('.')[0]==character_id
                         })[0];
                        pronounDropdown.val(match.split('.')[1]);
                    }
                    if(pronounDropdown.val() == 'null') {
                        // If there was an ambiguity about the pronoun but the user didn't notice.
                        e.stopPropagation();
                        // Make the unfilled select flash briefly
                        $(pronounDropdown).fadeOut(50).fadeIn(50).fadeOut(100).fadeIn(100);
                        return;
                    }
                    alt_possibility_span.innerHTML = pronounDropdown.find('option:selected').text();
                    bspan_jq.attr('data-larp-action', 'gender-switch');
                    bspan_jq.removeClass('broken-gender-switch');
                    bspan_jq.addClass('gender-switch');
                    bspan_jq.attr('data-character', characterDropdown.val());
                    bspan_jq.attr('data-keyword', pronounDropdown.val());
                    if(flipCheckbox.is(':checked')) {
                        bspan_jq.attr('data-gender-reversed', 'true');
                    }
                    // gender-switches should be contentEditable false, so you can't go screwing with them.
                    bspan_jq.attr('contenteditable', 'false');


                }

                $(bspan).removeAttr('data-names');

                genders.cycleCharacters(characterDropdown);


                bspan_jq.unbind('mousedown');
                bspan_jq.mousedown(function(e) {
		            e.stopPropagation();
                    $.fn.showClearDialog(e.currentTarget);
                });

                genders.nextFixGender(bspan_jq.closest('.editor'));
                e.stopPropagation();
            };

            utils.keyboard.isEnter(e, submit)

            utils.keyboard.isTab(e, function(){
                e.stopPropagation();
                e.preventDefault();
                var gender = bspan_jq.attr('data-default-gender')
                var ignore_value = "I"+gender;
                characterDropdown.val(ignore_value);
                submit();
            })
        });
        
        $(bspan).parent().find('.bubble').find('.gender-area').show();
        bubble.hideButtons.call(bspan);
        bubble.updatePosBetter($(bspan), $(bspan).parent().find('.bubble'), false);
        characterDropdown.focus();
    };

    $.fn.notebook.defaults = {
        hasControlPanel: false,
        autoFocus: false,
        mode: 'multiline',
        modifiers: ['bold', 'italic', 'underline', 'removeFormat', 'stNote', 'toDo', 'hidden', 'image', 'h2', 'h3', 'gender'],//, 'ol', 'ul'],
        characters: [
            {name:"Tamas Kazka", gender:"M", id:"1"},
            {name:"Adorran Salom", gender:"M", id:"2"},
            {name:"Anika Yenis", gender:"F", id:"3"},
            {name:"Liza ZaHunt", gender:"F", id:"4"}
        ]
    };

    //This uses the downloaded image resizer to let users resize images.
    $(".editor").wysiwygResize({
        selector: "img",
        beforeElementSelect: function(img){
            highlightedimage = $(img);
        }});

    //These might not work with multiple editors in one window.
    $(".editor").on("dragend", function(event){
        var img = $('.editor').find('img');
        actions.setupImage(img)
    });

    $(".editor").on("input", function(event) {
        $('button .cancel-lose-unsaved-warning').show();
    });


    // Function to make the editor-control-bar stay at the top as you scroll.
    $.fn.floatToTopOfParent = function() {
        var elem = $(this);
        var parent = elem.parent();
        function update() {
            var parentTop = parent.offset().top;
            var parentLeft = parent.offset().left;
            // Get full width includng padding but not border.
            var parentWidth = parent.innerWidth();

            if ($(window).scrollTop() > parentTop){
                elem.addClass('stuck-at-top');
                elem.width(parentWidth);
                elem.css({'left':parentLeft})
            } else {
                elem.removeClass('stuck-at-top');
                elem.width(parentWidth);
                elem.css({'left':''})
            }
        } 
        // Do it on scroll or resize or zoom.
        $(window).scroll( update );
        $(window).resize( update );
        $(window).on('zoom', update);
    }


    /*
    $(".editor").get(0).addEventListener("dragstart", function(event){
        event.dataTransfer.setData(event.target);
    });
    */
})(jQuery, document, window);
