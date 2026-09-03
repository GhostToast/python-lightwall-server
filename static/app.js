/* global swatches, initialState */

var mode;

// Mirrors the firmware palette in lightwall.ino: pure red and green with the
// off-channels at zero, plus neutral white for the baseline and text.
//
// Only the red and green channels are ever set here, exactly as on the wall. An
// earlier version hand-picked these values instead of deriving them from the
// firmware's hues, which hid a real bug -- the panels were showing aquamarine and
// magenta from blue bleed while the preview looked correct. If a colour here
// needs a blue component, the firmware is wrong, not this.
//
// The levels are raised relative to what the panels are sent, because an LED at
// close range is far brighter than the same numbers on a monitor. Ratios are
// preserved: the line is roughly three times the fill, as on the wall.
//
// Shared by the canvas preview and the legend, so the legend cannot describe
// colours the chart does not actually use.
var stockColors = {
    ' ': '#080808',
    'g': '#003c00', // gain fill  - pure green, dim
    'G': '#00b400', // gain line  - pure green
    'r': '#3c0000', // loss fill  - pure red, dim
    'R': '#d20000', // loss line  - pure red
    '-': '#3a3a3a', // baseline   - neutral white channel
    '@': '#cfcfcf'  // text       - neutral white channel
};

// Mirrors githubLevelLight in lightwall.ino: one canonical hue(120)/
// saturation(100)/lightness ramp, kept in sync across both files rather than
// re-picked by eye here (see stockColors' own comment above about why that
// matters). Level 0 is 0 -- true black, matching the untouched margin rows --
// not just dim, or a no-commit day never reads as blank. 1-4 spread wide
// (roughly even jumps in actual channel output, not raw lightness) so the
// steps read as distinct rather than blurring together.
var githubLevelLight = [0, 12, 24, 35, 50];
var githubColors = {' ': '#080808'};
githubLevelLight.forEach(function (lightness, level) {
    githubColors[String(level)] = 'hsl(120, 100%, ' + lightness + '%)';
});
// Initialize RGBW Color picker if on proper page.
if (window.location.pathname.indexOf('rgbw-color') == 1) {
    mode = 'rgbw';
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var colors = [0, 0, 0, 0];
    var rgbwShape = document.getElementById('rgbw-shape');

    // Load for RGBW Color Picker.
    setInitialRGBWState();
    loadSwatches();
    rgbwColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
}

if (window.location.pathname.indexOf('life') == 1) {
    mode = 'life';
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    var hsl = [0, 0, 0];

    // Buttons
    var pauseLifeButton = document.getElementById('pause-life');
    var playLifeButton = document.getElementById('play-life');

    // Speed / Organic sliders. Not part of the 'sliders' class collection
    // above -- that one is iterated by hslColorPicker() as hue/saturation/
    // lightness, and these two are neither.
    var lifeSpeedSlider = document.getElementById('life-speed-slider');
    var lifeOrganicSlider = document.getElementById('life-organic-slider');
    var lifeColorMutationSlider = document.getElementById('life-mutation-slider');
    var lifeEmberSlider = document.getElementById('life-ember-slider');
    var lifeSpeedMin = initialState.minSpeed || 80;
    var lifeSpeedMax = initialState.maxSpeed || 1500;
    var lifeSpeed = initialState.speed || 370; // Milliseconds/generation, as sent to the wall.
    var lifeOrganic = (initialState.organic !== undefined) ? initialState.organic : 50;
    var lifeColorMutation = (initialState.mutation !== undefined) ? initialState.mutation : 0;
    var lifeEmber = (initialState.ember !== undefined) ? initialState.ember : 25;

    // Load for HSL Color Picker.
    setInitialHSLState();
    loadSwatches();
    hslColorPicker();
    setInitialHSLState(); // Initialize a second time to get the hue into saturation slider.
    addSwatchSaveBinding();
    addBodyClickBinding();
    addPausePlayLifeButtonBinding();
    lifeTimingControl();
}

if (window.location.pathname.indexOf('stock') == 1) {
    mode = 'stock';

    var stockForm = document.getElementById('stock-form');
    var stockSymbol = document.getElementById('stock-symbol');
    var stockStatus = document.getElementById('stock-status');
    var stockPreview = document.getElementById('stock-preview');
    var stockBrightnessSlider = document.getElementById('stock-brightness-slider');
    var stockBrightness = initialState.brightness || 155;

    // There is no pause control here, unlike the animated modes -- this chart is
    // a still image, so there is nothing to pause.
    stockSymbol.value = initialState.symbol || '';
    fillStockLegend();
    addStockSymbolBinding();
    stockBrightnessControl();
    loadStockPreview();

    // The poller refreshes during market hours, so keep the preview in step.
    setInterval(loadStockPreview, 60000);
}

if (window.location.pathname.indexOf('github') == 1) {
    mode = 'github';

    var githubForm = document.getElementById('github-form');
    var githubUsername = document.getElementById('github-username');
    var githubStatus = document.getElementById('github-status');
    var githubPreview = document.getElementById('github-preview');
    var githubBrightnessSlider = document.getElementById('github-brightness-slider');
    var githubBrightness = initialState.brightness || 155;

    // There is no pause control here, unlike the animated modes -- this
    // calendar is a still image, so there is nothing to pause.
    githubUsername.value = initialState.username || '';
    fillGithubLegend();
    addGithubUsernameBinding();
    githubBrightnessControl();
    loadGithubPreview();

    // The poller refreshes in the background, so keep the preview in step.
    setInterval(loadGithubPreview, 60000);
}

if (window.location.pathname.indexOf('sprites') == 1) {
    mode = 'sprites';

    var spritesPreview = document.getElementById('sprites-preview');
    var spritesStatus = document.getElementById('sprites-status');
    var spritesSend = document.getElementById('sprites-send');
    var spritesShuffle = document.getElementById('sprites-shuffle');
    var spritesReset = document.getElementById('sprites-reset');
    var spritesList = document.getElementById('sprites-list');
    var spritesBrightnessSlider = document.getElementById('sprites-brightness-slider');

    var spriteLayout = initialState.layout.slice();
    var spriteBrightness = initialState.brightness || 155;

    listSprites();
    spriteBrightnessControl();
    addSpriteBindings();
    drawSpritePreview();
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

// Exact match, not indexOf: '/fireflies'.indexOf('fire') is also 1, so the
// loose test claimed the Fireflies page too and threw on
// document.getElementById('pause-fire') being null, aborting the rest of
// this file before the Fireflies block below could run.
if (window.location.pathname === '/fire') {
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

if (window.location.pathname.indexOf('fireflies') == 1) {
    mode = 'fireflies';
    var sliders = document.getElementsByClassName('sliders');
    var swatchContainer = document.getElementById('swatch-container');
    var saveColor       = document.getElementById('save-color');
    var previewElement  = document.getElementById('preview');
    // Seeded at s=100/l=50 rather than [0,0,0]: this is a hue-only mode, and
    // setInitialHueState() only fills s/l when initialState.h is truthy -- a
    // hue of 0 (red) would otherwise leave the preview black.
    var hsl = [0, 100, 50];

    // Buttons
    var pauseFirefliesButton = document.getElementById('pause-fireflies');
    var playFirefliesButton = document.getElementById('play-fireflies');

    // Glow/density sliders. Not part of the 'sliders' class collection above
    // -- that one is iterated by hslColorPicker() as hue/saturation/
    // lightness, and these four are neither.
    var firefliesFadeSlider = document.getElementById('fireflies-fade-slider');
    var firefliesHoldSlider = document.getElementById('fireflies-hold-slider');
    var firefliesFrequencySlider = document.getElementById('fireflies-frequency-slider');
    var firefliesVariationSlider = document.getElementById('fireflies-variation-slider');
    var firefliesFadeMin = initialState.minFade || 100;
    var firefliesFadeMax = initialState.maxFade || 2500;
    var firefliesHoldMin = (initialState.minHold !== undefined) ? initialState.minHold : 0;
    var firefliesHoldMax = initialState.maxHold || 3000;
    var firefliesFade = initialState.fade || 700;
    var firefliesHold = (initialState.hold !== undefined) ? initialState.hold : 300;
    var firefliesFrequency = (initialState.frequency !== undefined) ? initialState.frequency : 40;
    var firefliesVariation = (initialState.variation !== undefined) ? initialState.variation : 40;

    setInitialHueState();
    loadSwatches();
    hslColorPicker();
    addSwatchSaveBinding();
    addBodyClickBinding();
    addPausePlayFirefliesButtonBinding();
    firefliesTimingControl();
}

// Initialize Matrix if on proper page.
if (window.location.pathname.indexOf('matrix') == 1) {
    mode = 'matrix';
    var matrixButtons = document.getElementsByClassName('code-rain');
    var matrixSpecialButtons = document.getElementsByClassName('code-rain-special');
    var sliders = document.getElementsByClassName('sliders');
    var pauseMatrixButton = document.getElementById('pause-matrix');
    var playMatrixButton = document.getElementById('play-matrix');
    var colors = [[0, 16], [0, 16], [0, 16], [0, 16]];

    addColorModeClickBinding();
    addMatrixSpecialClickBinding();
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

            // Sync sliders + the shared colors array to the preset before
            // sending -- previously a preset click never touched either,
            // so the sliders kept showing stale values, and the *next*
            // slider drag would silently revert the other three channels
            // back to whatever they still displayed. fireSetEvent=false
            // suppresses each slider's own 'set' handler (which otherwise
            // POSTs individually) so this fires exactly one request below
            // instead of four.
            [].slice.call(sliders).forEach(function (slider, sliderIndex) {
                colors[sliderIndex] = data[sliderIndex];
                slider.noUiSlider.set(data[sliderIndex], false);
            });

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

function addMatrixSpecialClickBinding() {
    [].slice.call(matrixSpecialButtons).forEach(function (button, index) {
        button.addEventListener('click', function(e) {
            var button = e.target.closest('button.code-rain-special');
            var special = parseInt(button.getAttribute('data-matrix-special'));
            e.preventDefault();
            fetch('/_post_matrix_special/', {
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
        fetch('/_pause_life/', {
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

/**
 * Life's Speed (ms/generation, sent inverted -- see below), Organic (0-100,
 * per-cell fade stagger), Mutation (0-100, how far a new cell's hue can
 * drift from its parent's), and Ember (0-100, chance a death leaves a
 * persistent ember instead of fading to black) sliders. Built on the same
 * split as spriteBrightnessControl(): the handle position is tracked on every
 * 'update' tick for instant feedback, but the wall only hears about it on
 * 'change' (handle release). Each send is a blocking serial write behind a
 * process-wide mutex (see app.py's _serial_lock), so firing one per pixel of
 * drag would stall the UI and flood the wire.
 *
 * Deliberately posts to /_post_life_timing/ rather than /_post_life_color/ --
 * the color endpoint recolors every live cell on the wall, which would erase
 * whatever genetic drift the colony has built up on every drag.
 *
 * The wire value is milliseconds per generation, where a *smaller* number is
 * faster -- that reads backwards on a slider labelled "Speed", where dragging
 * right is expected to mean faster and show a bigger number. Rather than
 * expose raw milliseconds, the slider's own handle position is the mirror
 * image (lifeSpeedMin + lifeSpeedMax - ms): dragging right increases the
 * handle value and decreases the milliseconds sent, so right is faster and
 * the displayed number rises to match. The transform is its own inverse, so
 * the same line converts in both directions.
 */
function lifeTimingControl() {
    noUiSlider.create(lifeSpeedSlider, {
        start: lifeSpeedMin + lifeSpeedMax - lifeSpeed,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [lifeSpeedMin],
            'max': [lifeSpeedMax]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    noUiSlider.create(lifeOrganicSlider, {
        start: lifeOrganic,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [0],
            'max': [100]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    lifeSpeedSlider.noUiSlider.on('update', function () {
        var handleValue = parseInt(lifeSpeedSlider.noUiSlider.get());
        lifeSpeed = lifeSpeedMin + lifeSpeedMax - handleValue;
    });
    lifeSpeedSlider.noUiSlider.on('change', function () {
        sendLifeTiming();
    });

    lifeOrganicSlider.noUiSlider.on('update', function () {
        lifeOrganic = parseInt(lifeOrganicSlider.noUiSlider.get());
    });
    lifeOrganicSlider.noUiSlider.on('change', function () {
        sendLifeTiming();
    });

    noUiSlider.create(lifeColorMutationSlider, {
        start: lifeColorMutation,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [0],
            'max': [100]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    noUiSlider.create(lifeEmberSlider, {
        start: lifeEmber,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [0],
            'max': [100]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    lifeColorMutationSlider.noUiSlider.on('update', function () {
        lifeColorMutation = parseInt(lifeColorMutationSlider.noUiSlider.get());
    });
    lifeColorMutationSlider.noUiSlider.on('change', function () {
        sendLifeTiming();
    });

    lifeEmberSlider.noUiSlider.on('update', function () {
        lifeEmber = parseInt(lifeEmberSlider.noUiSlider.get());
    });
    lifeEmberSlider.noUiSlider.on('change', function () {
        sendLifeTiming();
    });
}

function sendLifeTiming() {
    fetch('/_post_life_timing/', {
        method: 'POST',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify({speed: lifeSpeed, organic: lifeOrganic, mutation: lifeColorMutation, ember: lifeEmber})
    }).then(
        response => response.text()
    ).then(
        html => console.log(html)
    );
}

/**
 * Fireflies' Fade (ms for each of fade-in and fade-out), Glow (ms held at full
 * brightness), Frequency (0-100, how often one reignites), and Color
 * Variation (0-100, how far each blink's hue may drift from the selected hue)
 * sliders. Same split as lifeTimingControl(): every 'update' tick caches the
 * handle position for instant feedback, and only 'change' (handle release)
 * reaches the wall. Unlike Life's Speed slider there is no inversion anywhere
 * here -- all four values already read the right way round, with more
 * meaning more.
 */
function firefliesTimingControl() {
    noUiSlider.create(firefliesFadeSlider, {
        start: firefliesFade,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [firefliesFadeMin],
            'max': [firefliesFadeMax]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    noUiSlider.create(firefliesHoldSlider, {
        start: firefliesHold,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [firefliesHoldMin],
            'max': [firefliesHoldMax]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    noUiSlider.create(firefliesFrequencySlider, {
        start: firefliesFrequency,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [0],
            'max': [100]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    noUiSlider.create(firefliesVariationSlider, {
        start: firefliesVariation,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [0],
            'max': [100]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    firefliesFadeSlider.noUiSlider.on('update', function () {
        firefliesFade = parseInt(firefliesFadeSlider.noUiSlider.get());
    });
    firefliesFadeSlider.noUiSlider.on('change', function () {
        sendFirefliesTiming();
    });

    firefliesHoldSlider.noUiSlider.on('update', function () {
        firefliesHold = parseInt(firefliesHoldSlider.noUiSlider.get());
    });
    firefliesHoldSlider.noUiSlider.on('change', function () {
        sendFirefliesTiming();
    });

    firefliesFrequencySlider.noUiSlider.on('update', function () {
        firefliesFrequency = parseInt(firefliesFrequencySlider.noUiSlider.get());
    });
    firefliesFrequencySlider.noUiSlider.on('change', function () {
        sendFirefliesTiming();
    });

    firefliesVariationSlider.noUiSlider.on('update', function () {
        firefliesVariation = parseInt(firefliesVariationSlider.noUiSlider.get());
    });
    firefliesVariationSlider.noUiSlider.on('change', function () {
        sendFirefliesTiming();
    });
}

function sendFirefliesTiming() {
    fetch('/_post_fireflies_timing/', {
        method: 'POST',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify({fade: firefliesFade, hold: firefliesHold, frequency: firefliesFrequency, variation: firefliesVariation})
    }).then(
        response => response.text()
    ).then(
        html => console.log(html)
    );
}

// --- Sprites --------------------------------------------------------------

var SPRITE_CELL = 9;   // Preview size of one LED.
var SPRITE_GAP = 1;    // Space between LEDs, so they read as dots.
var SPRITE_STRUT = 4;  // Drawn gap standing in for the wooden struts.

/**
 * Draw the 16 chosen sprites, one per panel.
 *
 * Uses the palette and bitmaps the server sent from sprites.py -- the same data
 * compiled into the firmware -- rather than colours picked by eye here. The stock
 * preview learned that lesson the hard way: hand-picked colours hid a real bug
 * for days because the preview and the wall could disagree.
 */
function drawSpritePreview() {
    var span = 8 * SPRITE_CELL + SPRITE_STRUT;   // one panel plus its strut
    var extent = 4 * span - SPRITE_STRUT;
    spritesPreview.width = extent;
    spritesPreview.height = extent;

    var context = spritesPreview.getContext('2d');
    context.fillStyle = '#000';
    context.fillRect(0, 0, extent, extent);
    context.globalAlpha = Math.max(0.3, spriteBrightness / 255);

    for (var panel = 0; panel < 16; panel++) {
        var bitmap = initialState.sprites[spriteLayout[panel]];
        var ox = (panel % 4) * span;
        var oy = Math.floor(panel / 4) * span;

        for (var y = 0; y < 8; y++) {
            for (var x = 0; x < 8; x++) {
                var index = bitmap[y * 8 + x];
                if (!index) {
                    continue;
                }
                context.fillStyle = initialState.palette[index - 1];
                context.fillRect(ox + x * SPRITE_CELL, oy + y * SPRITE_CELL,
                                 SPRITE_CELL - SPRITE_GAP, SPRITE_CELL - SPRITE_GAP);
            }
        }
    }
    context.globalAlpha = 1;
}

/** Which panel a click landed in, or -1. */
function spritePanelAt(event) {
    var rect = spritesPreview.getBoundingClientRect();
    var span = 8 * SPRITE_CELL + SPRITE_STRUT;
    var col = Math.floor((event.clientX - rect.left) / span);
    var row = Math.floor((event.clientY - rect.top) / span);
    if (col < 0 || col > 3 || row < 0 || row > 3) {
        return -1;
    }
    return row * 4 + col;
}

function addSpriteBindings() {
    // Click a panel to cycle its sprite; shift-click to go back.
    spritesPreview.addEventListener('click', function (e) {
        var panel = spritePanelAt(e);
        if (panel < 0) {
            return;
        }
        var count = initialState.sprites.length;
        var step = e.shiftKey ? count - 1 : 1;
        spriteLayout[panel] = (spriteLayout[panel] + step) % count;
        drawSpritePreview();
        spritesStatus.textContent = 'Panel ' + (panel + 1) + ': ' +
            initialState.names[spriteLayout[panel]] + ' (not sent yet)';
    });

    spritesSend.addEventListener('click', function () {
        sendSprites();
    });

    spritesShuffle.addEventListener('click', function () {
        for (var i = 0; i < spriteLayout.length; i++) {
            spriteLayout[i] = Math.floor(Math.random() * initialState.sprites.length);
        }
        drawSpritePreview();
        sendSprites();
    });

    spritesReset.addEventListener('click', function () {
        for (var i = 0; i < spriteLayout.length; i++) {
            spriteLayout[i] = i % initialState.sprites.length;
        }
        drawSpritePreview();
        sendSprites();
    });
}

function sendSprites() {
    fetch('/_post_sprites/', {
        method: 'POST',
        headers: {
            'content-type': 'application/json'
        },
        body: JSON.stringify({layout: spriteLayout, brightness: spriteBrightness})
    }).then(function (response) {
        // Read as text first: a 500 returns an HTML page, and parsing that as
        // JSON throws, which would otherwise fail silently.
        return response.text().then(function (text) {
            var body = null;
            try {
                body = JSON.parse(text);
            } catch (e) {
                body = null;
            }
            return {ok: response.ok, status: response.status, body: body, text: text};
        });
    }).then(function (result) {
        if (!result.body) {
            console.error('Non-JSON response from /_post_sprites/:', result.text);
            spritesStatus.textContent = 'Server error ' + result.status +
                ' - check the server console for the traceback.';
            return;
        }
        if (!result.ok) {
            spritesStatus.textContent = result.body.error || 'Could not send sprites.';
            return;
        }
        spritesStatus.textContent = 'Sent. Wall is showing these 16 sprites.';
    }).catch(function (error) {
        console.error('Request to /_post_sprites/ failed:', error);
        spritesStatus.textContent = 'Request failed: ' + error.message;
    });
}

function listSprites() {
    initialState.names.forEach(function (name, i) {
        var item = document.createElement('li');
        item.textContent = name;
        spritesList.appendChild(item);
    });
}

function spriteBrightnessControl() {
    noUiSlider.create(spritesBrightnessSlider, {
        start: spriteBrightness,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [initialState.minBrightness || 5],
            'max': [initialState.maxBrightness || 255]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    // Preview follows the drag; the wall only hears about it on release, since
    // each change is a serial write and a full repaint.
    spritesBrightnessSlider.noUiSlider.on('update', function () {
        spriteBrightness = parseInt(spritesBrightnessSlider.noUiSlider.get());
        drawSpritePreview();
    });
    spritesBrightnessSlider.noUiSlider.on('change', function () {
        sendSprites();
    });
}

/**
 * Colour the legend swatches and fill in the day count.
 *
 * Both come from the values the chart is actually drawn with -- stockColors and
 * the window size reported by the server -- rather than being written into the
 * template. A legend that can disagree with its chart is worse than no legend.
 */
function fillStockLegend() {
    var swatchElements = document.getElementsByClassName('legend-swatch');
    for (var i = 0; i < swatchElements.length; i++) {
        var token = swatchElements[i].getAttribute('data-token');
        swatchElements[i].style.background = stockColors[token] || stockColors[' '];
    }

    var days = initialState.days || 32;
    var dayElements = document.querySelectorAll('[data-days]');
    for (var j = 0; j < dayElements.length; j++) {
        dayElements[j].textContent = days;
    }
}

function addStockSymbolBinding() {
    stockForm.addEventListener('submit', function(e) {
        e.preventDefault();
        var symbol = stockSymbol.value.trim().toUpperCase();
        if (!symbol) {
            return;
        }
        stockSymbol.value = symbol;
        stockStatus.textContent = 'Fetching ' + symbol + '...';

        fetch('/_post_stock/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({symbol: symbol})
        }).then(function(response) {
            // A 500 returns an HTML error page, not JSON, so parsing it throws.
            // Read the body as text first and report what actually came back --
            // an earlier version chained straight into response.json() with no
            // catch, so any server error vanished silently and the page just sat
            // there looking like nothing had happened.
            return response.text().then(function(text) {
                var body = null;
                try {
                    body = JSON.parse(text);
                } catch (e) {
                    body = null;
                }
                return {ok: response.ok, status: response.status, body: body, text: text};
            });
        }).then(function(result) {
            if (!result.body) {
                console.error('Non-JSON response from /_post_stock/:', result.text);
                stockStatus.textContent = 'Server error ' + result.status +
                    ' - check the server console for the traceback.';
                return;
            }
            if (!result.ok) {
                stockStatus.textContent = result.body.error ||
                    ('Could not load that symbol (' + result.status + ').');
                return;
            }
            stockStatus.textContent = result.body.symbol + ' ' +
                result.body.price + ' ' + result.body.currency;
            loadStockPreview();
        }).catch(function(error) {
            console.error('Request to /_post_stock/ failed:', error);
            stockStatus.textContent = 'Request failed: ' + error.message;
        });
    });
}

/**
 * Overall brightness for the stock chart.
 *
 * Fires on 'change' rather than 'update' so dragging the handle does not send a
 * frame per pixel of travel -- each one is a serial write and a full repaint of
 * the wall. The preview follows continuously, so it still feels live.
 */
function stockBrightnessControl() {
    noUiSlider.create(stockBrightnessSlider, {
        start: stockBrightness,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [initialState.minBrightness || 5],
            'max': [initialState.maxBrightness || 255]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    // Bind keyboard, matching the other sliders on the site.
    var handle = stockBrightnessSlider.querySelector('.noUi-handle');
    handle.addEventListener('keydown', function (e) {
        var value = parseInt(stockBrightnessSlider.noUiSlider.get());
        if (e.which === 37) {
            stockBrightnessSlider.noUiSlider.set(value - 1);
        }
        if (e.which === 39) {
            stockBrightnessSlider.noUiSlider.set(value + 1);
        }
    });

    // Track the handle locally for instant preview feedback...
    stockBrightnessSlider.noUiSlider.on('update', function () {
        stockBrightness = parseInt(stockBrightnessSlider.noUiSlider.get());
        if (lastStockCells) {
            drawStockPreview(lastStockCells, lastStockStale);
        }
    });

    // ...but only tell the wall once the handle is released.
    stockBrightnessSlider.noUiSlider.on('change', function () {
        fetch('/_post_stock_brightness/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({brightness: stockBrightness})
        }).then(
            response => response.json()
        ).then(function (body) {
            if (body.error) {
                stockStatus.textContent = body.error;
            }
        }).catch(function (error) {
            console.error('Request to /_post_stock_brightness/ failed:', error);
            stockStatus.textContent = 'Brightness not applied: ' + error.message;
        });
    });
}

// Last grid received, kept so the brightness slider can redraw the preview
// without another round trip to the server.
var lastStockCells = null;
var lastStockStale = false;

function loadStockPreview() {
    fetch('/_stock_data/').then(
        response => response.json()
    ).then(function(snapshot) {
        if (snapshot.error) {
            stockStatus.textContent = snapshot.error;
        }
        if (snapshot.data && snapshot.data.cells) {
            lastStockCells = snapshot.data.cells;
            lastStockStale = snapshot.data.stale;
            drawStockPreview(lastStockCells, lastStockStale);
        }
    }).catch(function(error) {
        // Never fail silently here either -- without this a broken preview looks
        // identical to a preview that simply has no data yet.
        console.error('Request to /_stock_data/ failed:', error);
    });
}

/**
 * Paint what the wall is drawing.
 *
 * The server sends a 32x32 grid of tokens rather than raw prices, so the font
 * and the layout rules stay in one place -- this only has to know which color
 * each token is. Panel gaps are drawn as gaps so the preview reads like the
 * physical wall, struts included.
 */
function drawStockPreview(cells, stale) {
    var context = stockPreview.getContext('2d');
    var cell = 9;   // Pixel size in the preview.
    var strut = 3;  // Drawn gap between panels.
    var gap = 1;    // Space between pixels, so individual LEDs read as dots.

    // Size the canvas to exactly what gets drawn: 32 pixels, plus a strut after
    // each of the first three panels. Derived rather than hardcoded so it cannot
    // drift out of step with the metrics above and leave a dead margin.
    var extent = 32 * cell + 3 * strut - gap;
    stockPreview.width = extent;
    stockPreview.height = extent;

    context.fillStyle = '#000';
    context.fillRect(0, 0, extent, extent);

    // Reflect the brightness setting, floored so the preview never goes so dark
    // it looks broken -- at the low end you are dimming for a camera, not
    // turning the wall off, and the preview should still show the shape.
    var level = Math.max(0.3, stockBrightness / 255);
    context.globalAlpha = stale ? level * 0.5 : level;

    for (var y = 0; y < cells.length; y++) {
        for (var x = 0; x < cells[y].length; x++) {
            context.fillStyle = stockColors[cells[y][x]] || stockColors[' '];
            context.fillRect(
                x * cell + Math.floor(x / 8) * strut,
                y * cell + Math.floor(y / 8) * strut,
                cell - gap, cell - gap);
        }
    }

    context.globalAlpha = 1;
}

// --- GitHub contribution calendar ------------------------------------------

/**
 * Colour the legend swatches and fill in the week count. Mirrors
 * fillStockLegend() -- both come from the values the calendar is actually
 * drawn with, rather than being written into the template.
 */
function fillGithubLegend() {
    var swatchElements = document.getElementsByClassName('legend-swatch');
    for (var i = 0; i < swatchElements.length; i++) {
        var token = swatchElements[i].getAttribute('data-token');
        swatchElements[i].style.background = githubColors[token] || githubColors[' '];
    }

    var weeks = initialState.weeks || 32;
    var weekElements = document.querySelectorAll('[data-weeks]');
    for (var j = 0; j < weekElements.length; j++) {
        weekElements[j].textContent = weeks;
    }
}

function addGithubUsernameBinding() {
    githubForm.addEventListener('submit', function(e) {
        e.preventDefault();
        var username = githubUsername.value.trim();
        if (!username) {
            return;
        }
        githubUsername.value = username;
        githubStatus.textContent = 'Fetching ' + username + '...';

        fetch('/_post_github/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({username: username})
        }).then(function(response) {
            // A 500 returns an HTML error page, not JSON, so parsing it
            // throws -- read the body as text first and report what
            // actually came back, same reasoning as addStockSymbolBinding().
            return response.text().then(function(text) {
                var body = null;
                try {
                    body = JSON.parse(text);
                } catch (e) {
                    body = null;
                }
                return {ok: response.ok, status: response.status, body: body, text: text};
            });
        }).then(function(result) {
            if (!result.body) {
                console.error('Non-JSON response from /_post_github/:', result.text);
                githubStatus.textContent = 'Server error ' + result.status +
                    ' - check the server console for the traceback.';
                return;
            }
            if (!result.ok) {
                githubStatus.textContent = result.body.error ||
                    ('Could not load that username (' + result.status + ').');
                return;
            }
            githubStatus.textContent = result.body.username + ': ' +
                result.body.activeDays + ' active day(s).';
            loadGithubPreview();
        }).catch(function(error) {
            console.error('Request to /_post_github/ failed:', error);
            githubStatus.textContent = 'Request failed: ' + error.message;
        });
    });
}

/**
 * Overall brightness for the GitHub calendar. Mirrors stockBrightnessControl()
 * -- fires on 'change' rather than 'update' so dragging the handle does not
 * send a frame per pixel of travel, while the preview follows continuously.
 */
function githubBrightnessControl() {
    noUiSlider.create(githubBrightnessSlider, {
        start: githubBrightness,
        step: 1,
        connect: 'lower',
        tooltips: true,
        range: {
            'min': [initialState.minBrightness || 5],
            'max': [initialState.maxBrightness || 255]
        },
        format: {
            to: function (value) { return parseInt(value); },
            from: function (value) { return parseInt(value); }
        }
    });

    // Bind keyboard, matching the other sliders on the site.
    var handle = githubBrightnessSlider.querySelector('.noUi-handle');
    handle.addEventListener('keydown', function (e) {
        var value = parseInt(githubBrightnessSlider.noUiSlider.get());
        if (e.which === 37) {
            githubBrightnessSlider.noUiSlider.set(value - 1);
        }
        if (e.which === 39) {
            githubBrightnessSlider.noUiSlider.set(value + 1);
        }
    });

    // Track the handle locally for instant preview feedback...
    githubBrightnessSlider.noUiSlider.on('update', function () {
        githubBrightness = parseInt(githubBrightnessSlider.noUiSlider.get());
        if (lastGithubCells) {
            drawGithubPreview(lastGithubCells, lastGithubStale);
        }
    });

    // ...but only tell the wall once the handle is released.
    githubBrightnessSlider.noUiSlider.on('change', function () {
        fetch('/_post_github_brightness/', {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({brightness: githubBrightness})
        }).then(
            response => response.json()
        ).then(function (body) {
            if (body.error) {
                githubStatus.textContent = body.error;
            }
        }).catch(function (error) {
            console.error('Request to /_post_github_brightness/ failed:', error);
            githubStatus.textContent = 'Brightness not applied: ' + error.message;
        });
    });
}

// Last grid received, kept so the brightness slider can redraw the preview
// without another round trip to the server.
var lastGithubCells = null;
var lastGithubStale = false;

function loadGithubPreview() {
    fetch('/_github_data/').then(
        response => response.json()
    ).then(function(snapshot) {
        if (snapshot.error) {
            githubStatus.textContent = snapshot.error;
        }
        if (snapshot.data && snapshot.data.cells) {
            lastGithubCells = snapshot.data.cells;
            lastGithubStale = snapshot.data.stale;
            drawGithubPreview(lastGithubCells, lastGithubStale);
        }
    }).catch(function(error) {
        // Never fail silently here either -- without this a broken preview
        // looks identical to a preview that simply has no data yet.
        console.error('Request to /_github_data/ failed:', error);
    });
}

/**
 * Paint what the wall is drawing. Same cell/strut/gap metrics as
 * drawStockPreview() -- this is the same 32x32 chart space with the same
 * physical struts, just filled with square day-blocks (and the thin gap
 * between them) instead of a sparkline. The shape comes entirely from the
 * token grid github.py hands over; this loop is agnostic to what the tokens
 * represent.
 */
function drawGithubPreview(cells, stale) {
    var context = githubPreview.getContext('2d');
    var cell = 9;   // Pixel size in the preview.
    var strut = 3;  // Drawn gap between panels.
    var gap = 1;    // Space between pixels, so individual LEDs read as dots.

    var extent = 32 * cell + 3 * strut - gap;
    githubPreview.width = extent;
    githubPreview.height = extent;

    context.fillStyle = '#000';
    context.fillRect(0, 0, extent, extent);

    // Reflect the brightness setting, floored so the preview never goes so
    // dark it looks broken.
    var level = Math.max(0.3, githubBrightness / 255);
    context.globalAlpha = stale ? level * 0.5 : level;

    for (var y = 0; y < cells.length; y++) {
        for (var x = 0; x < cells[y].length; x++) {
            context.fillStyle = githubColors[cells[y][x]] || githubColors[' '];
            context.fillRect(
                x * cell + Math.floor(x / 8) * strut,
                y * cell + Math.floor(y / 8) * strut,
                cell - gap, cell - gap);
        }
    }

    context.globalAlpha = 1;
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

function addPausePlayFirefliesButtonBinding() {
    playFirefliesButton.addEventListener('click', function(e) {
        e.preventDefault();
        playFirefliesButton.style.display = 'none';
        pauseFirefliesButton.style.display = 'block';
        fetch('/_pause_fireflies/', {
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

    pauseFirefliesButton.addEventListener('click', function(e) {
        e.preventDefault();
        pauseFirefliesButton.style.display = 'none';
        playFirefliesButton.style.display = 'block';
        fetch('/_pause_fireflies/', {
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
            } else if (mode === 'life') {
                // Send color to server, to update light wall.
                fetch('/_post_life_color/', {
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
            } else if (mode === 'fireflies') {
                // Send color to server, to update light wall.
                fetch('/_post_fireflies_color/', {
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

    if (mode == 'hsl' || mode == 'life') {
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

    if (mode === 'hsl' || mode === 'life') {
        var styleColor = buildHSLPreviewColor(swatch);
        swatchElement.style.background = styleColor;
        swatchElement.setAttribute('data-h', swatch.h);
        swatchElement.setAttribute('data-s', swatch.s);
        swatchElement.setAttribute('data-l', swatch.l);
        swatchElement.addEventListener('click', swatchHSLClickHandler);
    } else if (mode === 'fire' || mode === 'fireflies') {
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

    if (mode == 'hsl' || mode == 'life') {
        if (hsl.h) {
            preview.h = parseInt(hsl.h, 10);
        }
        if (hsl.s) {
            preview.s = parseInt(hsl.s, 10);
        }
        if (hsl.l) {
            preview.l = curveLightness(hsl.l);
        }
    } else if (mode == 'fire' || mode == 'fireflies') {
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
    if (mode == 'hsl' || mode == 'life' || mode == 'fireflies') {
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
        if (mode === 'hsl' || mode === 'fire' || mode === 'life' || mode === 'fireflies') {
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

    if (mode == 'hsl' || mode == 'fire' || mode == 'life' || mode == 'fireflies') {
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

    if (mode == 'hsl' || mode == 'fire' || mode == 'life' || mode == 'fireflies') {
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
        w: colors[3],
        s: rgbwShape ? rgbwShape.value : 0
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

    
