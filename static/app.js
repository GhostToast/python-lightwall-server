/* global swatches, initialState */

var mode;

// Initialize RGBW Color picker if on proper page.
if (window.location.pathname.indexOf('rgbw-color') == 1) {
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];

    // Load for RGBW Color Picker.
    setInitialState();
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
    mode = 'rgbw';
}

// Initialize Matrix if on proper page.
if (window.location.pathname.indexOf('matrix') == 1) {
    var matrixButtons = document.getElementsByClassName('code-rain');
    var sliders = document.getElementsByClassName('sliders');
    var pauseButton = document.getElementById('pause-code');
    var colors = [[0, 0], [0, 0], [0, 0], [0, 0]];

    addColorModeClickBinding();
    addPauseButtonBinding();
    matrixColorSliders();
    mode = 'matrix';
}

// Initialize Gradient if on proper page.
if (window.location.pathname.indexOf('gradient-color') == 1) {
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var sendColor       = document.getElementById('send-color');
    var colors = [0, 0, 0, 0];

    // Load for RGBW Color Picker.
    setInitialState();
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
    addGradientClickBinding();
    mode = 'gradient';
}
    

// Load matrix sliders, leveraging noUiSlider.
function matrixColorSliders() {
    [].slice.call(sliders).forEach(function (slider, index) {

        noUiSlider.create(slider, {
            start: [0, 16],
            step: 1,
            connect: true,
            tooltips: true,
            range: {
                'min': [0],
                'max': [255]
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

            // Send color to server, to update light wall.
            fetch('/_post_matrix/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify(colors)
            }).then(
                response => response.text()
            ).then(
                html => console.log(html)
            );
        });
    });
}

function addColorModeClickBinding() {
    [].slice.call(matrixButtons).forEach(function (button, index) {
        button.addEventListener('click', function(e) {
            var button = e.target.closest('button.code-rain');
            var data = [
                JSON.parse(button.getAttribute('data-r')),
                JSON.parse(button.getAttribute('data-g')),
                JSON.parse(button.getAttribute('data-b')),
                JSON.parse(button.getAttribute('data-w'))
            ];
            console.log(data);
            e.preventDefault();
            fetch('/_post_matrix/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify(data)
            }).then(
                response => response.text()
            ).then(
                html => console.log(html)
            );
        });
    });
}

function addPauseButtonBinding() {
    pauseButton.addEventListener('click', function(e) {
        e.preventDefault();
        fetch('/_pause_matrix/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            }
        });
    });
}
    

// Load colors from server.
function setInitialState() {
    if (initialState.r) {
        colors[0] = initialState.r;
    }
    if (initialState.g) {
        colors[1] = initialState.g;
    }
    if (initialState.b) {
        colors[2] = initialState.b;
    }
    if (initialState.w) {
        colors[3] = initialState.w;
    }
    var rgbw = getColors();
    updatePreview(rgbw);
}

// Load color pickers, leveraging noUiSlider.
function rgbwColorPicker() {
    saveColor.style.display = 'none';
    [].slice.call(sliders).forEach(function (slider, index) {

        noUiSlider.create(slider, {
            start: colors[index],
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
            updatePreview(rgbw);

            if ( mode === 'rgbw' ) {
                // Send color to server, to update light wall.
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
            }
        });
    });
}

// Update preview.
function updatePreview(rgbw) {
    var alpha = makeAlpha(rgbw.w);
    var previewColor = 'rgba('+rgbw.r+','+rgbw.g+','+rgbw.b+','+alpha+')';
    previewElement.style.background = previewColor;
    previewElement.style.color = previewColor;
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
    var swatchToDelete = e.target.closest('div.swatch');
    var swatchWrapper = e.target.closest('div.swatch-wrapper');
    var swatchData = {
        r: parseInt(swatchToDelete.getAttribute('data-r')),
        g: parseInt(swatchToDelete.getAttribute('data-g')),
        b: parseInt(swatchToDelete.getAttribute('data-b')),
        w: parseInt(swatchToDelete.getAttribute('data-w'))
    }
    deleteSwatch(swatchData);
    
    swatchWrapper.parentNode.removeChild(swatchWrapper);
}

// Add event listener for saving a swatch.
function addSwatchSaveBinding() {
    saveColor.addEventListener('click', function(e) {
        saveColor.style.display = 'none';
        swatch = getColors();
        addSwatch(swatch);
        saveSwatch(swatch);
    });
}

// Save swatch to data storage.
function saveSwatch(swatch) {
    // Add type for parity with data model.
    swatch.type = "rgbw";

    fetch('/_rgbw_swatch_data/', {
        method: 'PUT',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify(swatch)
    }).then(
        response => response.text()
    ).then(
        html => console.log(html)
    );
}

// Delete swatch from data storage.
function deleteSwatch(swatch) {
    // Add type for parity with data model.
    swatch.type = "rgbw";

    fetch('/_rgbw_swatch_data/', {
        method: 'DELETE',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify(swatch)
    }).then(
        response => response.text()
    ).then(
        html => console.log(html)
    );
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

// Add event listener for clicking gradient send button.
function addGradientClickBinding() {
    sendColor.addEventListener('click', function(e) {
        // Send color to server, to update light wall.
        fetch('/_post_gradient/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify(getColors())
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });
}

    
