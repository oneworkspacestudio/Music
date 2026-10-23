// Retire the previous offline HTML shell. Authentication and app navigations
// always reach the server; this worker deliberately has no cache fetch handler.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
