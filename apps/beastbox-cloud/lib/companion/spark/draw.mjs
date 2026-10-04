/** Put a 64×64 sprite on a canvas. Pixels stay crisp. */

const sheets = new Map();

function bake(sprite) {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  canvas.getContext('2d').putImageData(new ImageData(sprite.rgba, 64, 64), 0, 0);
  return canvas;
}

export function paintSprite(canvas, sprite, scale = 3) {
  const ctx = canvas.getContext('2d');
  canvas.width = 64 * scale;
  canvas.height = 64 * scale;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(bake(sprite), 0, 0, canvas.width, canvas.height);
}

export function blitSprite(ctx, sprite, x, y, w, h, flip = false) {
  const key = sprite;
  let sheet = sheets.get(key);
  if (!sheet) {
    sheet = bake(sprite);
    sheets.set(key, sheet);
  }
  ctx.imageSmoothingEnabled = false;
  ctx.save();
  if (flip) {
    ctx.translate(Math.round(x + w), Math.round(y));
    ctx.scale(-1, 1);
    ctx.drawImage(sheet, 0, 0, w, h);
  } else {
    ctx.drawImage(sheet, Math.round(x), Math.round(y), w, h);
  }
  ctx.restore();
}
