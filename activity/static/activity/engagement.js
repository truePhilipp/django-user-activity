(function () {
    var ENDPOINT = window.ACTIVITY_ENGAGEMENT_URL || '/activity/engagement/';
    var IDLE_TIMEOUT_MS = (window.ACTIVITY_IDLE_TIMEOUT_SECONDS || 30) * 1000;
    var TICK_MS = 1000;
    var HEARTBEAT_MS = 30000;
    var INPUT_THROTTLE_MS = 2000;

    var lastActivityAt = Date.now();
    var activeSeconds = 0;
    var idleSeconds = 0;
    var interactionLog = [];
    var lastInputLogAt = {};

    // Generated once per page load (not persisted across reloads), so leaving and later
    // returning to the same url produces a new PageEngagement row server-side instead of
    // accumulating onto the same one forever. A bfcache restore keeps the same JS state
    // (including this id) since it's the same page load continuing, which is intentional -
    // that's a continuation of the same visit, not a new one.
    var VISIT_ID = (window.crypto && typeof window.crypto.randomUUID === 'function')
        ? window.crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2);

    // When this visit actually started, so PageEngagement gets its own accurate timestamp to
    // order by even if the visit never records a single click/input. Sent with every beacon but
    // only used server-side on the row's first creation.
    var VISIT_STARTED_AT = Date.now();

    function markActive() {
        lastActivityAt = Date.now();
    }

    function getXPath(element) {
        if (!element || element.nodeType !== 1) {
            return '';
        }
        if (element.id) {
            return '//*[@id="' + element.id + '"]';
        }
        if (element === document.body) {
            return '/html/body';
        }

        var index = 1;
        var sibling = element.previousElementSibling;
        while (sibling) {
            if (sibling.tagName === element.tagName) {
                index++;
            }
            sibling = sibling.previousElementSibling;
        }

        var parentPath = getXPath(element.parentElement) || '';
        return parentPath + '/' + element.tagName.toLowerCase() + '[' + index + ']';
    }

    // Appended, never merged: each call is its own row server-side, in order, so the sequence of
    // clicks/edits across different elements is preserved instead of collapsing into a per-xpath
    // counter that loses which order things happened in.
    function logInteraction(type, xpath, value) {
        if (!xpath) {
            return;
        }
        var entry = { type: type, xpath: xpath, at: Date.now() };
        if (value !== undefined) {
            entry.value = value;
        }
        interactionLog.push(entry);
    }

    // Fields whose content must never leave the browser, even though we still track that
    // interaction happened. Opt individual fields out further with data-activity-ignore.
    function isSensitiveField(target) {
        if (!target || !target.getAttribute) {
            return true;
        }
        if (target.getAttribute('data-activity-ignore') !== null) {
            return true;
        }
        var type = (target.type || '').toLowerCase();
        if (type === 'password') {
            return true;
        }
        var autocomplete = (target.getAttribute('autocomplete') || '').toLowerCase();
        return autocomplete.indexOf('password') !== -1 || autocomplete.indexOf('cc-') === 0 || autocomplete === 'one-time-code';
    }

    function inputValue(target) {
        return typeof target.value === 'string' ? target.value : (target.isContentEditable ? target.innerText : undefined);
    }

    document.addEventListener('click', function (event) {
        markActive();
        logInteraction('click', getXPath(event.target));
    }, true);

    document.addEventListener('input', function (event) {
        markActive();
        var target = event.target;
        if (isSensitiveField(target)) {
            return;
        }
        var xpath = getXPath(target);
        if (!xpath) {
            return;
        }

        // Throttled: an entry per keystroke would flood the log and make the sequence of
        // interactions harder to read, not easier. 'change' below still catches the exact final
        // value even if the user stops typing inside the throttle window.
        var now = Date.now();
        if (now - (lastInputLogAt[xpath] || 0) >= INPUT_THROTTLE_MS) {
            lastInputLogAt[xpath] = now;
            logInteraction('input', xpath, inputValue(target));
        }
    }, true);

    document.addEventListener('change', function (event) {
        var target = event.target;
        if (isSensitiveField(target)) {
            return;
        }
        var xpath = getXPath(target);
        if (!xpath) {
            return;
        }
        lastInputLogAt[xpath] = Date.now();
        logInteraction('input', xpath, inputValue(target));
    }, true);

    ['mousemove', 'scroll', 'touchstart', 'keydown'].forEach(function (eventName) {
        window.addEventListener(eventName, markActive, { passive: true });
    });

    setInterval(function () {
        if (document.hidden) {
            return;
        }
        var idle = Date.now() - lastActivityAt >= IDLE_TIMEOUT_MS;
        if (idle) {
            idleSeconds += TICK_MS / 1000;
        } else {
            activeSeconds += TICK_MS / 1000;
        }
    }, TICK_MS);

    function flush() {
        if (activeSeconds === 0 && idleSeconds === 0 && interactionLog.length === 0) {
            return;
        }

        var payload = JSON.stringify({
            url: location.pathname,
            visit_id: VISIT_ID,
            visit_started_at: VISIT_STARTED_AT,
            active_seconds: activeSeconds,
            idle_seconds: idleSeconds,
            interactions: interactionLog,
        });

        activeSeconds = 0;
        idleSeconds = 0;
        interactionLog = [];

        if (navigator.sendBeacon) {
            navigator.sendBeacon(ENDPOINT, new Blob([payload], { type: 'application/json' }));
        } else {
            fetch(ENDPOINT, { method: 'POST', body: payload, keepalive: true, headers: { 'Content-Type': 'application/json' } });
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            flush();
        } else {
            markActive();
        }
    });
    window.addEventListener('pagehide', flush);
    setInterval(flush, HEARTBEAT_MS);
})();
