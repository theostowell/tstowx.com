// Justified Gallery Layout Algorithm
// Based on hugo-theme-gallery

class RowLayout {
  constructor(config) {
    this.top = config.top;
    this.rowWidth = config.rowWidth;
    this.spacing = config.spacing;
    this.rowHeight = config.rowHeight;
    this.heightTolerance = config.heightTolerance;
    this.minAspectRatio = this.rowWidth / config.rowHeight * (1 - config.heightTolerance);
    this.maxAspectRatio = this.rowWidth / config.rowHeight * (1 + config.heightTolerance);
    this.items = [];
    this.height = 0;
  }

  addItem(item) {
    const newItem = { aspectRatio: item };
    const potentialItems = this.items.concat(newItem);
    const containerWidth = this.rowWidth - (potentialItems.length - 1) * this.spacing;
    const totalAspectRatio = potentialItems.reduce((sum, item) => sum + item.aspectRatio, 0);
    const targetAspectRatio = containerWidth / this.rowHeight;

    if (totalAspectRatio < this.minAspectRatio) {
      this.items.push(newItem);
      return true;
    }

    if (totalAspectRatio > this.maxAspectRatio) {
      if (this.items.length === 0) {
        this.items.push(newItem);
        this.completeLayout(containerWidth / totalAspectRatio);
        return true;
      }

      const currentWidth = this.rowWidth - (this.items.length - 1) * this.spacing;
      const currentAspectRatio = this.items.reduce((sum, item) => sum + item.aspectRatio, 0);
      const currentTargetRatio = currentWidth / this.rowHeight;

      if (Math.abs(totalAspectRatio - targetAspectRatio) > Math.abs(currentAspectRatio - currentTargetRatio)) {
        this.completeLayout(currentWidth / currentAspectRatio);
        return false;
      } else {
        this.items.push(newItem);
        this.completeLayout(containerWidth / totalAspectRatio);
        return true;
      }
    } else {
      this.items.push(newItem);
      this.completeLayout(containerWidth / totalAspectRatio);
      return true;
    }
  }

  completeLayout(calculatedHeight) {
    const containerWidth = this.rowWidth - (this.items.length - 1) * this.spacing;
    let adjustedHeight = Math.max(0.5 * this.rowHeight, Math.min(calculatedHeight, 2 * this.rowHeight));
    let scaleFactor;

    if (calculatedHeight !== adjustedHeight) {
      this.height = adjustedHeight;
      scaleFactor = containerWidth / adjustedHeight / (containerWidth / calculatedHeight);
    } else {
      this.height = calculatedHeight;
      scaleFactor = 1;
    }

    let leftPosition = 0;
    for (const item of this.items) {
      item.top = this.top;
      item.width = item.aspectRatio * this.height * scaleFactor;
      item.height = this.height;
      item.left = leftPosition;
      leftPosition += item.width + this.spacing;
    }
  }
}

function createJustifiedLayout(aspectRatios, config) {
  let currentTop = 0;
  let layoutItems = [];
  let currentRow = null;
  let lastHeight = 0;

  for (const aspectRatio of aspectRatios) {
    if (!currentRow) {
      currentRow = new RowLayout({ top: currentTop, ...config });
    }

    const itemAdded = currentRow.addItem(aspectRatio);

    if (currentRow.height > 0) {
      lastHeight = currentRow.height;
      layoutItems = layoutItems.concat(currentRow.items);
      currentTop += currentRow.height + config.spacing;
      currentRow = new RowLayout({ top: currentTop, ...config });

      if (!itemAdded) {
        const retry = currentRow.addItem(aspectRatio);
        if (currentRow.height > 0) {
          lastHeight = currentRow.height;
          layoutItems = layoutItems.concat(currentRow.items);
          currentTop += currentRow.height + config.spacing;
          currentRow = new RowLayout({ top: currentTop, ...config });
        }
      }
    }
  }

  if (currentRow && currentRow.items.length) {
    currentRow.completeLayout(lastHeight || config.rowHeight);
    layoutItems = layoutItems.concat(currentRow.items);
    currentTop += currentRow.height + config.spacing;
  }

  currentTop -= config.spacing;

  return {
    containerHeight: currentTop,
    boxes: layoutItems
  };
}

// Initialize gallery when DOM is ready
function initJustifiedGallery() {
  const gallery = document.getElementById('gallery');
  if (!gallery) return;

  const spacing = 8;
  const rowHeight = 288;
  const heightTolerance = 0.25;

  let currentWidth = 0;
  const galleryItems = gallery.querySelectorAll('.gallery-item');
  const aspectRatios = Array.from(galleryItems).map(item => {
    const img = item.querySelector('img');
    img.style.width = '100%';
    img.style.height = 'auto';
    return parseFloat(img.getAttribute('width')) / parseFloat(img.getAttribute('height'));
  });

  function layoutGallery() {
    if (currentWidth === gallery.getBoundingClientRect().width) return;
    currentWidth = gallery.getBoundingClientRect().width;

    const layout = createJustifiedLayout(aspectRatios, {
      rowWidth: currentWidth,
      spacing: spacing,
      rowHeight: rowHeight,
      heightTolerance: heightTolerance
    });

    galleryItems.forEach((item, index) => {
      const { width, height, top, left } = layout.boxes[index];
      item.style.position = 'absolute';
      item.style.width = width + 'px';
      item.style.height = height + 'px';
      item.style.top = top + 'px';
      item.style.left = left + 'px';
      item.style.overflow = 'hidden';
    });

    gallery.style.position = 'relative';
    gallery.style.height = layout.containerHeight + 'px';
    gallery.style.visibility = '';
  }

  window.addEventListener('resize', layoutGallery);
  window.addEventListener('orientationchange', layoutGallery);
  layoutGallery();
  layoutGallery(); // Run twice to ensure proper layout
}

// Run when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initJustifiedGallery);
} else {
  initJustifiedGallery();
}
