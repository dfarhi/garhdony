(function($, d, w) {

    var transform = (function() {
        var matrixToArray = function(str) {
	    if (!str || str == 'none') {
                return [1, 0, 0, 1, 0, 0];
	    }
	    return str.match(/(-?[0-9\.]+)/g);
        };
	
        var getPreviousTransforms = function(elem) {
		return elem.css('-webkit-transform') || elem.css('transform') || elem.css('-moz-transform') ||
                elem.css('-o-transform') || elem.css('-ms-transform');
        };
	
        var getMatrix = function(elem) {
	    var previousTransform = getPreviousTransforms(elem);
	    return matrixToArray(previousTransform);
        };
	
        var applyTransform = function(elem, transform) {
	    elem.css('-webkit-transform', transform);
	    elem.css('-moz-transform', transform);
	    elem.css('-o-transform', transform);
	    elem.css('-ms-transform', transform);
	    elem.css('transform', transform);
        };
	
        var buildTransformString = function(matrix) {
	    return 'matrix(' + matrix[0] +
                ', ' + matrix[1] +
                ', ' + matrix[2] +
                ', ' + matrix[3] +
                ', ' + matrix[4] +
                ', ' + matrix[5] + ')';
        };
	var getTranslate = function(elem) {
	    var matrix = getMatrix(elem);
	    return {
                x: parseInt(matrix[4]),
                y: parseInt(matrix[5])
	    };
        };
	
        var scale = function(elem, _scale) {
	    var matrix = getMatrix(elem);
	    matrix[0] = matrix[3] = _scale;
	    var transform = buildTransformString(matrix);
	    applyTransform(elem, transform);
        };
	
        var translate = function(elem, x, y) {
	    var matrix = getMatrix(elem);
	    matrix[4] = x;
	    matrix[5] = y;
	    var transform = buildTransformString(matrix);
	    applyTransform(elem, transform);
        };
	
	
        var rotate = function(elem, deg) {
	    var matrix = getMatrix(elem);
	    var rad1 = deg * (Math.PI / 180);
	    var rad2 = rad1 * -1;
	    matrix[1] = rad1;
	    matrix[2] = rad2;
	    var transform = buildTransformString(matrix);
	    applyTransform(elem, transform);
        };
	
        return {
	    scale: scale,
	    translate: translate,
	    rotate: rotate,
	    getTranslate: getTranslate
        };
    })(); // end of "transform" function                                                                                     
    
    $.fn.translate = function(x,y){transform.translate(this, x, y)};

    var actions = {
            unhide: function(){
                var inner = $(this).closest('.writers-bubble-inner');
                var outer = inner.closest('.writers-bubble');
                var contenttd = inner.find('.writers-bubble-content');
                var content = contenttd.html();
                outer.replaceWith(content);
            },
            delete: function(){
                var inner = $(this).closest('.writers-bubble-inner');
                var outer = inner.closest('.writers-bubble');
                inner.remove();
                var contents = outer.find('[contenteditable=true]').contents(); //Remove the outermost thing and the contenteditable thing.
                outer.replaceWith(contents);
            }
    };
    
    var setup = {
        position: function(bubble){
        //TODO: Improve this; it's not great for multiline notes.
        // Also it's not getting outerwidth right?
	    var outerwidth = bubble.outerWidth();
	    var outerheight = bubble.outerHeight();
	    var inner = bubble.find('.writers-bubble-inner');
	    var innerwidth = inner.outerWidth();
	    var innerheight = inner.outerHeight();
	    var posx =  - outerwidth/2 - innerwidth/2;
	    var posy = -innerheight+2;
	    
	    var bubbleleft = bubble.offset().left;
	    var maxX = w.innerWidth-innerwidth-bubbleleft;
	    var minX = -bubbleleft;
	    var boundedposx = Math.min(maxX, Math.max(minX, posx));
	    inner.translate(boundedposx, posy);
	},
        showInner: function(bubblespan, editmode){
            setTimeout(function(){
                var inner = $(bubblespan).children('.writers-bubble-inner');
                inner.show();

                if (editmode){
                    // Put in the delete button
                    if ($(bubblespan).hasClass('hidden')){
                    var action = function(e){actions.unhide.call(this)}
                    }else{
                        var action = function(e){actions.delete.call(this)}
                    };
                    setup.addCornerButton(bubblespan, 'trash.png', action);
                    var bubble_jq = $(bubblespan)
                    if(bubble_jq.hasClass('gender')){
                        //For complex gender switches, add the button for changing who it is.
                        var characterDropdown = bubble_jq.find('.character-dropdown');
                        var default_char_id = bubble_jq.attr('data-character');
                        genders.fillCharacterDropdown(characterDropdown, true, null, false, default_char_id);
                        characterDropdown.unbind('change');
                        characterDropdown.change(function(e){
                            var new_character = genders.cycleCharacters(characterDropdown);
                            genders.assign_character(bubble_jq, new_character)});
                    };
                };
                setup.position($(bubblespan))
            }, 50);
        },
	mouseOn: function(editmode){
        if (editmode){
            return function(e){
                var already_visible = $(this).find('.writers-bubble-inner').is(':visible');
                var actively_editing_writers_bubble = $('.has-active-bubble');
                if (!already_visible&&!actively_editing_writers_bubble.length){
                    setup.showInner(this, true);
                }
            }
        } else {
            return function(e){setup.showInner(this, false)}
        };
    },
	mouseOff: function(e){
	    if (!setup.hasActiveBubble($(this))){    
                setup.hideInner(this);                                            
            }; 
	},                                                                                
        hasActiveBubble: function(writers_bubble){                                   
            return writers_bubble.find('.writers-bubble-inner').hasClass('has-active-bubble');                          
        },
	hideInner: function(bubble){
            setTimeout(function(){
                var inner = $(bubble).find('.writers-bubble-inner');
                var button_cell = inner.find('.button-cell');
                button_cell.html('');
                inner.css('display','');//Don't want .hide() because we want it to go back to the default behavior of appearing on hover, as specified in css, when not in writing mode.                                                                                                                                                                                     
            }, 100);
        },
        addCornerButton: function(bubble, img_name, action){
	    var inner = $(bubble).children('.writers-bubble-inner');
	    var table = inner.children('table');
	    var firstrow = table.find('tr:first');
            var button_cell = firstrow.children('.button-cell');
            var new_span = document.createElement('span');
            button_cell.append(new_span);
            new_span.innerHTML = "<span><img src='/static/garhdony_app/"+ img_name +"' height='15px'></span>";
            $(new_span).click(action);
        }
    };
    $.fn.setupHoverActions = function(writers_bubble,editmode){
	writers_bubble.hover(
	    setup.mouseOn(editmode),
	    setup.mouseOff
	)
	
    };

    //A window can only have a single onload, so this might conflict with other things....
    // TODO: Should be easy to fix this by making it jquery instead.
    w.onload = function(){$.fn.setupHoverActions($('.writers-bubble'), false);}

})(jQuery, document, window);

