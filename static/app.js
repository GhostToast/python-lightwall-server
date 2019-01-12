/* global swatches */
$( function() {

    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];



    // Load color pickers, leveraging noUiSlider.
    function rgbwColorPicker() {
        [].slice.call(sliders).forEach(function (slider, index) {

            noUiSlider.create(slider, {
                start: 0,
                step: 1,
                connect: [true, false],
                tooltips: [true],
                range: {
                    'min': 0,
                    'max': 255
                },
                format: {
                    to: function (value) {
                        return parseInt(value);
                    },
                    from: function (value) {
                        return parseInt(value);
                    }
                }
            });

            // Bind keyboard.
            var handle = slider.querySelector('.noUi-handle');
            handle.addEventListener('keydown', function (e) {
                var value = parseInt(slider.noUiSlider.get());
                if (e.which === 37) {
                    slider.noUiSlider.set(value - 1);
                }
                if (e.which === 39) {
                    slider.noUiSlider.set(value + 1);
                }
            });

            // Bind the color changing function to the update event.
            slider.noUiSlider.on('set', function () {
                colors[index] = slider.noUiSlider.get();

                var alpha = makeAlpha(colors[3]);
                var previewColor = 'rgba('+colors[0]+','+colors[1]+','+colors[2]+','+alpha+')';
                previewElement.style.background = previewColor;
                previewElement.style.color = previewColor;

                colorsData = getColors();
                
                $.ajax({
                    url: '/_post_rgbw_color/',
                    type: 'POST',
                    dataType: 'json',
                    data: colorsData,
                    success: function(resp) {
                        console.log(resp);
                    }
                });
            });
        });

        function refreshSwatch() {
            var r = parseInt(redSlider.noUiSlider.get()),
                g = parseInt(greenSlider.noUiSlider.get()),
                b = parseInt(blueSlider.noUiSlider.get()),
                w = parseInt(whiteSlider.noUiSlider.get());

            console.log( "r"+r+"g"+g+"b"+b+"w"+w );
            $.ajax({
                    url: '/_post_rgbw_color/',
                    type: 'POST',
                    dataType: 'json',
                    data: {
                        red: r,
                        blue: b,
                        green: g,
                        white: w
                    },
                    success: function(resp) {
                        console.log(resp);
                    }
            });
        }
    }

    // Load swatches from server.
    function loadSwatches() {
        if (!Array.isArray(swatches) || !swatches.length) {
            return;
        }
        swatches.forEach(addSwatch);
    }

    // Add new swatch.
    function addSwatch(swatch) {
        var swatchWrapper = document.createElement('div');
        swatchWrapper.classList.add('swatch-wrapper');
        
        var swatchAnchor = document.createElement('a');
        swatchAnchor.classList.add('swatch');
        
        swatchAnchor.style.background = 'rgba('+swatch.r+','+swatch.g+','+swatch.b+','+makeAlpha(swatch.w)+''
        swatchAnchor.setAttribute('data-r', swatch.r);
        swatchAnchor.setAttribute('data-g', swatch.g);
        swatchAnchor.setAttribute('data-b', swatch.b);
        swatchAnchor.setAttribute('data-w', swatch.w);
        swatchAnchor.href = 'javascript:void(0)';
        swatchAnchor.addEventListener('click', addSwatchLoadBinding);
        swatchWrapper.appendChild(swatchAnchor)
        swatchContainer.insertBefore(swatchWrapper, swatchContainer.firstChild);
    }

    function addSwatchLoadBinding(e) {
        colors = [
            e.target.getAttribute('data-r'),
            e.target.getAttribute('data-g'),
            e.target.getAttribute('data-b'),
            e.target.getAttribute('data-w')
        ];
        var update = false;
        [].slice.call(sliders).forEach(function (slider, index) {
            if ( 3 == index ) {
                update = true;
            }
            slider.noUiSlider.setHandle(0, colors[index], update);
        });
    }

    function addSwatchSaveBinding() {
        saveColor.addEventListener('click', function(e) {
            swatch = getColors();
            addSwatch(swatch);
        });
    }

    function getColors() {
        return {
            r: colors[0],
            g: colors[1],
            b: colors[2],
            w: colors[3]
        }
    }

    // Convert Wite channel to alpha transparency for preview.
    function makeAlpha(alpha) {
        return 1-(alpha/255);
    }

    $( document ).ready(function() {
        loadSwatches();
        rgbwColorPicker();
        addSwatchSaveBinding();
    });


} );
