(function ($) {
    var utils = {
        makeTextBox: function(cell){
            var existing = cell.text();
            cell.empty();
            var newTextBox = $("<text")
        }
    }
    var setup = {
        yearCells: function(cells){
            cells.click(function(){
                $(this)
            })
        },
        dateCells: function(cells){
        },
        nameCells: function(cells){
        },
        descCells: function(cells){
        },
        charCells: function(cells){
        },
        charIndividuals: function(labels){
        },
    }
    $(document).ready(function() {
        setup.yearCells($(".year"));
        setup.dateCells($(".date"));
        setup.nameCells($(".name"));
        setup.descCells($(".default-description"));
        setup.charCells($(".characters"));
        setup.charIndividuals($(".individual-character"));
    })


})(jQuery);