(function () {
    var OPEN_KEY = 'activityDebugSidebarOpen';
    var SESSION_KEY = 'activityDebugSidebarSessionKey';
    var OPEN_CLASS = 'activity-debug-sidebar-open';
    var HIGHLIGHT_OUTLINE = '2px solid #f59e0b';
    var SESSION_KEY_PLACEHOLDER = '__SESSION_KEY__';

    var toggle = document.getElementById('activity-debug-sidebar-toggle');
    var panel = document.getElementById('activity-debug-sidebar-panel');
    var body = document.getElementById('activity-debug-sidebar-body');
    if (!toggle || !panel || !body || !window.htmx) {
        return;
    }

    var sessionsUrl = window.ACTIVITY_DEBUG_SESSIONS_URL;
    var sessionStepsUrlTemplate = window.ACTIVITY_DEBUG_SESSION_STEPS_URL_TEMPLATE;

    function readStorage(key) {
        try {
            return localStorage.getItem(key);
        } catch (_) {
            return null;
        }
    }

    function writeStorage(key, value) {
        try {
            if (value === null) {
                localStorage.removeItem(key);
            } else {
                localStorage.setItem(key, value);
            }
        } catch (_) {
            // Storage unavailable (privacy mode, etc) - the sidebar still works within one page.
        }
    }

    function setOpen(open) {
        panel.style.display = open ? 'flex' : 'none';
        document.documentElement.classList.toggle(OPEN_CLASS, open);
        writeStorage(OPEN_KEY, open ? 'true' : 'false');
    }

    function loadSessionList() {
        htmx.ajax('GET', sessionsUrl, { target: '#activity-debug-sidebar-body', swap: 'innerHTML' });
    }

    function loadSessionSteps(sessionKey) {
        var url = sessionStepsUrlTemplate.replace(SESSION_KEY_PLACEHOLDER, encodeURIComponent(sessionKey));
        htmx.ajax('GET', url, { target: '#activity-debug-sidebar-body', swap: 'innerHTML' });
    }

    function loadCurrentView() {
        var sessionKey = readStorage(SESSION_KEY);
        if (sessionKey) {
            loadSessionSteps(sessionKey);
        } else {
            loadSessionList();
        }
    }

    toggle.addEventListener('click', function () {
        var willOpen = panel.style.display !== 'flex';
        setOpen(willOpen);
        if (willOpen) {
            loadCurrentView();
        }
    });

    // Delegated so it keeps working across htmx swaps of #activity-debug-sidebar-body's content:
    // selecting a session, or a "visit" step within one, navigates the whole page (rather than
    // just swapping this fragment) - the currently loaded session_key is already in storage, so
    // the sidebar restores itself with the same steps showing once the new page loads. "back to
    // sessions" forgets the loaded session so a later page load restores the list instead.
    body.addEventListener('click', function (event) {
        var sessionRow = event.target.closest('[data-session-key]');
        if (sessionRow) {
            writeStorage(SESSION_KEY, sessionRow.dataset.sessionKey);
            window.location.href = sessionRow.dataset.startUrl;
            return;
        }

        if (event.target.closest('[data-activity-debug-back]')) {
            writeStorage(SESSION_KEY, null);
            return;
        }

        var visitRow = event.target.closest('[data-step-kind="visit"]');
        if (visitRow) {
            window.location.href = visitRow.dataset.stepUrl;
        }
    });

    // Hover-highlight: resolves a step's xpath against the *current* page's DOM, but only when
    // the step's recorded url matches the current page - the same xpath string can point at a
    // completely different element elsewhere, so cross-page hovering intentionally does nothing.
    var highlightedElement = null;
    var highlightedElementOriginalOutline = '';

    function clearHighlight() {
        if (highlightedElement) {
            highlightedElement.style.outline = highlightedElementOriginalOutline;
            highlightedElement = null;
        }
    }

    body.addEventListener('mouseover', function (event) {
        var row = event.target.closest('[data-step-xpath]');
        if (!row || !row.dataset.stepXpath || row.dataset.stepUrl !== location.pathname) {
            return;
        }

        var target;
        try {
            target = document.evaluate(
                row.dataset.stepXpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null,
            ).singleNodeValue;
        } catch (_) {
            target = null;
        }
        if (!target) {
            return;
        }

        clearHighlight();
        highlightedElement = target;
        highlightedElementOriginalOutline = target.style.outline;
        target.style.outline = HIGHLIGHT_OUTLINE;
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });

    body.addEventListener('mouseout', function (event) {
        if (event.target.closest('[data-step-xpath]')) {
            clearHighlight();
        }
    });

    // Restore state on every page load: if the sidebar was left open, reopen it and reload
    // whatever was being viewed - the session list, or a specific session's steps - so
    // navigating between pages doesn't reset it.
    if (readStorage(OPEN_KEY) === 'true') {
        setOpen(true);
        loadCurrentView();
    }
})();
