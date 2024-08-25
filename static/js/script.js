document.addEventListener('DOMContentLoaded', (event) => {
    function toggleMenu() {
        const boxesContainer = document.getElementById('boxes-container');
        if (boxesContainer) {
            const isVisible = boxesContainer.classList.contains('open');
            if (isVisible) {
                boxesContainer.classList.remove('open');
                boxesContainer.classList.add('close');
            } else {
                boxesContainer.classList.remove('close');
                boxesContainer.classList.add('open');
            }
        } else {
            console.error('Element with id "boxes-container" not found');
        }
    }

    // Expose the function globally if necessary
    window.toggleMenu = toggleMenu;
});
