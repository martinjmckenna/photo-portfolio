/* ---------------------------------------------------------------------------
   Photo detail page enhancements: swipe and keyboard navigation.

   Strictly additive. Both are shortcuts to links that already exist in the
   markup — with JavaScript off, or on a device where neither gesture applies,
   the visible Prev / Next / Index links work exactly as before.

   Pinch-to-zoom is deliberately absent from this file: it is native browser
   behaviour and needs no code, only a viewport meta tag that does not disable
   it. The only thing this script owes it is not to fight it, which is why the
   swipe handler bails out on multi-touch and while the page is zoomed in.
   --------------------------------------------------------------------------- */

(function () {
  'use strict';

  var prev = document.querySelector('a[rel="prev"]');
  var next = document.querySelector('a[rel="next"]');
  var index = document.querySelector('.nav-index');

  if (!prev && !next) return;

  function go(link) {
    if (link) window.location.href = link.href;
  }

  /* --- Keyboard: the desktop equivalent of the swipe gestures below ------- */

  document.addEventListener('keydown', function (e) {
    // Leave modified keys alone — they belong to the browser (back, history,
    // word-wise navigation) rather than to us.
    if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;

    if (e.key === 'ArrowLeft') go(prev);
    else if (e.key === 'ArrowRight') go(next);
    else if (e.key === 'Escape') go(index);
    else return;

    e.preventDefault();
  });

  /* --- Swipe ------------------------------------------------------------- */

  var THRESHOLD = 50; // px of horizontal travel before it counts as a swipe
  var TIME_LIMIT = 800; // ms — beyond this it is a slow drag, not a flick
  var startX = 0;
  var startY = 0;
  var startedAt = 0;
  var tracking = false;

  document.addEventListener(
    'touchstart',
    function (e) {
      // A second finger means a pinch, which belongs to the zoom, not to us.
      tracking = e.touches.length === 1;
      var t = e.changedTouches[0];
      startX = t.clientX;
      startY = t.clientY;
      startedAt = Date.now();
    },
    { passive: true }
  );

  document.addEventListener(
    'touchmove',
    function (e) {
      if (e.touches.length > 1) tracking = false;
    },
    { passive: true }
  );

  document.addEventListener(
    'touchcancel',
    function () {
      tracking = false;
    },
    { passive: true }
  );

  document.addEventListener(
    'touchend',
    function (e) {
      if (!tracking) return;
      tracking = false;

      // While the page is zoomed in, a horizontal drag is the visitor panning
      // around the photo. Navigating away from under them would be hostile.
      if (window.visualViewport && window.visualViewport.scale > 1.05) return;

      if (Date.now() - startedAt > TIME_LIMIT) return;

      var t = e.changedTouches[0];
      var dx = t.clientX - startX;
      var dy = t.clientY - startY;

      if (Math.abs(dx) < THRESHOLD) return;
      // Mostly-vertical travel is a scroll or a browser gesture, not a swipe.
      if (Math.abs(dx) < Math.abs(dy) * 1.5) return;

      go(dx < 0 ? next : prev);
    },
    { passive: true }
  );
})();
