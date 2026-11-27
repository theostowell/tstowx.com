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

// --- Balanced shuffle -------------------------------------------------------
// A plain shuffle can pile all the portraits into one row, or leave a row
// stretched tall or squashed flat. Instead we try lots of random orders, score
// each layout, and keep the best. Every visit still gets a fresh random order.

function shuffleIndices(n) {
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function scoreOrder(ratios, order, config) {
  const layout = createJustifiedLayout(order.map(i => ratios[i]), config);
  const boxes = layout.boxes;
  const portraitShare = ratios.filter(r => r < 1).length / ratios.length;

  // Group boxes into rows by their top position.
  const rows = [];
  boxes.forEach((box, k) => {
    const last = rows[rows.length - 1];
    if (last && Math.abs(last.top - box.top) < 0.5) last.idx.push(k);
    else rows.push({ top: box.top, height: box.height, idx: [k] });
  });

  let cost = 0;
  rows.forEach((row, r) => {
    const isLast = r === rows.length - 1;
    const rowRatios = row.idx.map(k => ratios[order[k]]);

    // Rows should sit close to the target height (log scale so tall and flat count equally).
    if (!isLast) cost += Math.pow(Math.log(row.height / config.rowHeight), 2) * 4;

    // Portraits and landscapes should be spread through the rows, not clumped.
    const portraits = rowRatios.filter(a => a < 1).length;
    cost += Math.pow(portraits / rowRatios.length - portraitShare, 2) * 1.5;

    // Penalise a lone image filling a whole row.
    if (rowRatios.length === 1 && rows.length > 1) cost += 2;

    // The last row should be reasonably full rather than one stranded photo.
    if (isLast && rows.length > 1) {
      const used = row.idx.reduce((s, k) => s + boxes[k].width, 0) + (row.idx.length - 1) * config.spacing;
      const fill = used / config.rowWidth;
      if (fill < 0.6) cost += (0.6 - fill) * 4;
    }
  });

  // Avoid two very similar images (same aspect ratio) landing next to each other too often.
  for (let k = 1; k < order.length; k++) {
    if (Math.abs(ratios[order[k]] - ratios[order[k - 1]]) < 0.01 && ratios[order[k]] < 1) cost += 0.05;
  }

  return cost / Math.max(rows.length, 1);
}

function pickBalancedOrder(ratios, config) {
  if (ratios.length < 3 || !config.rowWidth) return shuffleIndices(ratios.length);
  const tries = 150;
  let best = null;
  let bestCost = Infinity;
  for (let t = 0; t < tries; t++) {
    const order = shuffleIndices(ratios.length);
    const cost = scoreOrder(ratios, order, config);
    if (cost < bestCost) { bestCost = cost; best = order; }
  }
  return best;
}

// Initialize gallery when DOM is ready
function initJustifiedGallery() {
  const gallery = document.getElementById('gallery');
  if (!gallery) return;

  const spacing = 8;
  const rowHeight = 288;
  const heightTolerance = 0.25;

  let currentWidth = 0;
  const originalItems = Array.from(gallery.querySelectorAll('.gallery-item'));
  const originalRatios = originalItems.map(item => {
    const img = item.querySelector('img');
    img.style.width = '100%';
    img.style.height = 'auto';
    return parseFloat(img.getAttribute('width')) / parseFloat(img.getAttribute('height'));
  });

  // Random but balanced order: shuffle many times, keep the one whose rows look most even.
  const order = pickBalancedOrder(originalRatios, {
    rowWidth: gallery.getBoundingClientRect().width || window.innerWidth,
    spacing: spacing,
    rowHeight: rowHeight,
    heightTolerance: heightTolerance
  });
  const galleryItems = order.map(i => originalItems[i]);
  const aspectRatios = order.map(i => originalRatios[i]);
  galleryItems.forEach(item => gallery.appendChild(item)); // DOM order matches, so tabbing follows the grid

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
