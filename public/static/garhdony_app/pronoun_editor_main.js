$(document).ready(function() {
    //var editor = $('.editor');
    //var form = editor.closest("form")[0];
    var all_characters = [];
    characters_list = $('#characters-list').children();
    characters_list.each(function(index, character){
	var new_char = {gender:'', name:'', id:''};
	new_char.gender = character.getAttribute('gender');
	new_char.name = character.getAttribute("name");
	new_char.id = character.getAttribute("id");
	new_char.special=false; // Is this a special character, like STATIC or IGNORE?
	all_characters.push(new_char);
    });

    static_m = {gender:'M', name:'STATIC MALE', id:'SM', special:true};
    static_f = {gender:'F', name:'STATIC FEMALE', id:'SF', special:true};

    ignore_m = {gender:'M', name:'IGNORE FOR NOW', id:'IM', special:true};
    ignore_f = {gender:'F', name:'IGNORE FOR NOW', id:'IF', special:true};

    all_characters.push(static_m);
    all_characters.push(static_f);
    all_characters.push(ignore_m);
    all_characters.push(ignore_f);

    $('.editor').notebook({
	characters: all_characters,
        autoFocus: true,
	username: $('#username')[0].innerText //I don't even know how to put a comment explaining how ridiculous this method of passing the variable from django to javascript is....
    });

    //Make the editor-control-bar float at the top.
    // TODO: Abstract this to a function?
    // TODO: Doesn't work if you have more than one. But how did you get more than one?
    // TODO: Also might not work if you zoom?
    var controlBar = $('.editor-control-bar')
    var controlBarTop = controlBar.offset().top
    var controlBarLeft = controlBar.offset().left
    var controlBarWidth = controlBar.width()
    $(window).scroll( function() {
        if ($(window).scrollTop() > controlBarTop){
            controlBar.addClass('stuck-at-top');
            controlBar.width(controlBarWidth);
            controlBar.css({'left':controlBarLeft})
        } else {
            controlBar.removeClass('stuck-at-top');
            controlBar.width('100%');
            controlBar.css({'left':''})
        }
    } );
});
