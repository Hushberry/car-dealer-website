/* ============================================================
   BACK TO TOP
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    const backToTopBtn = document.getElementById('backToTop');

    if (backToTopBtn) {
        window.addEventListener('scroll', function () {
            backToTopBtn.style.display = window.scrollY > 500 ? 'flex' : 'none';
        });
    }
});


/* ============================================================
   CARD PHOTO ARROWS (homepage car grid)
   ============================================================ */
function changePhoto(button, direction) {
    const cardPhoto = button.closest('.card-photo');
    const img = cardPhoto.querySelector('.rotating-photo');
    const photos = JSON.parse(img.dataset.photos);
    let index = parseInt(img.dataset.index);

    index = (index + direction + photos.length) % photos.length;
    img.dataset.index = index;

    img.style.opacity = 0;

    setTimeout(function () {
        img.src = photos[index];
        img.style.opacity = 1;
    }, 200);

    const dots = cardPhoto.querySelectorAll('.photo-dot');

    dots.forEach(function (dot, i) {
        dot.classList.toggle('active', i === index);
    });
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.photo-arrow').forEach(function (btn) {
        btn.addEventListener('touchend', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const direction = btn.classList.contains('prev') ? -1 : 1;
            changePhoto(btn, direction);
        });
    });
});


/* ============================================================
   HERO SLIDESHOW (homepage)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    const slides = document.querySelectorAll('.hero-slide');
    const dots = document.querySelectorAll('.hero-dot');

    if (!slides.length) {
        return;
    }

    let currentSlide = 0;
    let slideTimer = null;

    function showSlide(index) {
        slides.forEach(function (slide, i) {
            slide.classList.toggle('active', i === index);
        });

        dots.forEach(function (dot, i) {
            dot.classList.toggle('active', i === index);
        });

        currentSlide = index;
    }

    function nextSlide() {
        const next = (currentSlide + 1) % slides.length;
        showSlide(next);
    }

    function startSlideshow() {
        clearInterval(slideTimer);
        slideTimer = setInterval(nextSlide, 6000);
    }

    dots.forEach(function (dot, index) {
        dot.addEventListener('click', function () {
            showSlide(index);
            startSlideshow();
        });
    });

    showSlide(0);
    startSlideshow();
});


/* ============================================================
   LIGHTBOX (car detail page)
   Expects window.carPhotos to be set by an inline script
   in car_detail.html before this file loads.
   ============================================================ */
let lightboxIndex = 0;

function openLightbox(index) {
    lightboxIndex = index;

    const lightbox = document.getElementById('lightbox');

    if (!lightbox) {
        return;
    }

    lightbox.style.display = 'flex';
    updateLightboxImage();
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');

    if (!lightbox) {
        return;
    }

    lightbox.style.display = 'none';
}

function nextPhoto() {
    const photos = window.carPhotos || [];

    if (!photos.length) {
        return;
    }

    lightboxIndex = (lightboxIndex + 1) % photos.length;
    updateLightboxImage();
}

function prevPhoto() {
    const photos = window.carPhotos || [];

    if (!photos.length) {
        return;
    }

    lightboxIndex = (lightboxIndex - 1 + photos.length) % photos.length;
    updateLightboxImage();
}

function updateLightboxImage() {
    const photos = window.carPhotos || [];

    if (!photos.length) {
        return;
    }

    const image = document.getElementById('lightbox-img');
    const counter = document.getElementById('lightbox-counter');

    if (image) {
        image.src = photos[lightboxIndex];
    }

    if (counter) {
        counter.textContent = (lightboxIndex + 1) + ' / ' + photos.length;
    }
}

document.addEventListener('keydown', function (e) {
    const lightbox = document.getElementById('lightbox');

    if (lightbox && lightbox.style.display === 'flex') {
        if (e.key === 'ArrowRight') {
            nextPhoto();
        }
        if (e.key === 'ArrowLeft') {
            prevPhoto();
        }
        if (e.key === 'Escape') {
            closeLightbox();
        }
    }
});

/* Touch support for lightbox arrows specifically */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.lightbox-arrow').forEach(function (btn) {
        btn.addEventListener('touchend', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (btn.classList.contains('prev')) {
                prevPhoto();
            } else {
                nextPhoto();
            }
        });
    });
});


/* ============================================================
   BOOKING / INQUIRY FORM TOGGLE (car detail page)
   ============================================================ */
function toggleForm(type) {
    const wrap = document.getElementById(type + '-form-wrap');
    const icon = document.getElementById(type + '-icon');

    if (!wrap || !icon) {
        return;
    }

    const isOpen = wrap.style.display === 'block';

    wrap.style.display = isOpen ? 'none' : 'block';
    icon.textContent = isOpen ? '+' : '−';
}


/* ============================================================
   GALLERY — VIEW MORE / VIEW LESS
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    const galleryGrid = document.getElementById('galleryGrid');
    const galleryButton = document.getElementById('galleryViewMoreBtn');

    if (!galleryGrid || !galleryButton) {
        return;
    }

    galleryButton.addEventListener('click', function () {
        const galleryItems = galleryGrid.querySelectorAll('.gallery-item');
        const isExpanded = galleryButton.dataset.expanded === 'true';

        if (!isExpanded) {
            galleryItems.forEach(function (item) {
                item.classList.remove('hidden-extra');
            });

            galleryButton.textContent = 'View Less';
            galleryButton.dataset.expanded = 'true';

            return;
        }

        galleryItems.forEach(function (item, index) {
            if (index >= 12) {
                item.classList.add('hidden-extra');
            } else {
                item.classList.remove('hidden-extra');
            }
        });

        galleryButton.textContent = 'View More Photos';
        galleryButton.dataset.expanded = 'false';

        const gallerySection = document.getElementById('gallery');

        if (gallerySection) {
            gallerySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});