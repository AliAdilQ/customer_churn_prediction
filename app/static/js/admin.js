document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');

    function setOpen(open) {
        document.body.classList.toggle('sidebar-open', open);
        toggle.setAttribute('aria-expanded', String(open));
    }
    if (toggle) toggle.addEventListener('click', () => setOpen(!document.body.classList.contains('sidebar-open')));
    if (backdrop) backdrop.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && toggle) setOpen(false);
    });
});
