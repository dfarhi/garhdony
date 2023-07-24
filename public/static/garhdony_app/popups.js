(function($, d, w) {
    var actions = {
        refilterChoices: function(){
            var selectedSheets = $('input.sheetCheck:checked');
            var sheetNames = $.map(selectedSheets, function(radio, index){
                return radio.value
            });
            var images = $('.thumbnail');
            images.hide()

            var filterstring = $('#textfilter').val();
            if(filterstring){
                images = images.filter(function(index, image){
                    var name = $(image).attr('data-name'),
                        found = name.indexOf(filterstring);
                    return found>-1
                })
            }

            images.each(function(index, img){
                $.each(sheetNames, function(index, sheet){
                    var findSheet = $(img).find('li').filter('[data-name="'+sheet+'"]');
                    if (findSheet.length){
                        $(img).show();
                    }
                })
            })
        },
        selectAllSheets: function(){
            $('input.sheetCheck').prop('checked', true);
            $('#all-checkbox').prop('checked', false);
            actions.refilterChoices();
        },
        selectNoSheets: function(){
            $('input.sheetCheck').prop('checked', false);
            $('#none-checkbox').prop('checked', false);
            actions.refilterChoices();
        }
        /*
        filterSheetsOnOff:function(){
            var on = $('#filtersheets').prop('checked');
            $('.hides-with-sheets').toggle(on);
            actions.refilterChoices();
        }*/
    }
    $(d).ready(function(){
        var hiddenselect = $('#hidden-select');
        $('.thumbnail').click(function(e){
                $('.thumbnail.selected').removeClass('selected');
                $(this).addClass('selected');
                var id = $(this).attr('data-id')
                hiddenselect.val(id);
        });

        $('input.sheetCheck:checkbox').click(actions.refilterChoices);

        $('#textfilter').on("keyup", actions.refilterChoices);
        $('#all-checkbox').click(actions.selectAllSheets);
        $('#none-checkbox').click(actions.selectNoSheets);
        //$('#filtersheets').change(actions.filterSheetsOnOff);
        actions.refilterChoices();
    });
})(jQuery, document, window);
