/* global swatches, initialState */

var mode;
if (window.location.pathname.indexOf('life') == 1) {
    mode = 'life';
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];

    // Buttons
    var pauseLifeButton = document.getElementById('pause-life');
    var playLifeButton = document.getElementById('play-life');

    // Load for RGBW Color Picker.
    setInitialRGBWState();
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
    addPausePlayLifeButtonBinding();
}

// Initialize RGBW Color picker if on proper page.
if (window.location.pathname.indexOf('rgbw-color') == 1) {
    mode = 'rgbw';
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];

    // Load for RGBW Color Picker.
    setInitialRGBWState();
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
}

// Initialize HSL Color picker if on proper page.
if (window.location.pathname.indexOf('hsl-color') == 1) {
    mode = 'hsl';
    var hslButtons = document.getElementsByClassName('hsl-special');
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var hsl = [0, 0, 0];

    // Load for HSL Color Picker.
    setInitialHSLState();
    loadSwatches();
    hslColorPicker();
    setInitialHSLState(); // Initialize a second time to get the hue into saturation slider.
    addSwatchSaveBinding();
    addHSLModeClickBinding();
    addBodyClickBinding();
}

if (window.location.pathname.indexOf('fire') == 1) {
    mode = 'fire';
    var fireButtons = document.getElementsByClassName('flames');
    var fireSpecialButtons = document.getElementsByClassName('flames-special');
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var hsl = [0, 0, 0];

    // Buttons
    var pauseFireButton = document.getElementById('pause-fire');
    var playFireButton = document.getElementById('play-fire');

    setInitialHueState();
    loadSwatches();
    hslColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
    addFireModeClickBinding();
    addPausePlayFireButtonBinding();
}

// Initialize Matrix if on proper page.
if (window.location.pathname.indexOf('matrix') == 1) {
    mode = 'matrix';
    var matrixButtons = document.getElementsByClassName('code-rain');
    var sliders = document.getElementsByClassName('sliders');
    var pauseMatrixButton = document.getElementById('pause-matrix');
    var playMatrixButton = document.getElementById('play-matrix');
    var colors = [[0, 0], [0, 0], [0, 0], [0, 0]];

    addColorModeClickBinding();
    addPausePlayMatrixButtonBinding();
    matrixColorSliders();
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
    setInitialRGBWState();
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

function addHSLModeClickBinding() {
    [].slice.call(hslButtons).forEach(function (button, index) {
        button.addEventListener('click', function(e) {
            var button = e.target.closest('button.hsl-special');
            var special = parseInt(button.getAttribute('data-hsl-special'));
            var swatchList = document.getElementsByClassName('swatch');
            [].forEach.call(swatchList, function(el) {
                el.classList.remove('active');
            });
            saveColor.style.display = 'none';
            e.preventDefault();
            fetch('/_post_hsl_special/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify({special})
            }).then(
                response => response.text()
            ).then(
                html => console.log(html)
            );
        });
    });
}

function addFireModeClickBinding() {
    [].slice.call(fireSpecialButtons).forEach(function (button, index) {
        button.addEventListener('click', function(e) {
            var button = e.target.closest('button.flames-special');
            var special = parseInt(button.getAttribute('data-fire-special'));
            e.preventDefault();
            fetch('/_post_fire_special/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify({special})
            }).then(
                response => response.text()
            ).then(
                html => console.log(html)
            );
        });
    });
    [].slice.call(fireButtons).forEach(function (button, index) {
        button.addEventListener('click', function(e) {
            var button = e.target.closest('button.flames');
            var h = parseInt(button.getAttribute('data-h'))
            hsl = [
                h,
                100,
                50
            ];
            var swatchList = document.getElementsByClassName('swatch');
            [].forEach.call(swatchList, function(el) {
                el.classList.remove('active');
            });
            [].slice.call(sliders).forEach(function (slider, index) {
                slider.noUiSlider.setHandle(0, hsl[index], true);
            });
            saveColor.style.display = 'none';
            e.preventDefault();
            fetch('/_post_fire_color/', {
                method: 'POST',
                headers: {
                    'content-type': 'application/json'
                },
                body: JSON.stringify({h})
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

function addPausePlayLifeButtonBinding() {
    playLifeButton.addEventListener('click', function(e) {
        e.preventDefault();
        playLifeButton.style.display = 'none';
        pauseLifeButton.style.display = 'block';
        fetch('/_pause_life/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 0})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });

    pauseLifeButton.addEventListener('click', function(e) {
        e.preventDefault();
        pauseLifeButton.style.display = 'none';
        playLifeButton.style.display = 'block';
        fetch('/_pause_fire/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 1})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });
}

function addPausePlayFireButtonBinding() {
    playFireButton.addEventListener('click', function(e) {
        e.preventDefault();
        playFireButton.style.display = 'none';
        pauseFireButton.style.display = 'block';
        fetch('/_pause_fire/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 0})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });

    pauseFireButton.addEventListener('click', function(e) {
        e.preventDefault();
        pauseFireButton.style.display = 'none';
        playFireButton.style.display = 'block';
        fetch('/_pause_fire/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 1})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });
}

function addPausePlayMatrixButtonBinding() {
    pauseMatrixButton.addEventListener('click', function(e) {
        pauseMatrixButton.style.display = 'none';
        playMatrixButton.style.display = 'block';
        e.preventDefault();
        fetch('/_pause_matrix/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 1})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });

    playMatrixButton.addEventListener('click', function(e) {
        e.preventDefault();
        playMatrixButton.style.display = 'none';
        pauseMatrixButton.style.display = 'block';
        fetch('/_pause_matrix/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({pause: 0})
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });
}

// Load HSL colors from server.
function setInitialHSLState() {
    if (initialState.h) {
        hsl[0] = initialState.h;
    }
    if (initialState.s) {
        hsl[1] = initialState.s;
    }
    if (initialState.l) {
        hsl[2] = initialState.l;
    }
    updateHSLPreview(getHSLColors());
}

// Load Hue color from server.
function setInitialHueState() {
    if (initialState.h) {
        hsl[0] = initialState.h;
        hsl[1] = 100;
        hsl[2] = 50;
    }
    updateHSLPreview(getHSLColors());
}

// Load RGBW colors from server.
function setInitialRGBWState() {
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
    var rgbw = getRGBWColors();
    updateRGBWPreview(rgbw);
}

// Load HSL color pickers, leveraging noUiSlider.
function hslColorPicker() {
    saveColor.style.display = 'none';
    [].slice.call(sliders).forEach(function (slider, index) {
        var max = 100;
        if (index == 0) {
            max = 359;
        }

        noUiSlider.create(slider, {
            start: hsl[index],
            step: 1,
            connect: [true, false],
            tooltips: [true],
            range: {
                'min': 0,
                'max': max
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
            hsl[index] = slider.noUiSlider.get();

            var hslColors = getHSLColors();
            updateHSLPreview(hslColors);

            if ( mode === 'hsl' ) {
                // Send color to server, to update light wall.
                fetch('/_post_hsl_color/', {
                    method: 'POST',
                    headers: {
                        'content-type': 'application/json'
                    },
                    body: JSON.stringify(hslColors)
                }).then(
                    response => response.text()
                ).then(
                    html => console.log(html)
                );
            } else if (mode === 'fire') {
                // Send color to server, to update light wall.
                fetch('/_post_fire_color/', {
                    method: 'POST',
                    headers: {
                        'content-type': 'application/json'
                    },
                    body: JSON.stringify({h: hslColors.h})
                }).then(
                    response => response.text()
                ).then(
                    html => console.log(html)
                );
            }
        });
    });
}

// Load RGBW color pickers, leveraging noUiSlider.
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

            var rgbw = getRGBWColors();
            updateRGBWPreview(rgbw);

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

// Update HSL preview.
function updateHSLPreview(hslcolors) {
    var previewColor = buildHSLPreviewColor(hslcolors);
    previewElement.style.background = previewColor;
    previewElement.style.color = previewColor;

    if (mode == 'hsl') {
        var saturation = sliders[1].getElementsByClassName('noUi-connects');
        var lightness = sliders[2].getElementsByClassName('noUi-connects');
        if (saturation && saturation[0]) {
            saturation[0].style.background = 'linear-gradient(0.25turn, #808080, hsl('+hsl[0]+', 100%, 50%))';
        }
        if (lightness && lightness[0]) {
            lightness[0].style.background = 'linear-gradient(0.25turn, #000000, hsl('+hsl[0]+', 100%, 50%), #FFFFFF)';
        }
    }

}

// Update RGBW preview.
function updateRGBWPreview(rgbw) {
    var previewColor = buildRGBWPreviewColor(rgbw);
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

    if (mode === 'hsl') {
        var styleColor = buildHSLPreviewColor(swatch);
        swatchElement.style.background = styleColor;
        swatchElement.setAttribute('data-h', swatch.h);
        swatchElement.setAttribute('data-s', swatch.s);
        swatchElement.setAttribute('data-l', swatch.l);
        swatchElement.addEventListener('click', swatchHSLClickHandler);
    } else if (mode === 'fire') {
        var styleColor = buildHSLPreviewColor(swatch);
        swatchElement.style.background = styleColor;
        swatchElement.setAttribute('data-h', swatch.h);
        swatchElement.setAttribute('data-s', 100);
        swatchElement.setAttribute('data-l', 50);
        swatchElement.addEventListener('click', swatchHueClickHandler);
    } else {
        var styleColor = buildRGBWPreviewColor(swatch);
        swatchElement.style.background = styleColor;
        swatchElement.setAttribute('data-r', swatch.r);
        swatchElement.setAttribute('data-g', swatch.g);
        swatchElement.setAttribute('data-b', swatch.b);
        swatchElement.setAttribute('data-w', swatch.w);
        swatchElement.addEventListener('click', swatchRGBWClickHandler);
    }
    

    swatchWrapper.appendChild(swatchElement)
    swatchContainer.insertBefore(swatchWrapper, swatchContainer.firstChild);
}

function buildHSLPreviewColor(hsl) {
    var preview = {
        h: 0,
        s: 0,
        l: 0
    };

    if (mode == 'hsl') {
        if (hsl.h) {
            preview.h = parseInt(hsl.h, 10);
        }
        if (hsl.s) {
            preview.s = parseInt(hsl.s, 10);
        }
        if (hsl.l) {
            preview.l = curveLightness(hsl.l);
        }
    } else if (mode == 'fire') {
        if (hsl.h) {
            preview.h = parseInt(hsl.h, 10);
        }
        preview.s = 100;
        preview.l = 50;
    }
    

    console.log(preview);

    return 'hsl('+preview.h+','+preview.s+'%,'+preview.l+'%)';
}

function buildRGBWPreviewColor(rgbw) {
    var preview = {
        r: 0,
        g: 0,
        b: 0,
        w: 0
    };

    if (rgbw.r) {
        preview.r = curveColor(rgbw.r);
    }

    if (rgbw.g) {
        preview.g = curveColor(rgbw.g);
    }

    if (rgbw.b) {
        preview.b = curveColor(rgbw.b);
    }

    if (rgbw.w) {
        preview.w = curveColor(rgbw.w);
    }

    console.log(preview);

    return 'rgba('+preview.r+','+preview.g+','+preview.b+','+makeAlpha(preview.w)+')';
}

// Amplify color for better preview.
function curveColor(color=0) {
    color = parseInt(color,10);
    if (color > 0) {
        return Math.min(255, color+64);
    }
    return color;
}

// Amplify lightness for better preview.
function curveLightness(lightness=0) {
    lightness = parseInt(lightness,10);
    if (lightness > 0) {
        return Math.min(100, lightness+15);
    }
    return lightness;
}

// Handle Hue swatch click.
function swatchHueClickHandler(e) {
    var swatchList = document.getElementsByClassName('swatch');
    [].forEach.call(swatchList, function(el) {
        el.classList.remove('active');
    });
    e.target.classList.add('active');
    
    hsl = [
        parseInt(e.target.getAttribute('data-h')),
        100,
        50
    ];
    [].slice.call(sliders).forEach(function (slider, index) {
        slider.noUiSlider.setHandle(0, hsl[index], true);
    });
    saveColor.style.display = 'none';
}

// Handle HSL swatch click.
function swatchHSLClickHandler(e) {
    var swatchList = document.getElementsByClassName('swatch');
    [].forEach.call(swatchList, function(el) {
        el.classList.remove('active');
    });
    e.target.classList.add('active');
    
    hsl = [
        parseInt(e.target.getAttribute('data-h')),
        parseInt(e.target.getAttribute('data-s')),
        parseInt(e.target.getAttribute('data-l'))
    ];
    var update = false;
    [].slice.call(sliders).forEach(function (slider, index) {
        if ( 2 == index ) {
            update = true;
        }
        slider.noUiSlider.setHandle(0, hsl[index], update);
    });
    saveColor.style.display = 'none';
}

// Handle RGBW swatch click.
function swatchRGBWClickHandler(e) {
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
    if (mode=='hsl') {
        var swatchData = {
            h: parseInt(swatchToDelete.getAttribute('data-h')),
            s: parseInt(swatchToDelete.getAttribute('data-s')),
            l: parseInt(swatchToDelete.getAttribute('data-l'))
        }
    } else {
        var swatchData = {
            r: parseInt(swatchToDelete.getAttribute('data-r')),
            g: parseInt(swatchToDelete.getAttribute('data-g')),
            b: parseInt(swatchToDelete.getAttribute('data-b')),
            w: parseInt(swatchToDelete.getAttribute('data-w'))
        }
    }

    deleteSwatch(swatchData);
    
    swatchWrapper.parentNode.removeChild(swatchWrapper);
}

// Add event listener for saving a swatch.
function addSwatchSaveBinding() {
    saveColor.addEventListener('click', function(e) {
        saveColor.style.display = 'none';
        if (mode === 'hsl' || mode === 'fire') {
            swatch = getHSLColors();
        } else {
            swatch = getRGBWColors();
        }
        addSwatch(swatch);
        saveSwatch(swatch);
    });
}

// Save swatch to data storage.
function saveSwatch(swatch) {
    // Add type for parity with data model.
    swatch.type = 'rgbw';
    var endpoint = '/_rgbw_swatch_data/';

    if (mode=='hsl' || mode=='fire') {
        swatch.type = 'hsl';
        endpoint = '/_hsl_swatch_data/';
    }

    fetch(endpoint, {
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
    swatch.type = 'rgbw';
    var endpoint = '/_rgbw_swatch_data/';

    if (mode=='hsl') {
        swatch.type = 'hsl';
        endpoint = '/_hsl_swatch_data/';
    }

    fetch(endpoint, {
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

// Get current state of colors array: RGBW.
function getRGBWColors() {
    return {
        r: colors[0],
        g: colors[1],
        b: colors[2],
        w: colors[3]
    }
}

// Get current state of colors array: HSL.
function getHSLColors() {
    return {
        h: hsl[0],
        s: hsl[1],
        l: hsl[2]
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
            body: JSON.stringify(getRGBWColors())
        }).then(
            response => response.text()
        ).then(
            html => console.log(html)
        );
    });
}

    
