async function trackActivity(type, detail = '') {
    try {
        await fetch('/api/gamification/activity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, detail })
        });
    } catch (e) { /* silent */ }
}