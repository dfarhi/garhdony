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
});
