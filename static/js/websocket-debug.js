// websocket-debug.js
function initWebSocketDebug(url) {
    const debugDiv = document.createElement('div');
    debugDiv.id = 'websocket-debug';
    debugDiv.style.cssText = 'position: fixed; bottom: 10px; right: 10px; width: 300px; height: 200px; background: #f0f0f0; border: 1px solid #ccc; overflow: auto; padding: 10px; font-family: monospace;';
    document.body.appendChild(debugDiv);

    const socket = new WebSocket(url);
    let messageCount = 0;

    function log(message) {
        const logEntry = document.createElement('div');
        logEntry.textContent = message;
        debugDiv.appendChild(logEntry);
        debugDiv.scrollTop = debugDiv.scrollHeight;
        
        messageCount++;
        if (messageCount > 5) {
            debugDiv.removeChild(debugDiv.firstChild);
        }
    }

    socket.onopen = () => log('WebSocket Connected');
    socket.onclose = () => log('WebSocket Disconnected');
    socket.onerror = () => log('WebSocket Error');
    socket.onmessage = (event) => log(`Received: ${event.data}`);

    // Expose a function to send messages for testing
    window.sendWebSocketMessage = (message) => {
        socket.send(message);
        log(`Sent: ${message}`);
    };
}
