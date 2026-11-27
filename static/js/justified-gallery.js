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
// the part of the layout people will actually see, and keep the best. Every
// visit (and every press of Randomise) still gets a fresh random order.

const SHUFFLE_TRIES = 150;

function shuffled(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Score the first `count` ratios of a sequence. Lower is better.
function scoreSequence(seq, count, portraitShare, config) {
  const ratios = seq.slice(0, count);
  const layout = createJustifiedLayout(ratios, config);
  const boxes = layout.boxes;

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
    const rowRatios = row.idx.map(k => ratios[k]);

    // Rows should sit close to the target height (log scale so tall and flat count equally).
    if (!isLast) cost += Math.pow(Math.log(row.height / config.rowHeight), 2) * 4;

    // Portraits and landscapes should be spread through the rows, not clumped.
    const portraits = rowRatios.filter(a => a < 1).length;
    cost += Math.pow(portraits / rowRatios.length - portraitShare, 2) * 1.5;

    // Penalise a lone image filling a whole row.
    if (rowRatios.length === 1 && rows.length > 1) cost += 2;

    // The bottom row should be reasonably full rather than one stranded photo.
    if (isLast && rows.length > 1) {
      const used = row.idx.reduce((s, k) => s + boxes[k].width, 0) + (row.idx.length - 1) * config.spacing;
      const fill = used / config.rowWidth;
      if (fill < 0.6) cost += (0.6 - fill) * 4;
    }
  });

  return cost / Math.max(rows.length, 1);
}

// Keep `fixed` as it is, shuffle `rest` behind it, and return the most balanced
// result, judged over the first `count` items.
function balancedShuffle(fixed, rest, count, ratioOf, portraitShare, config) {
  if (rest.length < 3 || !config.rowWidth) return fixed.concat(shuffled(rest));
  const head = fixed.map(ratioOf);
  let best = null;
  let bestCost = Infinity;
  for (let t = 0; t < SHUFFLE_TRIES; t++) {
    const candidate = shuffled(rest);
    const seq = head.concat(candidate.map(ratioOf));
    const cost = scoreSequence(seq, Math.min(count, seq.length), portraitShare, config);
    if (cost < bestCost) { bestCost = cost; best = candidate; }
  }
  return fixed.concat(best);
}

// --- Gallery ----------------------------------------------------------------
// Shows a first batch of photos, a Load more button for the rest, and a
// Randomise button that deals a fresh, balanced first batch.

function initJustifiedGallery() {
  const gallery = document.getElementById('gallery');
  if (!gallery) return;

  const spacing = 8;
  const rowHeight = 288;
  const heightTolerance = 0.25;
  const pageSize = parseInt(gallery.dataset.pageSize, 10) || 24;

  const loadMoreWrap = document.getElementById('gallery-load-more');
  const loadMoreBtn = loadMoreWrap && loadMoreWrap.querySelector('button');
  const loadMoreCount = loadMoreWrap && loadMoreWrap.querySelector('.gallery-load-more-count');
  const randomiseBtn = document.getElementById('gallery-randomise');

  const allItems = Array.from(gallery.querySelectorAll('.gallery-item'));
  const ratio = new Map();
  allItems.forEach(item => {
    const img = item.querySelector('img');
    img.style.width = '100%';
    img.style.height = 'auto';
    ratio.set(item, parseFloat(img.getAttribute('width')) / parseFloat(img.getAttribute('height')));
  });
  const ratioOf = item => ratio.get(item);
  const portraitShare = allItems.filter(i => ratioOf(i) < 1).length / Math.max(allItems.length, 1);

  let order = allItems;
  let shown = 0;
  let currentWidth = 0;

  function config() {
    return {
      rowWidth: gallery.getBoundingClientRect().width || window.innerWidth,
      spacing: spacing,
      rowHeight: rowHeight,
      heightTolerance: heightTolerance
    };
  }

  function layout() {
    currentWidth = gallery.getBoundingClientRect().width;
    const visible = order.slice(0, shown);
    const result = createJustifiedLayout(visible.map(ratioOf), config());

    visible.forEach((item, index) => {
      const { width, height, top, left } = result.boxes[index];
      item.style.display = '';
      item.style.position = 'absolute';
      item.style.width = width + 'px';
      item.style.height = height + 'px';
      item.style.top = top + 'px';
      item.style.left = left + 'px';
      item.style.overflow = 'hidden';
    });
    order.slice(shown).forEach(item => { item.style.display = 'none'; });

    gallery.style.position = 'relative';
    gallery.style.height = Math.max(result.containerHeight, 0) + 'px';
    gallery.style.overflow = '';
    gallery.style.visibility = '';
  }

  function render() {
    // DOM order matches the grid, so tabbing and screen readers follow what you see.
    order.forEach(item => gallery.appendChild(item));
    layout();
    if (loadMoreWrap) {
      const left = order.length - shown;
      loadMoreWrap.hidden = left <= 0;
      if (loadMoreCount) loadMoreCount.textContent = `Showing ${shown} of ${order.length}`;
    }
  }

  function deal() {
    shown = Math.min(pageSize, allItems.length);
    order = balancedShuffle([], allItems, shown, ratioOf, portraitShare, config());
    render();
  }

  function loadMore() {
    const next = Math.min(shown + pageSize, order.length);
    order = balancedShuffle(order.slice(0, shown), order.slice(shown), next, ratioOf, portraitShare, config());
    const firstNew = order[shown];
    shown = next;
    render();
    // Move focus to the first new photo so keyboard users carry on from where they were.
    const link = firstNew && firstNew.querySelector('a');
    if (link) link.focus({ preventScroll: true });
  }

  if (loadMoreBtn) loadMoreBtn.addEventListener('click', loadMore);

  if (randomiseBtn) {
    randomiseBtn.hidden = allItems.length < 2;
    randomiseBtn.addEventListener('click', () => {
      gallery.classList.add('is-reshuffling');
      setTimeout(() => {
        deal();
        gallery.classList.remove('is-reshuffling');
      }, 180);
    });
  }

  function onResize() {
    if (currentWidth !== gallery.getBoundingClientRect().width) layout();
  }
  window.addEventListener('resize', onResize);
  window.addEventListener('orientationchange', onResize);

  deal();
  onResize(); // a scrollbar can appear after the first layout and narrow the gallery
}

// Run when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initJustifiedGallery);
} else {
  initJustifiedGallery();
}
