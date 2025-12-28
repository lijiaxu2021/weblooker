(function() {
    'use strict';

    const VisitorTracker = {
        config: {
            apiEndpoint: '',
            sessionId: null,
            visitId: null,
            eventQueue: [],
            sendInterval: 30000,
            maxQueueSize: 50,
            debug: false
        },

        init: function(options) {
            if (typeof options === 'string') {
                this.config.apiEndpoint = options;
            } else if (typeof options === 'object') {
                Object.assign(this.config, options);
            }

            if (!this.config.apiEndpoint) {
                console.warn('VisitorTracker: API endpoint not configured');
                return;
            }

            this.config.sessionId = this.generateSessionId();
            this.config.visitId = this.generateVisitId();

            this.collectPageData();
            this.trackPageView();
            this.bindEvents();
            this.startPeriodicSend();

            window.addEventListener('beforeunload', () => {
                this.sendPendingEvents();
            });

            window.addEventListener('pagehide', () => {
                this.sendPendingEvents();
            });

            if (this.config.debug) {
                console.log('VisitorTracker initialized', {
                    sessionId: this.config.sessionId,
                    visitId: this.config.visitId
                });
            }
        },

        generateSessionId: function() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        },

        generateVisitId: function() {
            const ip = this.getClientIP();
            const ua = navigator.userAgent;
            const combined = ip + '-' + ua;
            let hash = 0;
            for (let i = 0; i < combined.length; i++) {
                const char = combined.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            return 'visit_' + Math.abs(hash).toString(16) + '_' + Date.now();
        },

        getClientIP: function() {
            return 'client_ip';
        },

        collectPageData: function() {
            this.pageData = {
                pageUrl: window.location.href,
                referrer: document.referrer || '',
                screenResolution: window.screen.width + 'x' + window.screen.height,
                language: navigator.language || navigator.userLanguage || 'en-US',
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                platform: navigator.platform || 'Unknown',
                cookiesEnabled: navigator.cookieEnabled,
                doNotTrack: navigator.doNotTrack || 'unspecified',
                pageTitle: document.title || '',
                pagePath: window.location.pathname || '/',
                hostname: window.location.hostname || '',
                port: window.location.port || '',
                protocol: window.location.protocol || 'https:',
                online: navigator.onLine
            };
        },

        trackPageView: function() {
            this.sendData('/visit', this.pageData);
        },

        bindEvents: function() {
            this.bindClickEvents();
            this.bindScrollEvents();
            this.bindFormEvents();
            this.bindVisibilityEvents();
            this.bindClickEvents();
        },

        bindClickEvents: function() {
            document.addEventListener('click', (e) => {
                const target = e.target.closest('a, button, [data-trackable="true"], [data-trackable], input[type="submit"], .btn, .button');

                if (target) {
                    const clickData = this.getElementInfo(target);
                    clickData.tag = target.tagName.toLowerCase();
                    clickData.text = this.getElementText(target).substring(0, 200);
                    clickData.href = target.href || '';

                    this.trackEvent('click', clickData, target);
                }
            }, true);
        },

        bindScrollEvents: function() {
            let maxScrollDepth = 0;
            let scrollThresholds = [25, 50, 75, 100];
            let reachedThresholds = new Set();

            const handleScroll = () => {
                const scrollTop = window.scrollY || document.documentElement.scrollTop;
                const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                const scrollPercent = Math.round((scrollTop / docHeight) * 100);

                scrollThresholds.forEach(threshold => {
                    if (scrollPercent >= threshold && !reachedThresholds.has(threshold)) {
                        reachedThresholds.add(threshold);
                        this.trackEvent('scroll_depth', {
                            depth: threshold,
                            scrollTop: scrollTop,
                            scrollPercent: scrollPercent
                        });
                    }
                });

                maxScrollDepth = Math.max(maxScrollDepth, scrollPercent);
            };

            let scrollTimeout;
            const throttledScroll = () => {
                if (scrollTimeout) return;
                scrollTimeout = setTimeout(() => {
                    handleScroll();
                    scrollTimeout = null;
                }, 100);
            };

            window.addEventListener('scroll', throttledScroll, { passive: true });
        },

        bindFormEvents: function() {
            document.addEventListener('focus', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                    this.trackEvent('form_focus', {
                        formType: e.target.type || 'text',
                        formName: e.target.name || '',
                        formId: e.target.id || '',
                        formAction: this.getFormAction(e.target.form),
                        placeholder: e.target.placeholder || ''
                    });
                }
            }, true);

            document.addEventListener('change', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
                    this.trackEvent('form_change', {
                        formType: e.target.type || 'select',
                        formName: e.target.name || '',
                        formId: e.target.id || '',
                        value: this.getInputValue(e.target)
                    });
                }
            }, true);

            document.addEventListener('submit', (e) => {
                if (e.target.tagName === 'FORM') {
                    const formData = new FormData(e.target);
                    const formInfo = {
                        formAction: e.target.action || '',
                        formMethod: e.target.method || 'POST',
                        formId: e.target.id || '',
                        formClass: e.target.className || '',
                        fieldCount: formData.keys().length
                    };

                    if (this.config.debug) {
                        formInfo.formData = Object.fromEntries(formData);
                    }

                    this.trackEvent('form_submit', formInfo, e.target);
                }
            }, true);
        },

        bindVisibilityEvents: function() {
            let pageVisibleTime = 0;
            let lastVisibilityChange = Date.now();

            const handleVisibilityChange = () => {
                const now = Date.now();
                if (!document.hidden) {
                    pageVisibleTime += now - lastVisibilityChange;
                }
                lastVisibilityChange = now;

                this.trackEvent('visibility_change', {
                    visible: !document.hidden,
                    pageVisibleTime: pageVisibleTime,
                    visibilityState: document.visibilityState
                });
            };

            document.addEventListener('visibilitychange', handleVisibilityChange);

            window.addEventListener('focus', () => {
                this.trackEvent('window_focus', {});
            });

            window.addEventListener('blur', () => {
                this.trackEvent('window_blur', {});
            });
        },

        trackEvent: function(eventType, eventData, element) {
            const event = {
                eventType: eventType,
                eventData: eventData,
                visitId: this.config.visitId,
                sessionId: this.config.sessionId,
                elementSelector: element ? this.getCssSelector(element) : '',
                timestamp: new Date().toISOString(),
                pageUrl: window.location.href
            };

            this.config.eventQueue.push(event);

            if (this.config.eventQueue.length >= this.config.maxQueueSize) {
                this.sendPendingEvents();
            }

            if (this.config.debug) {
                console.log('VisitorTracker event:', eventType, event);
            }
        },

        getElementInfo: function(element) {
            const rect = element.getBoundingClientRect();
            return {
                className: element.className || '',
                id: element.id || '',
                tagName: element.tagName,
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                positionX: Math.round(rect.left + rect.width / 2),
                positionY: Math.round(rect.top + rect.height / 2),
                viewportPositionX: Math.round(rect.left),
                viewportPositionY: Math.round(rect.top)
            };
        },

        getElementText: function(element) {
            if (element.textContent) {
                return element.textContent.trim();
            }
            if (element.value) {
                return element.value.trim();
            }
            return '';
        },

        getInputValue: function(input) {
            const type = input.type ? input.type.toLowerCase() : 'text';

            if (type === 'checkbox' || type === 'radio') {
                return input.checked ? 'checked' : 'unchecked';
            }

            if (type === 'file') {
                return input.files.length > 0 ? 'file_selected' : 'no_file';
            }

            const sensitiveTypes = ['password', 'email', 'tel', 'hidden'];
            if (sensitiveTypes.includes(type)) {
                return '[REDACTED]';
            }

            return (input.value || '').substring(0, 100);
        },

        getFormAction: function(form) {
            if (!form) return '';
            return form.action || '';
        },

        getCssSelector: function(element) {
            if (element.id) {
                return '#' + element.id;
            }

            if (element.className && typeof element.className === 'string') {
                const classes = element.className.trim().split(/\s+/).filter(c => c);
                if (classes.length > 0) {
                    return element.tagName.toLowerCase() + '.' + classes.join('.');
                }
            }

            let path = [];
            while (element.nodeType === Node.ELEMENT_NODE) {
                let selector = element.tagName.toLowerCase();

                if (element.id) {
                    selector += '#' + element.id;
                    path.unshift(selector);
                    break;
                }

                let nth = 1;
                let sibling = element.previousSibling;
                while (sibling) {
                    if (sibling.nodeType === Node.ELEMENT_NODE &&
                        sibling.nodeName === element.nodeName) {
                        nth++;
                    }
                    sibling = sibling.previousSibling;
                }

                if (nth > 1) {
                    selector += ':nth-of-type(' + nth + ')';
                }

                path.unshift(selector);
                element = element.parentNode;

                if (path.length >= 3) break;
            }

            return path.join(' > ');
        },

        sendData: function(endpoint, data) {
            const payload = {
                ...data,
                visitId: this.config.visitId,
                sessionId: this.config.sessionId
            };

            if (navigator.sendBeacon) {
                const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                const url = this.config.apiEndpoint + endpoint;

                try {
                    const result = navigator.sendBeacon(url, blob);
                    if (!result && this.config.debug) {
                        console.warn('VisitorTracker: sendBeacon returned false');
                    }
                } catch (e) {
                    if (this.config.debug) {
                        console.error('VisitorTracker sendBeacon error:', e);
                    }
                    this.fallbackSend(endpoint, payload);
                }
            } else {
                this.fallbackSend(endpoint, payload);
            }
        },

        fallbackSend: function(endpoint, payload) {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', this.config.apiEndpoint + endpoint, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.timeout = 10000;

            xhr.ontimeout = () => {
                if (this.config.debug) {
                    console.warn('VisitorTracker: Request timeout');
                }
            };

            xhr.onerror = () => {
                if (this.config.debug) {
                    console.error('VisitorTracker: Request error');
                }
            };

            try {
                xhr.send(JSON.stringify(payload));
            } catch (e) {
                if (this.config.debug) {
                    console.error('VisitorTracker send error:', e);
                }
            }
        },

        sendPendingEvents: function() {
            if (this.config.eventQueue.length === 0) return;

            const events = [...this.config.eventQueue];
            this.config.eventQueue = [];

            this.sendData('/events', { events: events });
        },

        startPeriodicSend: function() {
            setInterval(() => {
                this.sendPendingEvents();
            }, this.config.sendInterval);
        },

        manualTrack: function(eventType, eventData) {
            this.trackEvent(eventType, eventData || {}, null);
            this.sendPendingEvents();
        },

        getSessionInfo: function() {
            return {
                sessionId: this.config.sessionId,
                visitId: this.config.visitId,
                startTime: this.pageData.timestamp
            };
        },

        ping: function() {
            this.trackEvent('ping', {
                timestamp: new Date().toISOString()
            });
            this.sendPendingEvents();
        }
    };

    window.VisitorTracker = VisitorTracker;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = VisitorTracker;
    }
})();
