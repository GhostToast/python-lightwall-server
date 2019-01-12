/* global swatches */

// Initialize RGBW Color picker if on proper page.
if (window.location.pathname.indexOf('rgbw-color')) {
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];

    // Load for RGBW Color Picker.
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
}

// Load color pickers, leveraging noUiSlider.
function rgbwColorPicker() {
    saveColor.style.display = 'none';
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
            saveColor.style.display = 'inline-block';
            colors[index] = slider.noUiSlider.get();

            var rgbw = getColors();
            var alpha = makeAlpha(rgbw.w);
            var previewColor = 'rgba('+rgbw.r+','+rgbw.g+','+rgbw.b+','+alpha+')';
            previewElement.style.background = previewColor;
            previewElement.style.color = previewColor;

            fetch('/_post_rgbw_color/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify(rgbw)
            }).then(
                response => response.text()
            ).then(
                html => console.log(html)
            );

            // Send color to server.
            //var xmlhttp = new XMLHttpRequest();
            //xmlhttp.open('POST', '/_post_rgbw_color');
            //xmlhttp.setRequestHeader('Content-Type', 'application/json');
            //xmlhttp.send(JSON.stringify(colorsData));
        });
    });
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
    
    var swatchElement = document.createElement('div');
    swatchElement.classList.add('swatch', 'text-right');

    var swatchDelBtn = document.createElement('button');
    swatchDelBtn.classList.add('btn', 'btn-danger');
    swatchDelBtn.setAttribute('type','button');

    var swatchDelBtnIcon = document.createElement('i');
    swatchDelBtnIcon.classList.add('material-icons');
    swatchDelBtnIcon.appendChild(document.createTextNode('delete'));
    swatchDelBtn.appendChild(swatchDelBtnIcon);
    swatchDelBtn.addEventListener('click', swatchDeleteHandler);
    
    swatchElement.appendChild(swatchDelBtn);

    var styleColor = 'rgba('+swatch.r+','+swatch.g+','+swatch.b+','+makeAlpha(swatch.w)+')';
    swatchElement.style.background = styleColor;
    swatchElement.setAttribute('data-r', swatch.r);
    swatchElement.setAttribute('data-g', swatch.g);
    swatchElement.setAttribute('data-b', swatch.b);
    swatchElement.setAttribute('data-w', swatch.w);
    swatchElement.addEventListener('click', swatchClickHandler);

    swatchWrapper.appendChild(swatchElement)
    swatchContainer.insertBefore(swatchWrapper, swatchContainer.firstChild);
}

// Handle a swatch click.
function swatchClickHandler(e) {
    var swatchList = document.getElementsByClassName('swatch');
    [].forEach.call(swatchList, function(el) {
        el.classList.remove('active');
    });
    e.target.classList.add('active');
    
    colors = [
        parseInt(e.target.getAttribute('data-r')),
        parseInt(e.target.getAttribute('data-g')),
        parseInt(e.target.getAttribute('data-b')),
        parseInt(e.target.getAttribute('data-w'))
    ];
    var update = false;
    [].slice.call(sliders).forEach(function (slider, index) {
        if ( 3 == index ) {
            update = true;
        }
        slider.noUiSlider.setHandle(0, colors[index], update);
    });
    saveColor.style.display = 'none';
}

// Handle deleting a swatch.
function swatchDeleteHandler(e) {
    e.stopPropagation();
    var swatchToDelete = e.target.closest('div.swatch-wrapper');
    swatchToDelete.parentNode.removeChild(swatchToDelete);
}

// Add event listener for saving a swatch.
function addSwatchSaveBinding() {
    saveColor.addEventListener('click', function(e) {
        saveColor.style.display = 'none';
        swatch = getColors();
        addSwatch(swatch);
    });
}

// Get current state of colors array.
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

// Add event listener for clicking body, to release active swatch.
function addBodyClickBinding() {
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('swatch')){
            return;
        } else {
            var swatchList = document.getElementsByClassName('swatch');
            [].forEach.call(swatchList, function(el) {
                el.classList.remove('active');
            });
        }
    });
}
